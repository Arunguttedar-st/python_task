from app.services.email_service import send_email
from app.core.config import settings

def notify_low_stock(product_name: str, stock: int, reorder_level: int):
    if stock <= reorder_level:
        subject = f"Low Stock Alert: {product_name}"
        body = (
            f"Attention Administrator,\n\n"
            f"Product '{product_name}' has reached low stock levels.\n"
            f"Current Stock: {stock}\n"
            f"Reorder Level: {reorder_level}\n\n"
            f"Please reorder immediately."
        )
        send_email(to_email=settings.ADMIN_EMAIL, subject=subject, body=body)

def notify_user_registration(username: str, email: str):
    subject = "Welcome to Inventory Management API"
    body = (
        f"Hello {username},\n\n"
        f"Your account has been successfully registered.\n"
        f"Thank you for joining our platform!"
    )
    send_email(to_email=email, subject=subject, body=body)