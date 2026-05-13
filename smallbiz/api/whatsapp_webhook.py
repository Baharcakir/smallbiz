import os
import json
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from agents.customer_support_agent import (
    add_whatsapp_message,
    create_customer_support_agent,
    run_customer_support_agent,
)


load_dotenv()

app = FastAPI(title="SmallBiz WhatsApp Webhook")
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "customer_support" / "webhook_events.log"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _log_event(event: str, payload: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "payload": payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _agent() -> Dict:
    return create_customer_support_agent(_env("GOOGLE_API_KEY"))


def _extract_messages(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = value.get("contacts", [])
            contact_lookup = {
                contact.get("wa_id", ""): contact.get("profile", {}).get("name", "")
                for contact in contacts
            }
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                from_phone = message.get("from", "")
                body = message.get("text", {}).get("body", "").strip()
                if not from_phone or not body:
                    continue
                messages.append(
                    {
                        "message_id": message.get("id", ""),
                        "from_phone": from_phone,
                        "customer_name": contact_lookup.get(from_phone, from_phone),
                        "body": body,
                    }
                )
    return messages


def _conversation_id(phone: str) -> str:
    normalized = "".join(ch for ch in phone if ch.isdigit())
    return f"WP-{normalized[-10:] or normalized}"


def _send_whatsapp_text(to_phone: str, body: str) -> Dict[str, Any]:
    access_token = _env("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = _env("WHATSAPP_PHONE_NUMBER_ID")
    graph_version = _env("WHATSAPP_GRAPH_VERSION", "v23.0")

    if not access_token or not phone_number_id:
        return {
            "sent": False,
            "skipped": True,
            "reason": "WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID is missing.",
        }

    url = f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        },
        timeout=15,
    )

    if response.status_code >= 400:
        error_result = {
            "sent": False,
            "skipped": False,
            "status_code": response.status_code,
            "response": response.text,
        }
        _log_event("whatsapp_send_error", error_result)
        return error_result

    success_result = {"sent": True, "skipped": False, "response": response.json()}
    _log_event("whatsapp_send_success", success_result)
    return success_result


def _handle_incoming_message(from_phone: str, customer_name: str, body: str) -> Dict[str, Any]:
    conversation_id = _conversation_id(from_phone)
    add_whatsapp_message(
        conversation_id=conversation_id,
        customer_name=customer_name,
        customer_phone=from_phone,
        sender="customer",
        message=body,
        status="bot_active",
    )

    result = run_customer_support_agent(_agent(), body)
    status = "needs_human" if result.get("confidence") == "low" else "bot_active"
    add_whatsapp_message(
        conversation_id=conversation_id,
        customer_name=customer_name,
        customer_phone=from_phone,
        sender="agent",
        message=result["answer"],
        status=status,
    )
    send_result = _send_whatsapp_text(from_phone, result["answer"])

    return {
        "conversation_id": conversation_id,
        "answer": result["answer"],
        "confidence": result.get("confidence", ""),
        "sources": result.get("sources", []),
        "send_result": send_result,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(request: Request) -> str:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    expected_token = _env("WHATSAPP_VERIFY_TOKEN", "smallbiz_support_verify")

    if mode == "subscribe" and token == expected_token and challenge:
        return challenge

    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@app.post("/webhook")
async def receive_webhook(request: Request) -> Dict[str, Any]:
    payload = await request.json()
    _log_event("webhook_received", payload)
    processed = []
    for message in _extract_messages(payload):
        processed.append(
            _handle_incoming_message(
                from_phone=message["from_phone"],
                customer_name=message["customer_name"],
                body=message["body"],
            )
        )
    return {"ok": True, "processed": processed}


@app.post("/simulate")
async def simulate_message(payload: Dict[str, str]) -> Dict[str, Any]:
    _log_event("simulate_received", payload)
    from_phone = payload.get("from_phone", "+905551112233")
    customer_name = payload.get("customer_name", "Demo Musteri")
    body = payload.get("message", "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="message is required")

    return {
        "ok": True,
        "processed": [
            _handle_incoming_message(
                from_phone=from_phone,
                customer_name=customer_name,
                body=body,
            )
        ],
    }
