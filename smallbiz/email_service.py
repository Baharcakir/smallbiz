import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime
import database
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class EmailSender:
    """Handle sending emails for order notifications."""
    
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        sender_email: str = None,
        sender_password: str = None,
        use_mock: Optional[bool] = None,
    ):
        """
        Initialize email sender.
        
        Args:
            smtp_server: SMTP server address (default: Gmail)
            smtp_port: SMTP port (default: 587)
            sender_email: Sender email address
            sender_password: Sender email password
        """
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = sender_email or os.getenv("SENDER_EMAIL", "noreply@smallbiz.com")
        self.sender_password = sender_password or os.getenv("SENDER_PASSWORD", "")
        # Business owner email to receive copies for tracking
        self.owner_email = os.getenv("BUSINESS_OWNER_EMAIL")
        # Determine mock/real sending: explicit override via `use_mock`, otherwise infer from sender_password
        if use_mock is None:
            self.use_mock = not bool(self.sender_password)
        else:
            self.use_mock = bool(use_mock)

        if self.use_mock:
            print("[EMAIL] Running in MOCK mode. No emails will be sent.")
        else:
            print(f"[EMAIL] Real email sending enabled using {self.smtp_server}:{self.smtp_port} from {self.sender_email}")
    
    def send_order_confirmation(self, order: Dict) -> bool:
        """Send order confirmation email to customer."""
        if not order.get("customer_email"):
            return False
        
        items = json.loads(order["items"])
        items_html = "<ul>"
        for item in items:
            items_html += f"<li>{item['name']} x {item['quantity']} - ${item['price']}</li>"
        items_html += "</ul>"
        
        subject = f"Order Confirmation - {order['order_id']}"
        
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Order Confirmation</h2>
                <p>Dear {order['customer_name']},</p>
                <p>Thank you for your order! Here are the details:</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                    <p><strong>Order ID:</strong> {order['order_id']}</p>
                    <p><strong>Date:</strong> {order['created_at']}</p>
                    <p><strong>Status:</strong> <span style="color: #ff9800; font-weight: bold;">{order['status'].upper()}</span></p>
                </div>
                
                <h3>Items:</h3>
                {items_html}
                
                <div style="background-color: #e8f5e9; padding: 10px; border-radius: 5px; margin-top: 15px;">
                    <p><strong>Total Amount:</strong> <span style="font-size: 18px; color: #2e7d32;">${order['total_amount']:.2f}</span></p>
                </div>
                
                <p style="margin-top: 20px;">You can track your order status anytime on our website.</p>
                <p>Thank you for your business!</p>
                
                <hr style="margin-top: 30px;">
                <p style="color: #999; font-size: 12px;">This is an automated message, please do not reply.</p>
            </body>
        </html>
        """
        
        return self._send_email(
            to_email=order["customer_email"],
            subject=subject,
            body_html=body_html,
            order_id=order["order_id"],
            email_type="order_confirmation"
        )
    
    def send_order_shipped(self, order: Dict, tracking_number: str = None) -> bool:
        """Send order shipped notification email."""
        if not order.get("customer_email"):
            return False
        
        subject = f"Your Order {order['order_id']} Has Been Shipped!"
        
        tracking_info = ""
        if tracking_number:
            tracking_info = f"<p><strong>Tracking Number:</strong> {tracking_number}</p>"
        
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Order Shipped</h2>
                <p>Hi {order['customer_name']},</p>
                <p>Great news! Your order has been shipped.</p>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px;">
                    <p><strong>Order ID:</strong> {order['order_id']}</p>
                    {tracking_info}
                    <p><strong>Estimated Delivery:</strong> In 3-5 business days</p>
                </div>
                
                <p>You can track your shipment using the tracking number provided above.</p>
                <p>Thank you!</p>
                
                <hr style="margin-top: 30px;">
                <p style="color: #999; font-size: 12px;">This is an automated message, please do not reply.</p>
            </body>
        </html>
        """
        
        return self._send_email(
            to_email=order["customer_email"],
            subject=subject,
            body_html=body_html,
            order_id=order["order_id"],
            email_type="order_shipped"
        )
    
    def send_order_delivered(self, order: Dict) -> bool:
        """Send order delivered notification email."""
        if not order.get("customer_email"):
            return False
        
        subject = f"Your Order {order['order_id']} Has Been Delivered"
        
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Order Delivered</h2>
                <p>Hi {order['customer_name']},</p>
                <p>Your order has been delivered!</p>
                
                <div style="background-color: #f1f8e9; padding: 15px; border-radius: 5px;">
                    <p><strong>Order ID:</strong> {order['order_id']}</p>
                    <p><strong>Delivered on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <p>Thank you for shopping with us. We hope you're satisfied with your purchase!</p>
                <p>If you have any questions or concerns, please contact our support team.</p>
                
                <hr style="margin-top: 30px;">
                <p style="color: #999; font-size: 12px;">This is an automated message, please do not reply.</p>
            </body>
        </html>
        """
        
        return self._send_email(
            to_email=order["customer_email"],
            subject=subject,
            body_html=body_html,
            order_id=order["order_id"],
            email_type="order_delivered"
        )
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        order_id: str,
        email_type: str
    ) -> bool:
        """Internal method to send email."""
        
        # Determine recipients (customer + optional owner)
        recipients = [to_email]
        if self.owner_email:
            recipients.append(self.owner_email)

        if self.use_mock:
            print(f"[MOCK EMAIL] To: {to_email}")
            if self.owner_email:
                print(f"[MOCK EMAIL] Cc: {self.owner_email}")
            print(f"[MOCK EMAIL] Subject: {subject}")
            print(f"[MOCK EMAIL] Type: {email_type}")
            # Log mock status for each recipient
            for r in recipients:
                database.log_email(order_id, r, email_type, "mock")
            return True
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = to_email
            if self.owner_email:
                msg["Cc"] = self.owner_email

            # Attach HTML
            msg.attach(MIMEText(body_html, "html"))

            # Send email to all recipients (customer + owner if set)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipients, msg.as_string())

            # Log success for each recipient
            for r in recipients:
                database.log_email(order_id, r, email_type, "sent")

            return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            # Log failed status for each recipient
            for r in recipients:
                database.log_email(order_id, r, email_type, "failed")
            return False


def send_order_notification(order: Dict, event_type: str = "created", tracking_number: str = None, use_real: bool = False) -> bool:
    """
    Send order notification based on event type.
    
    Args:
        order: Order dictionary
        event_type: Type of event ('created', 'shipped', 'delivered')
        tracking_number: Tracking number for shipped orders
    
    Returns:
        Boolean indicating success
    """
    # If `use_real` is True, pass use_mock=False to attempt real sending
    sender = EmailSender(use_mock=not bool(use_real))
    
    if event_type == "created":
        return sender.send_order_confirmation(order)
    elif event_type == "shipped":
        return sender.send_order_shipped(order, tracking_number)
    elif event_type == "delivered":
        return sender.send_order_delivered(order)
    
    return False
