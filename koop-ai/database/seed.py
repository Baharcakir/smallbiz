"""
Hatay kooperatifi için gerçekçi demo verisi.
Çalıştır: python database/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date, timedelta
from database.db import SessionLocal, init_db
from database.models import Product, Order, Employee, Task, Shipment


def seed():
    init_db()
    db = SessionLocal()

    # Mevcut veriyi temizle
    db.query(Shipment).delete()
    db.query(Task).delete()
    db.query(Order).delete()
    db.query(Employee).delete()
    db.query(Product).delete()
    db.commit()

    # ── Ürünler ─────────────────────────────────────────────────────────────
    products = [
        Product(
            name="Hatay Biber Salçası",
            description="Geleneksel yöntemle üretilen, katkısız taze biber salçası. 450 gram cam kavanoz.",
            price=85.0,
            stock_quantity=120,
            unit="adet",
            category="Salça & Sos",
        ),
        Product(
            name="Hatay İsot Biberi",
            description="Kurutulmuş ve öğütülmüş isot biberi. Yemeklere eşsiz aroma katar. 250 gram.",
            price=65.0,
            stock_quantity=80,
            unit="adet",
            category="Baharat",
        ),
        Product(
            name="Sızma Zeytinyağı",
            description="Soğuk sıkım, ilk hasat sızma zeytinyağı. 500 ml cam şişe.",
            price=220.0,
            stock_quantity=45,
            unit="adet",
            category="Yağ",
        ),
        Product(
            name="Antep Fıstıklı Sucuk",
            description="El yapımı, Antep fıstığı dolgulu köy sucuğu. 300 gram.",
            price=150.0,
            stock_quantity=30,  # Düşük stok — demo için
            unit="adet",
            category="Et Ürünleri",
        ),
        Product(
            name="Doğal Defne Sabunu",
            description="Hatay'ın simgesi, geleneksel yöntemle üretilen saf defne sabunu. 100 gram.",
            price=45.0,
            stock_quantity=200,
            unit="adet",
            category="Kişisel Bakım",
        ),
        Product(
            name="Dövme Sumak",
            description="Taze sumak meyvesinden elde edilen doğal ekşilik. 150 gram.",
            price=40.0,
            stock_quantity=95,
            unit="adet",
            category="Baharat",
        ),
        Product(
            name="Humus",
            description="Tahin ve nohuttan hazırlanan geleneksel humus. 300 gram cam kavanoz.",
            price=70.0,
            stock_quantity=60,
            unit="adet",
            category="Meze",
        ),
    ]
    db.add_all(products)
    db.commit()

    # ── Çalışanlar ────────────────────────────────────────────────────────────
    employees = [
        Employee(name="Fatma Yıldız", role="Üretim Uzmanı", department="Üretim", status="active"),
        Employee(name="Ayşe Kaya", role="Paketleme Sorumlusu", department="Paketleme", status="active"),
        Employee(name="Hatice Demir", role="Muhasebe Uzmanı", department="Muhasebe", status="active"),
        Employee(name="Zeynep Çelik", role="Satış Temsilcisi", department="Satış", status="active"),
        Employee(name="Emine Şahin", role="Kalite Kontrol", department="Üretim", status="on_leave"),
    ]
    db.add_all(employees)
    db.commit()

    # ── Görevler ─────────────────────────────────────────────────────────────
    today = date.today()
    tasks = [
        # Aktif görevler
        Task(employee_id=1, title="Aylık salça üretimi planla", description="Mayıs ayı salça üretim miktarını ve ham madde ihtiyacını hesapla", status="in_progress", due_date=today + timedelta(days=3)),
        Task(employee_id=2, title="Kargo paketlerini hazırla", description="Bekleyen 12 siparişin paketlenmesi ve etiketlenmesi", status="pending", due_date=today + timedelta(days=1)),
        Task(employee_id=3, title="Nisan ayı muhasebe raporu", description="Gelir-gider tablosunu hazırla ve kooperatif yönetimine sun", status="done", due_date=today - timedelta(days=5)),
        Task(employee_id=4, title="Instagram pazarlama görselleri", description="Yeni ürünler için tanıtım görseli ve içerik hazırla", status="in_progress", due_date=today + timedelta(days=7)),
        # Gecikmiş görevler (demo etkisi için)
        Task(employee_id=1, title="Stok sayımı yap", description="Tüm ürünlerin fiziksel stok sayımını gerçekleştir ve sisteme gir", status="pending", due_date=today - timedelta(days=3)),
        Task(employee_id=5, title="Kalite sertifikası yenile", description="Gıda güvenliği sertifikasının yenilenmesi için başvuru yap", status="pending", due_date=today - timedelta(days=7)),
        Task(employee_id=2, title="Depo düzeni iyileştir", description="Paketleme alanı yerleşim planını yeniden düzenle", status="pending", due_date=today + timedelta(days=14)),
        Task(employee_id=3, title="KDV beyannamesi hazırla", description="2. çeyrek KDV beyannamesi için belgeleri topla", status="pending", due_date=today + timedelta(days=10)),
    ]
    db.add_all(tasks)
    db.commit()

    # ── Siparişler & Kargolar ────────────────────────────────────────────────
    tracking_counter = 100001
    orders_data = [
        ("Mehmet Arslan", "mehmet@example.com", "+90 532 111 2233", 1, 3, "delivered"),
        ("Selma Koç", "selma@example.com", "+90 533 222 3344", 3, 1, "delivered"),
        ("Ali Yılmaz", "ali@example.com", "+90 534 333 4455", 2, 5, "shipped"),
        ("Fatma Güneş", "fatma.gunes@example.com", "+90 535 444 5566", 5, 10, "shipped"),
        ("Hasan Öztürk", "hasan@example.com", "+90 536 555 6677", 1, 2, "confirmed"),
        ("Merve Aktaş", "merve@example.com", "+90 537 666 7788", 4, 1, "confirmed"),
        ("Bülent Sarı", "bulent@example.com", "+90 538 777 8899", 7, 3, "pending"),
        ("Derya Polat", "derya@example.com", "+90 539 888 9900", 6, 2, "pending"),
        ("Cengiz Aydın", "cengiz@example.com", "+90 530 999 0011", 3, 2, "pending"),
        ("Nilüfer Başer", "nilufer@example.com", "+90 531 000 1122", 1, 4, "shipped"),
        ("Kadir Tunç", "kadir@example.com", "+90 532 123 4567", 2, 3, "delivered"),
        ("Reyhan Yıldız", "reyhan@example.com", "+90 533 234 5678", 5, 5, "pending"),
    ]

    cargo_status_map = {
        "delivered": "delivered",
        "shipped": "in_transit",
        "confirmed": "picked_up",
        "pending": "preparing",
    }

    cargo_location_map = {
        "delivered": "Teslim Edildi",
        "in_transit": "İskenderun Dağıtım Merkezi",
        "picked_up": "Hatay Şube",
        "preparing": "Kooperatif Deposu",
    }

    for i, (cname, cemail, cphone, pid, qty, status) in enumerate(orders_data):
        product = db.get(Product, pid)
        total = product.price * qty
        tracking_no = f"KOOP{tracking_counter + i}"
        created_days_ago = (len(orders_data) - i) * 2

        order = Order(
            customer_name=cname,
            customer_email=cemail,
            customer_phone=cphone,
            product_id=pid,
            quantity=qty,
            total_price=total,
            status=status,
            cargo_tracking_no=tracking_no,
            created_at=datetime.utcnow() - timedelta(days=created_days_ago),
        )
        db.add(order)
        db.flush()

        cargo_s = cargo_status_map[status]
        shipment = Shipment(
            order_id=order.id,
            tracking_no=tracking_no,
            carrier="Yurtiçi Kargo",
            status=cargo_s,
            last_location=cargo_location_map[cargo_s],
            estimated_delivery=date.today() + timedelta(days=2) if status != "delivered" else date.today() - timedelta(days=1),
            updated_at=datetime.utcnow() - timedelta(days=max(0, created_days_ago - 1)),
        )
        db.add(shipment)

    db.commit()
    db.close()
    print("✅ Demo verisi başarıyla yüklendi!")
    print(f"   📦 {len(products)} ürün")
    print(f"   👥 {len(employees)} çalışan")
    print(f"   📋 {len(tasks)} görev")
    print(f"   🛒 {len(orders_data)} sipariş + kargo kaydı")


if __name__ == "__main__":
    seed()
