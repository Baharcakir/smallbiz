import json
import os
import re
from typing import Dict, List, Optional

from langchain_core.tools import tool

import database
import email_service

try:
	import google.generativeai as genai
except Exception:
	genai = None


def _call_order_agent(order_agent, prompt: str) -> str:
	"""Reserved for future cross-agent collaboration with the order agent."""
	if not order_agent:
		return "Sipariş asistanı kullanılamıyor."

	try:
		from agents.order_agent import run_order_agent

		return run_order_agent(order_agent, prompt)
	except Exception:
		return "Sipariş asistanından bağlam alınamadı."


@tool
def get_inventory_tool() -> str:
	"""Get the full inventory list."""
	return json.dumps(database.get_inventory())


@tool
def get_inventory_item_tool(product_name: str) -> str:
	"""Get a single inventory item by product name."""
	item = database.get_inventory_item(product_name)
	if not item:
		return f"{product_name} için envanter kaydı bulunamadı."
	return json.dumps(item)


@tool
def get_low_stock_items_tool() -> str:
	"""Get items that are at or below the reorder threshold."""
	return json.dumps(database.get_low_stock_items())


@tool
def get_inventory_health_tool() -> str:
	"""Get a summary of inventory health."""
	return json.dumps(database.get_inventory_health())


@tool
def get_popular_products_tool(limit: int = 5) -> str:
	"""Get the most wanted products based on all-time sales history."""
	return json.dumps(database.get_stock_recommendations(limit=limit))


@tool
def adjust_stock_tool(product_name: str, delta: int, notes: str = "") -> str:
	"""Adjust the stock quantity for a product."""
	updated = database.adjust_inventory_stock(product_name, delta, notes)
	if not updated:
		return f"{product_name} için stok güncellenemedi."
	return json.dumps(updated)


@tool
def send_low_stock_alert_tool() -> str:
	"""Send a low stock alert email to the business owner."""
	low_stock_items = database.get_low_stock_items()
	if not low_stock_items:
		return "Düşük stok ürünü bulunamadı."

	return json.dumps(_process_low_stock_alert(use_real=False))


def _process_low_stock_alert(use_real: bool) -> Dict:
	"""Create follow-up restock tasks and send the low-stock alert."""
	low_stock_items = database.get_low_stock_items()
	if not low_stock_items:
		return {"sent": False, "count": 0, "created_tasks": 0, "recipient": ""}

	created_tasks = []
	for item in low_stock_items:
		task = database.create_restock_task(
			product_name=item["product_name"],
			current_stock=item["current_stock"],
			reorder_level=item["reorder_level"],
		)
		if task:
			created_tasks.append(task)

	enable_env = os.getenv("ENABLE_REAL_EMAIL", "").lower() in ("1", "true", "yes")
	has_creds = bool(os.getenv("SENDER_EMAIL")) and bool(os.getenv("SENDER_PASSWORD"))
	effective_use_real = use_real or enable_env or has_creds
	sent = email_service.send_low_stock_notification(low_stock_items, use_real=effective_use_real)
	return {
		"sent": sent,
		"count": len(low_stock_items),
		"created_tasks": len(created_tasks),
		"recipient": os.getenv("BUSINESS_OWNER_EMAIL") or os.getenv("SENDER_EMAIL", "noreply@smallbiz.com"),
	}


tools_list = [
	get_inventory_tool,
	get_inventory_item_tool,
	get_low_stock_items_tool,
	get_inventory_health_tool,
	get_popular_products_tool,
	adjust_stock_tool,
	send_low_stock_alert_tool,
]


def create_stock_manager_agent(api_key: str, order_agent=None):
	"""Create a stock manager agent object."""
	if not api_key or genai is None:
		return {
			"api_key": api_key,
			"order_agent": order_agent,
			"tools": tools_list,
			"name": "Stock Manager Agent",
		}

	api_key = api_key.strip() if isinstance(api_key, str) else api_key
	genai.configure(api_key=api_key)
	return {
		"api_key": api_key,
		"model": "gemini-1.5",
		"temperature": 0.4,
		"order_agent": order_agent,
		"tools": tools_list,
		"name": "Stock Manager Agent",
	}


def _format_inventory_list(items: List[Dict]) -> str:
	if not items:
		return "Envanter kaydı bulunamadı."

	lines = ["Envanter:"]
	for item in items:
		lines.append(
			f"- {item['product_name']} | SKU: {item['sku']} | Stok: {item['current_stock']} | Reorder: {item['reorder_level']}"
		)
	return "\n".join(lines)


def _format_recommendations(items: List[Dict]) -> str:
	if not items:
		return "Öneri üretilemedi."

	lines = ["En çok talep gören ürünler:"]
	for item in items:
		stock_label = "stok bilgisi yok"
		if item.get("current_stock") is not None:
			stock_label = f"stok {item['current_stock']}"
		lines.append(
			f"- {item['product_name']} | Satış: {item['total_quantity_sold']} | Sipariş: {item['order_count']} | {stock_label}"
		)
	return "\n".join(lines)


def run_stock_manager_agent(agent, user_input: str) -> str:
	"""Run the stock manager agent with intent-based routing."""
	text = user_input.strip()
	lower = text.lower()

	if any(k in lower for k in ["alert", "low stock email", "send low stock", "düşük stok", "stok alarm", "notify owner"]):
		return json.dumps(_process_low_stock_alert(use_real=bool(agent.get("use_real_email", False))))

	if any(k in lower for k in ["recommend", "most wanted", "best seller", "popular", "en çok talep", "öner"]):
		match = re.search(r"\b(\d+)\b", text)
		limit = int(match.group(1)) if match else 5
		return _format_recommendations(database.get_stock_recommendations(limit=limit))

	if any(k in lower for k in ["low stock", "reorder", "stock status", "stok", "envanter", "inventory"]):
		low_stock = database.get_low_stock_items()
		if any(k in lower for k in ["health", "summary", "overview", "durum"]):
			return json.dumps(database.get_inventory_health())
		return _format_inventory_list(low_stock or database.get_inventory())

	if any(k in lower for k in ["adjust", "update stock", "restock", "add stock", "remove stock", "stok güncelle"]):
		product_match = re.search(r'"([^"]+)"|\b([A-Za-z0-9\- ]{2,})\b', text)
		delta_match = re.search(r"([+-]?\d+)", text)
		if not product_match or not delta_match:
			return "Stok güncellemek için ürün adı ve miktar belirtin. Örn: Laptop +5"

		product_name = (product_match.group(1) or product_match.group(2) or "").strip()
		delta = int(delta_match.group(1))
		updated = database.adjust_inventory_stock(product_name, delta)
		if not updated:
			return f"{product_name} için stok güncellenemedi."
		return json.dumps(updated)

	if any(k in lower for k in ["order", "sipariş", "sales context", "demand", "what is up"]):
		# Keep a light collaboration hook available for prompts that want sales context.
		sales_summary = database.get_product_sales_summary(limit=5)
		if agent.get("order_agent"):
			_call_order_agent(agent.get("order_agent"), "Son siparişlerdeki ürün talebi hakkında bağlam ver.")
		return _format_recommendations(sales_summary)

	health = database.get_inventory_health()
	recommendations = database.get_stock_recommendations(limit=5)
	return (
		f"Envanter özeti: toplam {health['total_items']} ürün, "
		f"{health['low_stock_items']} düşük stok, {health['out_of_stock_items']} sıfır stok.\n\n"
		f"{_format_recommendations(recommendations)}"
	)
