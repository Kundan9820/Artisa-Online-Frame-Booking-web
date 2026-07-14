from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user

from ..extensions import db
from ..models import UploadedPhoto, Size, Order, OrderItem
from ..forms import CustomFrameForm
from ..utils import save_image, generate_order_number, build_whatsapp_order_message, whatsapp_link, notify

custom_bp = Blueprint("custom_frame", __name__)

FRAME_STYLES = ["Classic Wooden", "Modern Slim", "Ornate Antique", "Minimal Black", "Premium Gold", "Rustic Barnwood"]
FRAME_COLORS = ["Brown", "Black", "White", "Golden", "Walnut", "Natural Wood"]


@custom_bp.route("/", methods=["GET", "POST"])
def custom_order():
    form = CustomFrameForm()
    sizes = Size.query.order_by(Size.display_order).all()
    size_choices = [(s.label, s.label) for s in sizes] or [("8x10", "8x10")]
    size_choices.append(("Custom Size", "Custom Size"))
    form.frame_size.choices = size_choices
    form.frame_style.choices = [(s, s) for s in FRAME_STYLES]
    form.frame_color.choices = [(c, c) for c in FRAME_COLORS]

    if form.validate_on_submit():
        try:
            photo_path = save_image(form.photo.data, current_app.config["CUSTOM_UPLOAD_FOLDER"])
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("custom_frame.html", form=form)

        uploaded = UploadedPhoto(
            user_id=current_user.id if current_user.is_authenticated else None,
            file_path=photo_path,
            frame_style=form.frame_style.data,
            frame_color=form.frame_color.data,
            frame_size=form.frame_size.data,
            orientation=form.orientation.data,
            quantity=form.quantity.data,
            special_instructions=form.special_instructions.data,
            customer_name=form.customer_name.data,
            customer_mobile=form.customer_mobile.data,
        )
        db.session.add(uploaded)
        db.session.commit()
        notify("custom_upload", f"New custom frame request from {uploaded.customer_name}",
               link=f"/admin/custom-orders")

        # Redirect to a lightweight confirmation step to collect delivery address
        return redirect(url_for("custom_frame.confirm_custom_order", photo_id=uploaded.id))

    return render_template("custom_frame.html", form=form)


@custom_bp.route("/confirm/<int:photo_id>", methods=["GET", "POST"])
def confirm_custom_order(photo_id):
    uploaded = UploadedPhoto.query.get_or_404(photo_id)

    if request.method == "POST":
        address_line = request.form.get("address_line", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        landmark = request.form.get("landmark", "").strip()

        if not all([address_line, city, state, pincode]):
            flash("Please fill in your complete delivery address.", "danger")
            return render_template("custom_frame_confirm.html", uploaded=uploaded)

        order = Order(
            order_number=generate_order_number(),
            user_id=uploaded.user_id,
            customer_name=uploaded.customer_name,
            customer_mobile=uploaded.customer_mobile,
            address_line=address_line, city=city, state=state,
            pincode=pincode, landmark=landmark,
            subtotal=0, discount_amount=0, delivery_charge=0, total_amount=0,
            special_instructions=uploaded.special_instructions,
        )
        db.session.add(order)
        db.session.flush()

        item = OrderItem(
            order_id=order.id,
            product_name=f"Custom Photo Frame ({uploaded.frame_style}, {uploaded.frame_color}, "
                          f"{uploaded.frame_size}, {uploaded.orientation})",
            size_label=uploaded.frame_size,
            quantity=uploaded.quantity,
            unit_price=0,
            is_custom=True,
            custom_photo_id=uploaded.id,
        )
        db.session.add(item)
        db.session.commit()

        message_text = build_whatsapp_order_message(order, [item])

        # Add a direct link to the uploaded photo so the shop owner can view it
        try:
            photo_url = url_for("static", filename=uploaded.file_path, _external=True)
            message_text += f"\n\n*Uploaded Photo:* {photo_url}"
        except Exception:
            pass
        message_text += ("\n\n_Note: This is a custom frame order. Final price to be confirmed "
                          "by the shop over WhatsApp._")

        wa_link = whatsapp_link(current_app.config["SHOP_WHATSAPP_NUMBER"], message_text)
        order.sent_via_whatsapp = True
        db.session.commit()
        notify("new_order", f"New custom order {order.order_number} from {order.customer_name}")

        return redirect(wa_link)

    return render_template("custom_frame_confirm.html", uploaded=uploaded)
