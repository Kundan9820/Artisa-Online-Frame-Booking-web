import os
import re
import uuid
import urllib.parse
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from .extensions import db
from .models import Notification


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_image(file_storage, destination_folder):
    """Safely saves an uploaded image with a unique filename. Returns the
    relative static path (e.g. 'uploads/products/xyz.jpg') or None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("File type not allowed. Please upload an image (jpg, png, webp).")

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)
    full_path = os.path.join(destination_folder, safe_name)
    file_storage.save(full_path)

    # Return path relative to /static for use in url_for('static', filename=...)
    static_root = current_app.config["STATIC_FOLDER"]
    rel_path = os.path.relpath(full_path, static_root).replace("\\", "/")
    return rel_path


def generate_order_number():
    return "AF" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:4].upper()


def notify(type_, message, link=None):
    n = Notification(type=type_, message=message, link=link)
    db.session.add(n)
    db.session.commit()
    return n


def build_whatsapp_order_message(order, items):
    """Builds the pre-filled WhatsApp order message text (URL-encoded)."""
    lines = [
        f"*New Order - {current_app.config['SHOP_NAME']}*",
        f"Order No: {order.order_number}",
        f"Time: {order.created_at.strftime('%d %b %Y, %I:%M %p')}",
        "",
        f"*Customer:* {order.customer_name}",
        f"*Phone:* {order.customer_mobile}",
        f"*Address:* {order.address_line}, {order.city}, {order.state} - {order.pincode}",
    ]
    if order.landmark:
        lines.append(f"*Landmark:* {order.landmark}")
    lines.append("")
    lines.append("*Items:*")
    for it in items:
        line = f"- {it.product_name}"
        if it.size_label:
            line += f" ({it.size_label})"
        line += f" x{it.quantity} = Rs. {float(it.unit_price) * it.quantity:.2f}"
        lines.append(line)
        if it.is_custom:
            lines.append("  [Custom photo frame - see uploaded photo in admin panel / attach separately]")

    if order.special_instructions:
        lines.append("")
        lines.append(f"*Special Instructions:* {order.special_instructions}")

    lines.append("")
    lines.append(f"*Subtotal:* Rs. {float(order.subtotal):.2f}")
    if order.discount_amount:
        lines.append(f"*Discount:* -Rs. {float(order.discount_amount):.2f}")
    if order.delivery_charge:
        lines.append(f"*Delivery:* Rs. {float(order.delivery_charge):.2f}")
    lines.append(f"*Total: Rs. {float(order.total_amount):.2f}*")

    text = "\n".join(lines)
    return text


def whatsapp_link(phone_number, message_text):
    encoded = urllib.parse.quote(message_text)
    return f"https://wa.me/{phone_number}?text={encoded}"
