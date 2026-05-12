"""
E-posta gönderme modülü (smtplib — dış bağımlılık yok).
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_order_confirmation(
    to_email: str,
    customer_name: str,
    product_name: str,
    quantity: int,
    total_price: float,
    tracking_no: str,
) -> bool:
    """Sipariş onay e-postası gönder. Başarılıysa True döner."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"[MAILER] SMTP yapılandırılmamış — e-posta simüle edildi: {to_email}")
        return True

    subject = "Siparişiniz Alındı — Koop-AI Hatay Kooperatifi"
    body = f"""
Sayın {customer_name},

Siparişiniz başarıyla alınmıştır. Teşekkür ederiz! 🎉

📦 Ürün: {product_name}
🔢 Adet: {quantity}
💰 Toplam Tutar: {total_price:.2f} TL
🚚 Kargo Takip No: {tracking_no}
⏱️ Tahmini Teslimat: 2-3 iş günü (Yurtiçi Kargo)

Kargonuzu takip etmek için: https://www.yurticikargo.com/tr/online-islemler/gonderi-sorgula

Herhangi bir sorunuz için:
📧 info@koop-ai.com
📞 +90 326 000 0000 (Hafta içi 09:00-18:00)

Sevgilerle,
Hatay Kadınlar Kooperatifi - Koop-AI
"""

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[MAILER] ✅ E-posta gönderildi: {to_email}")
        return True
    except Exception as e:
        print(f"[MAILER] ❌ E-posta gönderilemedi: {e}")
        return False


def send_shipping_notification(
    to_email: str,
    customer_name: str,
    tracking_no: str,
) -> bool:
    """Kargo bildirimi e-postası gönder."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"[MAILER] Kargo bildirimi simüle edildi: {to_email}")
        return True

    subject = "Siparişiniz Kargoya Verildi — Koop-AI"
    body = f"""
Sayın {customer_name},

Harika haber! Siparişiniz kargoya verilmiştir. 🚚

🔍 Kargo Takip No: {tracking_no}
📦 Kargo Firması: Yurtiçi Kargo
⏱️ Tahmini Teslimat: 1-2 iş günü

Takip linki: https://www.yurticikargo.com/tr/online-islemler/gonderi-sorgula

Sevgilerle,
Hatay Kadınlar Kooperatifi - Koop-AI
"""
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[MAILER] ❌ {e}")
        return False
