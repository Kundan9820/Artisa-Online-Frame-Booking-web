import csv
import io
import os
from functools import wraps
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    current_app, abort, send_file, Response
)
from flask_login import login_required, current_user, login_user, logout_user

from ..extensions import db
from ..models import (
    User, Product, ProductImage, Category, Size, Order, OrderItem, UploadedPhoto,
    Review, Coupon, Notification, Testimonial, Slider, Setting, CartItem, GalleryImage
)
from ..forms import (
    ProductForm, CategoryForm, SizeForm, CouponForm, SliderForm, TestimonialForm,
    AdminLoginForm, GalleryImageForm
)
from ..utils import save_image, slugify, notify

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.is_admin and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin credentials.", "danger")

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout")
@admin_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


def _dashboard_analytics():
    """Compute chart-ready data for the dashboard. Done in Python (not raw SQL
    date-truncation) so it works identically on SQLite and MySQL."""
    from collections import OrderedDict, defaultdict
    import calendar

    today = datetime.utcnow().date()

    # --- Daily sales & orders for the last 30 days ---
    start_30 = today - timedelta(days=29)
    daily_revenue = OrderedDict()
    daily_orders = OrderedDict()
    for i in range(30):
        d = start_30 + timedelta(days=i)
        daily_revenue[d] = 0.0
        daily_orders[d] = 0

    recent_orders_30d = Order.query.filter(
        Order.created_at >= datetime.combine(start_30, datetime.min.time()),
        Order.status != "Cancelled",
    ).all()
    for o in recent_orders_30d:
        d = o.created_at.date()
        if d in daily_revenue:
            daily_revenue[d] += float(o.total_amount or 0)
            daily_orders[d] += 1

    sales_labels = [d.strftime("%d %b") for d in daily_revenue.keys()]
    sales_revenue = [round(v, 2) for v in daily_revenue.values()]
    sales_order_counts = list(daily_orders.values())

    # --- Monthly revenue for the last 6 months ---
    month_keys = []
    cursor = today.replace(day=1)
    for _ in range(6):
        month_keys.append((cursor.year, cursor.month))
        prev_month = cursor.month - 1 or 12
        prev_year = cursor.year - 1 if cursor.month == 1 else cursor.year
        cursor = cursor.replace(year=prev_year, month=prev_month, day=1)
    month_keys.reverse()

    monthly_revenue = OrderedDict((mk, 0.0) for mk in month_keys)
    range_start = datetime(month_keys[0][0], month_keys[0][1], 1)
    all_orders_6m = Order.query.filter(
        Order.created_at >= range_start, Order.status != "Cancelled"
    ).all()
    for o in all_orders_6m:
        key = (o.created_at.year, o.created_at.month)
        if key in monthly_revenue:
            monthly_revenue[key] += float(o.total_amount or 0)

    revenue_labels = [f"{calendar.month_abbr[m]} {y}" for (y, m) in month_keys]
    revenue_values = [round(v, 2) for v in monthly_revenue.values()]

    # --- Top 5 products by quantity sold (all-time) ---
    product_qty = defaultdict(int)
    for item in OrderItem.query.filter(OrderItem.product_id.isnot(None)).all():
        product_qty[item.product_name] += item.quantity or 0
    top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:5]
    top_product_labels = [p[0] for p in top_products]
    top_product_values = [p[1] for p in top_products]

    # --- New customer signups per month (last 6 months) ---
    monthly_signups = OrderedDict((mk, 0) for mk in month_keys)
    new_users = User.query.filter(
        User.is_admin == False, User.created_at >= range_start
    ).all()
    for u in new_users:
        key = (u.created_at.year, u.created_at.month)
        if key in monthly_signups:
            monthly_signups[key] += 1
    signup_values = list(monthly_signups.values())

    # --- Order status breakdown (all-time) ---
    status_counts = OrderedDict((s, 0) for s in ORDER_STATUSES)
    for status, count in db.session.query(Order.status, db.func.count(Order.id)).group_by(Order.status).all():
        if status in status_counts:
            status_counts[status] = count
    status_labels = list(status_counts.keys())
    status_values = list(status_counts.values())

    return dict(
        sales_labels=sales_labels, sales_revenue=sales_revenue, sales_order_counts=sales_order_counts,
        revenue_labels=revenue_labels, revenue_values=revenue_values,
        top_product_labels=top_product_labels, top_product_values=top_product_values,
        signup_labels=revenue_labels, signup_values=signup_values,
        status_labels=status_labels, status_values=status_values,
    )


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    today = datetime.utcnow().date()
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).count()
    total_sales = db.session.query(db.func.coalesce(db.func.sum(Order.total_amount), 0)).filter(
        Order.status != "Cancelled").scalar()
    total_products = Product.query.count()
    total_customers = User.query.filter_by(is_admin=False).count()
    total_categories = Category.query.count()
    pending_orders = Order.query.filter_by(status="Pending").count()
    completed_orders = Order.query.filter_by(status="Delivered").count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    recent_activity = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    low_stock = Product.query.filter(Product.stock <= 5, Product.is_available == True).all()

    analytics = _dashboard_analytics()

    return render_template(
        "admin/dashboard.html", today_orders=today_orders, total_sales=total_sales,
        total_products=total_products, total_customers=total_customers,
        total_categories=total_categories, pending_orders=pending_orders,
        completed_orders=completed_orders, recent_orders=recent_orders,
        recent_activity=recent_activity, low_stock=low_stock,
        analytics=analytics,
    )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
@admin_bp.route("/products")
@admin_required
def products():
    q = request.args.get("q", "")
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    items = query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items, q=q)


def _populate_category_choices(form):
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]


def _populate_size_choices(form):
    form.sizes.choices = [(s.id, s.label) for s in Size.query.order_by(Size.display_order).all()]


@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    form = ProductForm()
    _populate_category_choices(form)
    _populate_size_choices(form)

    if form.validate_on_submit():
        if Product.query.filter_by(sku=form.sku.data).first():
            flash("A product with this SKU already exists.", "danger")
            return render_template("admin/product_form.html", form=form, product=None)

        slug = slugify(form.name.data) + "-" + form.sku.data.lower()
        product = Product(
            name=form.name.data, sku=form.sku.data, slug=slug, description=form.description.data,
            price=form.price.data, discount_percent=form.discount_percent.data or 0,
            stock=form.stock.data, category_id=form.category_id.data, subcategory=form.subcategory.data,
            frame_material=form.frame_material.data, frame_color=form.frame_color.data,
            delivery_time_days=form.delivery_time_days.data, is_available=form.is_available.data,
            is_featured=form.is_featured.data, is_new_arrival=form.is_new_arrival.data,
            is_best_seller=form.is_best_seller.data, is_clearance=form.is_clearance.data,
            is_customizable=form.is_customizable.data,
        )
        db.session.add(product)
        db.session.flush()

        if form.sizes.data:
            product.sizes = Size.query.filter(Size.id.in_(form.sizes.data)).all()

        if form.images.data:
            path = save_image(form.images.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])
            if path:
                db.session.add(ProductImage(product_id=product.id, image_path=path, is_primary=True))

        db.session.commit()
        flash("Product added successfully.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", form=form, product=None)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    # IMPORTANT: Product.images (the relationship, a list of ProductImage rows)
    # has the same name as the form's `images` FileField. WTForms' obj= binding
    # matches fields to object attributes by name, so on GET (or when no new
    # file is part of this request) it populates the FileField's data with
    # that list of existing image objects instead of leaving it empty. Only
    # clear it in that specific case — if a real file was uploaded in this
    # request, WTForms has already correctly overwritten .data with that
    # FileStorage by the time we get here, and we must not discard it.
    if isinstance(form.images.data, list):
        form.images.data = None
    _populate_category_choices(form)
    _populate_size_choices(form)

    if request.method == "GET":
        form.category_id.data = product.category_id
        form.sizes.data = [s.id for s in product.sizes]

    if form.validate_on_submit():
        product.name = form.name.data
        product.sku = form.sku.data
        product.description = form.description.data
        product.price = form.price.data
        product.discount_percent = form.discount_percent.data or 0
        product.stock = form.stock.data
        product.category_id = form.category_id.data
        product.subcategory = form.subcategory.data
        product.frame_material = form.frame_material.data
        product.frame_color = form.frame_color.data
        product.delivery_time_days = form.delivery_time_days.data
        product.is_available = form.is_available.data
        product.is_featured = form.is_featured.data
        product.is_new_arrival = form.is_new_arrival.data
        product.is_best_seller = form.is_best_seller.data
        product.is_clearance = form.is_clearance.data
        product.is_customizable = form.is_customizable.data
        product.sizes = Size.query.filter(Size.id.in_(form.sizes.data)).all() if form.sizes.data else []

        if form.images.data:
            path = save_image(form.images.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])
            if path:
                # A newly uploaded photo should become the one shown across the
                # site. Previously, uploading a replacement photo for a product
                # that already had one just appended it as a *second* image
                # without ever marking it primary, so the old photo kept showing
                # everywhere (home page, category pages, product page) even
                # though the upload itself "succeeded".
                for existing in product.images:
                    existing.is_primary = False
                db.session.add(ProductImage(product_id=product.id, image_path=path, is_primary=True))

        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", form=form, product=product)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/image/<int:image_id>/delete", methods=["POST"])
@admin_required
def delete_product_image(image_id):
    image = ProductImage.query.get_or_404(image_id)
    product_id = image.product_id
    was_primary = image.is_primary
    db.session.delete(image)
    db.session.flush()

    if was_primary:
        remaining = ProductImage.query.filter_by(product_id=product_id).order_by(
            ProductImage.display_order, ProductImage.id).first()
        if remaining:
            remaining.is_primary = True

    db.session.commit()
    flash("Image removed.", "info")
    return redirect(url_for("admin.edit_product", product_id=product_id))


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@admin_bp.route("/categories")
@admin_required
def categories():
    items = Category.query.order_by(Category.display_order, Category.name).all()
    return render_template("admin/categories.html", categories=items)


@admin_bp.route("/categories/add", methods=["GET", "POST"])
@admin_required
def add_category():
    form = CategoryForm()
    form.parent_id.choices = [(0, "-- None (Top Level) --")] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]

    if form.validate_on_submit():
        slug = slugify(form.name.data)
        if Category.query.filter_by(slug=slug).first():
            flash("A category with this name already exists.", "danger")
            return render_template("admin/category_form.html", form=form, category=None)

        image_path = None
        if form.image.data:
            image_path = save_image(form.image.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])

        cat = Category(
            name=form.name.data, slug=slug, description=form.description.data,
            image=image_path, parent_id=form.parent_id.data or None, is_active=form.is_active.data,
        )
        db.session.add(cat)
        db.session.commit()
        flash("Category created.", "success")
        return redirect(url_for("admin.categories"))

    return render_template("admin/category_form.html", form=form, category=None)


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category(category_id):
    cat = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=cat)
    # Same class of bug as edit_product: cat.image is a plain string (the
    # existing image path), and WTForms' obj= binding would load that string
    # into the image FileField's data when no new file is part of this
    # request. Only clear it in that case — if a file WAS uploaded, WTForms
    # has already correctly overwritten .data with that FileStorage.
    if isinstance(form.image.data, str):
        form.image.data = None
    form.parent_id.choices = [(0, "-- None (Top Level) --")] + [
        (c.id, c.name) for c in Category.query.filter(Category.id != cat.id).order_by(Category.name).all()
    ]
    if request.method == "GET":
        form.parent_id.data = cat.parent_id or 0

    if form.validate_on_submit():
        cat.name = form.name.data
        cat.description = form.description.data
        cat.parent_id = form.parent_id.data or None
        cat.is_active = form.is_active.data
        if form.image.data:
            cat.image = save_image(form.image.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])
        db.session.commit()
        flash("Category updated.", "success")
        return redirect(url_for("admin.categories"))

    return render_template("admin/category_form.html", form=form, category=cat)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    if cat.products:
        flash("Cannot delete a category that still has products. Move or delete its products first.", "danger")
        return redirect(url_for("admin.categories"))
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("admin.categories"))


# ---------------------------------------------------------------------------
# Sizes
# ---------------------------------------------------------------------------
@admin_bp.route("/sizes", methods=["GET", "POST"])
@admin_required
def sizes():
    form = SizeForm()
    if form.validate_on_submit():
        if Size.query.filter_by(label=form.label.data).first():
            flash("This size already exists.", "danger")
        else:
            db.session.add(Size(label=form.label.data, is_custom=form.is_custom.data))
            db.session.commit()
            flash("Size added.", "success")
        return redirect(url_for("admin.sizes"))

    items = Size.query.order_by(Size.display_order).all()
    return render_template("admin/sizes.html", sizes=items, form=form)


@admin_bp.route("/sizes/<int:size_id>/delete", methods=["POST"])
@admin_required
def delete_size(size_id):
    size = Size.query.get_or_404(size_id)
    db.session.delete(size)
    db.session.commit()
    return redirect(url_for("admin.sizes"))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
from ..models import ORDER_STATUSES  # noqa: E402


@admin_bp.route("/orders")
@admin_required
def orders():
    status = request.args.get("status", "")
    query = Order.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=items, statuses=ORDER_STATUSES, current_status=status)


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/order_detail.html", order=order, statuses=ORDER_STATUSES)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in ORDER_STATUSES:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.order_number} marked as {new_status}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/orders/export")
@admin_required
def export_orders():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order Number", "Date", "Customer", "Mobile", "Address", "City", "State", "Pincode",
        "Subtotal", "Discount", "Delivery", "Total", "Status", "Items"
    ])
    for o in Order.query.order_by(Order.created_at.desc()).all():
        item_summary = "; ".join(f"{i.product_name} x{i.quantity}" for i in o.items)
        writer.writerow([
            o.order_number, o.created_at.strftime("%Y-%m-%d %H:%M"), o.customer_name, o.customer_mobile,
            o.address_line, o.city, o.state, o.pincode, o.subtotal, o.discount_amount,
            o.delivery_charge, o.total_amount, o.status, item_summary,
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=artista_frame_orders.csv"
    return response


# ---------------------------------------------------------------------------
# Custom Photo Frame Requests
# ---------------------------------------------------------------------------
@admin_bp.route("/custom-orders")
@admin_required
def custom_orders():
    items = UploadedPhoto.query.order_by(UploadedPhoto.created_at.desc()).all()
    return render_template("admin/custom_orders.html", uploads=items)


@admin_bp.route("/custom-orders/<int:photo_id>/status", methods=["POST"])
@admin_required
def update_custom_status(photo_id):
    photo = UploadedPhoto.query.get_or_404(photo_id)
    photo.status = request.form.get("status", photo.status)
    db.session.commit()
    return redirect(url_for("admin.custom_orders"))


@admin_bp.route("/custom-orders/download-all")
@admin_required
def download_custom_photos():
    """Provides a listing page with direct download links (zipping requires
    extra deps not included by default; each photo can be downloaded individually)."""
    items = UploadedPhoto.query.order_by(UploadedPhoto.created_at.desc()).all()
    return render_template("admin/custom_orders.html", uploads=items, download_mode=True)


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
@admin_bp.route("/coupons")
@admin_required
def coupons():
    items = Coupon.query.order_by(Coupon.id.desc()).all()
    return render_template("admin/coupons.html", coupons=items)


@admin_bp.route("/coupons/add", methods=["GET", "POST"])
@admin_required
def add_coupon():
    form = CouponForm()
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        if Coupon.query.filter_by(code=code).first():
            flash("A coupon with this code already exists.", "danger")
        else:
            db.session.add(Coupon(
                code=code, discount_percent=form.discount_percent.data,
                max_discount_amount=form.max_discount_amount.data,
                min_order_amount=form.min_order_amount.data or 0,
                usage_limit=form.usage_limit.data, is_active=form.is_active.data,
            ))
            db.session.commit()
            flash("Coupon created.", "success")
        return redirect(url_for("admin.coupons"))
    return render_template("admin/coupon_form.html", form=form, coupon=None)


@admin_bp.route("/coupons/<int:coupon_id>/delete", methods=["POST"])
@admin_required
def delete_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted.", "info")
    return redirect(url_for("admin.coupons"))


# ---------------------------------------------------------------------------
# Homepage Slider
# ---------------------------------------------------------------------------
@admin_bp.route("/sliders")
@admin_required
def sliders():
    items = Slider.query.order_by(Slider.display_order).all()
    return render_template("admin/sliders.html", sliders=items)


@admin_bp.route("/sliders/add", methods=["GET", "POST"])
@admin_required
def add_slider():
    form = SliderForm()
    if form.validate_on_submit():
        if not form.image.data:
            flash("Slider image is required.", "danger")
        else:
            path = save_image(form.image.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])
            db.session.add(Slider(
                title=form.title.data, subtitle=form.subtitle.data, image=path,
                link_url=form.link_url.data, button_text=form.button_text.data or "Shop Now",
                is_active=form.is_active.data,
            ))
            db.session.commit()
            flash("Slider added.", "success")
            return redirect(url_for("admin.sliders"))
    return render_template("admin/slider_form.html", form=form)


@admin_bp.route("/sliders/<int:slider_id>/delete", methods=["POST"])
@admin_required
def delete_slider(slider_id):
    s = Slider.query.get_or_404(slider_id)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for("admin.sliders"))


# ---------------------------------------------------------------------------
# Shop Gallery (photos of the physical shop / workshop)
# ---------------------------------------------------------------------------
@admin_bp.route("/gallery")
@admin_required
def gallery():
    items = GalleryImage.query.order_by(GalleryImage.display_order, GalleryImage.id).all()
    return render_template("admin/gallery.html", images=items)


@admin_bp.route("/gallery/add", methods=["GET", "POST"])
@admin_required
def add_gallery_image():
    form = GalleryImageForm()
    if form.validate_on_submit():
        path = save_image(form.image.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])
        if not path:
            flash("Please choose a photo to upload.", "danger")
        else:
            db.session.add(GalleryImage(image=path, caption=form.caption.data, is_active=form.is_active.data))
            db.session.commit()
            flash("Shop photo added.", "success")
            return redirect(url_for("admin.gallery"))
    return render_template("admin/gallery_form.html", form=form)


@admin_bp.route("/gallery/<int:image_id>/delete", methods=["POST"])
@admin_required
def delete_gallery_image(image_id):
    img = GalleryImage.query.get_or_404(image_id)
    db.session.delete(img)
    db.session.commit()
    flash("Photo removed.", "info")
    return redirect(url_for("admin.gallery"))


# ---------------------------------------------------------------------------
# Testimonials
# ---------------------------------------------------------------------------
@admin_bp.route("/testimonials")
@admin_required
def testimonials():
    items = Testimonial.query.order_by(Testimonial.display_order).all()
    return render_template("admin/testimonials.html", testimonials=items)


@admin_bp.route("/testimonials/add", methods=["GET", "POST"])
@admin_required
def add_testimonial():
    form = TestimonialForm()
    if form.validate_on_submit():
        image_path = save_image(form.image.data, current_app.config["PRODUCT_UPLOAD_FOLDER"]) if form.image.data else None
        db.session.add(Testimonial(
            customer_name=form.customer_name.data, rating=int(form.rating.data),
            comment=form.comment.data, image=image_path, is_active=form.is_active.data,
        ))
        db.session.commit()
        flash("Testimonial added.", "success")
        return redirect(url_for("admin.testimonials"))
    return render_template("admin/testimonial_form.html", form=form)


@admin_bp.route("/testimonials/<int:t_id>/delete", methods=["POST"])
@admin_required
def delete_testimonial(t_id):
    t = Testimonial.query.get_or_404(t_id)
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("admin.testimonials"))


# ---------------------------------------------------------------------------
# Reviews moderation
# ---------------------------------------------------------------------------
@admin_bp.route("/reviews")
@admin_required
def reviews():
    items = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=items)


@admin_bp.route("/reviews/<int:review_id>/approve", methods=["POST"])
@admin_required
def approve_review(review_id):
    r = Review.query.get_or_404(review_id)
    r.is_approved = True
    db.session.commit()
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@admin_required
def delete_review(review_id):
    r = Review.query.get_or_404(review_id)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for("admin.reviews"))


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@admin_bp.route("/customers")
@admin_required
def customers():
    items = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template("admin/customers.html", customers=items)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
@admin_bp.route("/notifications")
@admin_required
def notifications():
    items = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    Notification.query.update({"is_read": True})
    db.session.commit()
    return render_template("admin/notifications.html", notifications=items)


# ---------------------------------------------------------------------------
# Website Settings
# ---------------------------------------------------------------------------
@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        for key, value in request.form.items():
            if key == "csrf_token":
                continue
            row = Setting.query.filter_by(key=key).first()
            if row:
                row.value = value
            else:
                db.session.add(Setting(key=key, value=value))
        db.session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("admin.settings"))

    current = Setting.get_settings()
    return render_template("admin/settings.html", settings=current)


# ---------------------------------------------------------------------------
# Backup / Restore (SQLite convenience; for MySQL use mysqldump - see README)
# ---------------------------------------------------------------------------
@admin_bp.route("/backup")
@admin_required
def backup_database():
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite"):
        flash("Direct backup download is only available for SQLite. For MySQL, use mysqldump (see README).", "warning")
        return redirect(url_for("admin.dashboard"))

    db_path = uri.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        flash("Database file not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    return send_file(db_path, as_attachment=True, download_name="artista_frame_backup.db")
