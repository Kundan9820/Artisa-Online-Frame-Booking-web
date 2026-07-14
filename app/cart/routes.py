from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user

from ..extensions import db
from ..models import CartItem, Product, Coupon, Order, OrderItem, Address
from ..forms import AddressForm, CouponApplyForm
from ..utils import generate_order_number, build_whatsapp_order_message, whatsapp_link, notify

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/")
@login_required
def view_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum((i.subtotal for i in items), 0)
    coupon_code = session.get("coupon_code")
    discount_amount = Decimal("0")
    coupon = None
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon:
            valid, msg = coupon.is_valid(order_amount=subtotal)
            if valid:
                discount_amount = round(Decimal(str(subtotal)) * coupon.discount_percent / 100, 2)
                if coupon.max_discount_amount:
                    discount_amount = min(discount_amount, coupon.max_discount_amount)
            else:
                flash(f"Coupon no longer valid: {msg}", "warning")
                session.pop("coupon_code", None)
                coupon = None

    total = round(Decimal(str(subtotal)) - discount_amount, 2)
    coupon_form = CouponApplyForm()

    return render_template(
        "cart.html", items=items, subtotal=subtotal, discount_amount=discount_amount,
        total=total, coupon=coupon, coupon_form=coupon_form,
    )


@cart_bp.route("/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    size_label = request.form.get("size_label")
    quantity = max(1, request.form.get("quantity", 1, type=int))

    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product.id, size_label=size_label
    ).first()
    if existing:
        existing.quantity += quantity
    else:
        db.session.add(CartItem(
            user_id=current_user.id, product_id=product.id,
            size_label=size_label, quantity=quantity,
        ))
    db.session.commit()
    flash(f"{product.name} added to cart.", "success")
    return redirect(request.referrer or url_for("cart.view_cart"))


@cart_bp.route("/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    quantity = request.form.get("quantity", 1, type=int)
    if quantity and quantity > 0:
        item.quantity = quantity
        db.session.commit()
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/apply-coupon", methods=["POST"])
@login_required
def apply_coupon():
    form = CouponApplyForm()
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        coupon = Coupon.query.filter_by(code=code).first()
        if not coupon:
            flash("Invalid coupon code.", "danger")
        else:
            items = CartItem.query.filter_by(user_id=current_user.id).all()
            subtotal = sum((i.subtotal for i in items), 0)
            valid, msg = coupon.is_valid(order_amount=subtotal)
            if valid:
                session["coupon_code"] = code
                flash(f"Coupon '{code}' applied!", "success")
            else:
                flash(msg, "danger")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("main.home"))

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    form = AddressForm()

    if form.validate_on_submit():
        subtotal = sum((i.subtotal for i in items), 0)

        coupon_code = session.get("coupon_code")
        discount_amount = Decimal("0")
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code).first()
            if coupon:
                valid, _ = coupon.is_valid(order_amount=subtotal)
                if valid:
                    discount_amount = round(Decimal(str(subtotal)) * coupon.discount_percent / 100, 2)
                    if coupon.max_discount_amount:
                        discount_amount = min(discount_amount, coupon.max_discount_amount)
                    coupon.times_used = (coupon.times_used or 0) + 1

        settings_delivery = 0
        total = round(Decimal(str(subtotal)) - discount_amount + Decimal(str(settings_delivery)), 2)

        order = Order(
            order_number=generate_order_number(),
            user_id=current_user.id,
            customer_name=form.full_name.data,
            customer_mobile=form.mobile.data,
            customer_email=form.email.data,
            address_line=form.address_line.data,
            city=form.city.data,
            state=form.state.data,
            pincode=form.pincode.data,
            landmark=form.landmark.data,
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_charge=settings_delivery,
            total_amount=total,
            coupon_code=coupon_code,
            special_instructions=request.form.get("special_instructions"),
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for ci in items:
            db.session.add(OrderItem(
                order_id=order.id, product_id=ci.product_id, product_name=ci.product.name,
                size_label=ci.size_label, quantity=ci.quantity, unit_price=ci.product.final_price,
            ))

        # Clear cart + coupon session
        for ci in items:
            db.session.delete(ci)
        session.pop("coupon_code", None)

        db.session.commit()
        notify("new_order", f"New order {order.order_number} from {order.customer_name}", link=f"/admin/orders/{order.id}")

        message_text = build_whatsapp_order_message(order, order.items)
        wa_link = whatsapp_link(current_app.config["SHOP_WHATSAPP_NUMBER"], message_text)

        order.sent_via_whatsapp = True
        db.session.commit()

        return redirect(wa_link)

    return render_template("checkout.html", items=items, addresses=addresses, form=form)
