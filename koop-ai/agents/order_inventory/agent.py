"""
Agent 2 — Sipariş & Stok Yönetimi
"""
import random
from datetime import date, timedelta
from sqlalchemy.orm import Session

from database.models import Order, Product, Shipment
from agents.order_inventory.mailer import send_order_confirmation, send_shipping_notification

LOW_STOCK_THRESHOLD = 10


def generate_tracking_no() -> str:
    return f"KOOP{random.randint(100000, 999999)}"


def create_order(
    db: Session,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    product_id: int,
    quantity: int,
    notes: str = "",
) -> dict:
    """
    Sipariş oluştur:
    1. Stok kontrol
    2. Sipariş + kargo kaydı oluştur
    3. Stok düş
    4. Onay e-postası gönder
    """
    product = db.get(Product, product_id)
    if not product:
        return {"success": False, "error": "Ürün bulunamadı."}

    if product.stock_quantity < quantity:
        return {
            "success": False,
            "error": f"Yetersiz stok. Mevcut: {product.stock_quantity} {product.unit}",
        }

    total_price = product.price * quantity
    tracking_no = generate_tracking_no()

    # Sipariş oluştur
    order = Order(
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        product_id=product_id,
        quantity=quantity,
        total_price=total_price,
        status="confirmed",
        cargo_tracking_no=tracking_no,
        notes=notes,
    )
    db.add(order)
    db.flush()

    # Kargo kaydı oluştur
    shipment = Shipment(
        order_id=order.id,
        tracking_no=tracking_no,
        carrier="Yurtiçi Kargo",
        status="preparing",
        last_location="Kooperatif Deposu",
        estimated_delivery=date.today() + timedelta(days=3),
    )
    db.add(shipment)

    # Stok düş
    product.stock_quantity -= quantity
    db.commit()

    # E-posta gönder (arka planda)
    if customer_email:
        send_order_confirmation(
            to_email=customer_email,
            customer_name=customer_name,
            product_name=product.name,
            quantity=quantity,
            total_price=total_price,
            tracking_no=tracking_no,
        )

    result = {
        "success": True,
        "order_id": order.id,
        "tracking_no": tracking_no,
        "total_price": total_price,
        "product_name": product.name,
        "remaining_stock": product.stock_quantity,
        "low_stock_warning": product.stock_quantity < LOW_STOCK_THRESHOLD,
    }
    return result


def get_orders(db: Session, status: str = None) -> list:
    """Siparişleri listele, opsiyonel olarak duruma göre filtrele."""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.created_at.desc()).all()
    return [o.to_dict() for o in orders]


def update_order_status(db: Session, order_id: int, new_status: str) -> dict:
    """Sipariş durumunu güncelle, kargoya verilirse bildirim gönder."""
    order = db.get(Order, order_id)
    if not order:
        return {"success": False, "error": "Sipariş bulunamadı."}

    old_status = order.status
    order.status = new_status

    # Kargo durumunu da senkronize et
    if order.shipment:
        status_map = {
            "pending": "preparing",
            "confirmed": "picked_up",
            "shipped": "in_transit",
            "delivered": "delivered",
        }
        if new_status in status_map:
            order.shipment.status = status_map[new_status]
            if new_status == "shipped":
                order.shipment.last_location = "İskenderun Dağıtım Merkezi"
            elif new_status == "delivered":
                order.shipment.last_location = "Teslim Edildi"

    db.commit()

    # Kargoya verildi bildirimi
    if new_status == "shipped" and order.customer_email and old_status != "shipped":
        send_shipping_notification(
            to_email=order.customer_email,
            customer_name=order.customer_name,
            tracking_no=order.cargo_tracking_no,
        )

    return {"success": True, "order_id": order_id, "new_status": new_status}


def check_stock(db: Session, product_id: int) -> dict:
    """Stok durumunu kontrol et."""
    product = db.get(Product, product_id)
    if not product:
        return {"success": False, "error": "Ürün bulunamadı."}

    return {
        "product_id": product_id,
        "product_name": product.name,
        "stock_quantity": product.stock_quantity,
        "unit": product.unit,
        "low_stock_warning": product.stock_quantity < LOW_STOCK_THRESHOLD,
    }


def get_all_stock(db: Session) -> list:
    """Tüm ürünlerin stok durumunu getir."""
    products = db.query(Product).all()
    return [
        {
            **p.to_dict(),
            "low_stock_warning": p.stock_quantity < LOW_STOCK_THRESHOLD,
        }
        for p in products
    ]
