"""
Agent 4 — Kargo Takip
Mock kargo durumu + SQLite entegrasyonu
"""
import random
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session

from database.models import Shipment, Order

CARGO_STATUSES = ["preparing", "picked_up", "in_transit", "out_for_delivery", "delivered"]

STATUS_LABELS = {
    "preparing": "Hazırlanıyor",
    "picked_up": "Kargoya Verildi",
    "in_transit": "Yolda",
    "out_for_delivery": "Dağıtımda",
    "delivered": "Teslim Edildi",
}

STATUS_ICONS = {
    "preparing": "📦",
    "picked_up": "🚛",
    "in_transit": "🛣️",
    "out_for_delivery": "🏠",
    "delivered": "✅",
}

LOCATIONS = {
    "preparing": "Kooperatif Deposu, Hatay",
    "picked_up": "Hatay Yurtiçi Kargo Şubesi",
    "in_transit": "İskenderun Dağıtım Merkezi",
    "out_for_delivery": "Teslimat Şubesi",
    "delivered": "Teslim Edildi",
}


def generate_tracking_no() -> str:
    return f"KOOP{random.randint(100000, 999999)}"


def get_cargo_status(db: Session, tracking_no: str) -> dict:
    """Takip numarasına göre kargo durumunu getir."""
    shipment = db.query(Shipment).filter(Shipment.tracking_no == tracking_no).first()

    if not shipment:
        return {"success": False, "error": f"'{tracking_no}' takip numaralı kargo bulunamadı."}

    # Sipariş yaşına göre otomatik durum ilerletme (demo amaçlı)
    _auto_advance_status(db, shipment)

    status_index = CARGO_STATUSES.index(shipment.status) if shipment.status in CARGO_STATUSES else 0

    # Zaman çizelgesi
    timeline = []
    for i, s in enumerate(CARGO_STATUSES):
        timeline.append({
            "status": s,
            "label": STATUS_LABELS[s],
            "icon": STATUS_ICONS[s],
            "completed": i <= status_index,
            "active": i == status_index,
        })

    order_info = None
    if shipment.order:
        order_info = {
            "customer_name": shipment.order.customer_name,
            "product_name": shipment.order.product.name if shipment.order.product else "Bilinmiyor",
            "quantity": shipment.order.quantity,
        }

    return {
        "success": True,
        "tracking_no": tracking_no,
        "status": shipment.status,
        "status_label": STATUS_LABELS.get(shipment.status, shipment.status),
        "last_location": shipment.last_location,
        "carrier": shipment.carrier,
        "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
        "updated_at": shipment.updated_at.isoformat() if shipment.updated_at else None,
        "timeline": timeline,
        "order": order_info,
    }


def _auto_advance_status(db: Session, shipment: Shipment):
    """Sipariş yaşına göre kargo durumunu otomatik ilerlet (demo)."""
    if not shipment.order or shipment.status == "delivered":
        return

    order_age_days = (datetime.utcnow() - shipment.order.created_at).days

    new_status = shipment.status
    if order_age_days >= 5:
        new_status = "delivered"
    elif order_age_days >= 3:
        new_status = "out_for_delivery"
    elif order_age_days >= 2:
        new_status = "in_transit"
    elif order_age_days >= 1:
        new_status = "picked_up"

    if new_status != shipment.status:
        shipment.status = new_status
        shipment.last_location = LOCATIONS.get(new_status, "")
        shipment.updated_at = datetime.utcnow()
        if new_status == "delivered":
            shipment.estimated_delivery = date.today()
        db.commit()


def assign_cargo(db: Session, order_id: int) -> dict:
    """Siparişe kargo atama."""
    order = db.get(Order, order_id)
    if not order:
        return {"success": False, "error": "Sipariş bulunamadı."}

    if order.shipment:
        return {
            "success": True,
            "tracking_no": order.cargo_tracking_no,
            "message": "Kargo zaten atanmış.",
        }

    tracking_no = generate_tracking_no()
    shipment = Shipment(
        order_id=order_id,
        tracking_no=tracking_no,
        carrier="Yurtiçi Kargo",
        status="preparing",
        last_location=LOCATIONS["preparing"],
        estimated_delivery=date.today() + timedelta(days=3),
    )
    db.add(shipment)
    order.cargo_tracking_no = tracking_no
    db.commit()

    return {"success": True, "tracking_no": tracking_no}


def get_all_shipments(db: Session) -> list:
    """Tüm kargo kayıtlarını getir."""
    shipments = db.query(Shipment).order_by(Shipment.updated_at.desc()).all()
    return [s.to_dict() for s in shipments]
