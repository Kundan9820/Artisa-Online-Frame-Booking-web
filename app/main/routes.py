from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import current_user
from sqlalchemy import or_

from ..extensions import db
from ..models import (
    Product, Category, Slider, Testimonial, Review, Order, Coupon, Size, GalleryImage
)
from ..forms import ContactForm, ReviewForm
from ..utils import notify

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    sliders = Slider.query.filter_by(is_active=True).order_by(Slider.display_order).all()
    featured = Product.query.filter_by(is_available=True, is_featured=True).limit(8).all()
    new_arrivals = Product.query.filter_by(is_available=True, is_new_arrival=True).order_by(
        Product.created_at.desc()).limit(8).all()
    best_sellers = Product.query.filter_by(is_available=True, is_best_seller=True).limit(8).all()
    categories = Category.query.filter_by(is_active=True, parent_id=None).order_by(Category.display_order).all()
    testimonials = Testimonial.query.filter_by(is_active=True).order_by(Testimonial.display_order).all()

    return render_template(
        "index.html",
        sliders=sliders,
        featured=featured,
        new_arrivals=new_arrivals,
        best_sellers=best_sellers,
        categories=categories,
        testimonials=testimonials,
    )


@main_bp.route("/category/<slug>")
def category(slug):
    cat = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
    page = request.args.get("page", 1, type=int)

    query = Product.query.filter_by(category_id=cat.id, is_available=True)

    # Filters
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    color = request.args.get("color")
    material = request.args.get("material")
    sort = request.args.get("sort", "newest")

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if color:
        query = query.filter(Product.frame_color == color)
    if material:
        query = query.filter(Product.frame_material == material)

    if sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    elif sort == "discount":
        query = query.order_by(Product.discount_percent.desc())
    elif sort == "popularity":
        query = query.order_by(Product.view_count.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=current_app.config["PRODUCTS_PER_PAGE"], error_out=False)

    subcategories = Category.query.filter_by(parent_id=cat.id, is_active=True).all()

    # Query args minus 'page', used to build pagination links without
    # accidentally passing 'page' twice to url_for() (once explicitly, once
    # via spreading request.args) — that combination raises a TypeError.
    qs_args = {k: v for k, v in request.args.items() if k != "page"}

    return render_template(
        "category.html", category=cat, products=pagination.items,
        pagination=pagination, subcategories=subcategories, qs_args=qs_args,
    )


@main_bp.route("/product/<slug>")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    product.view_count = (product.view_count or 0) + 1
    db.session.commit()

    related = Product.query.filter(
        Product.category_id == product.category_id, Product.id != product.id
    ).limit(4).all()

    approved_reviews = [r for r in product.reviews if r.is_approved]
    review_form = ReviewForm()

    return render_template(
        "product_detail.html", product=product, related=related,
        reviews=approved_reviews, review_form=review_form,
    )


@main_bp.route("/product/<slug>/review", methods=["POST"])
def submit_review(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    if not current_user.is_authenticated:
        flash("Please log in to write a review.", "warning")
        return redirect(url_for("auth.login"))

    form = ReviewForm()
    if form.validate_on_submit():
        from ..models import Review as ReviewModel
        from ..utils import save_image

        image_path = None
        if form.image.data:
            image_path = save_image(form.image.data, current_app.config["PRODUCT_UPLOAD_FOLDER"])

        review = ReviewModel(
            product_id=product.id, user_id=current_user.id,
            rating=int(form.rating.data), comment=form.comment.data, image=image_path,
        )
        db.session.add(review)
        db.session.commit()
        flash("Thanks! Your review has been submitted and is awaiting approval.", "success")
    else:
        flash("Please correct the errors in your review.", "danger")

    return redirect(url_for("main.product_detail", slug=slug))


@main_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Product.query.filter_by(is_available=True)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like),
                                  Product.subcategory.ilike(like)))

    sort = request.args.get("sort", "newest")
    if sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=current_app.config["PRODUCTS_PER_PAGE"], error_out=False)

    return render_template("search.html", q=q, products=pagination.items, pagination=pagination)


@main_bp.route("/shop")
def shop_all():
    page = request.args.get("page", 1, type=int)
    query = Product.query.filter_by(is_available=True)

    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    color = request.args.get("color")
    material = request.args.get("material")
    category_id = request.args.get("category_id", type=int)
    sort = request.args.get("sort", "newest")

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if color:
        query = query.filter(Product.frame_color == color)
    if material:
        query = query.filter(Product.frame_material == material)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    if sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    elif sort == "discount":
        query = query.order_by(Product.discount_percent.desc())
    elif sort == "popularity":
        query = query.order_by(Product.view_count.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=current_app.config["PRODUCTS_PER_PAGE"], error_out=False)
    all_categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()

    qs_args = {k: v for k, v in request.args.items() if k != "page"}

    return render_template("shop_all.html", products=pagination.items, pagination=pagination,
                            all_categories=all_categories, qs_args=qs_args)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        notify("contact_form", f"New contact message from {form.name.data}")
        flash("Thanks for reaching out! We'll get back to you shortly.", "success")
        return redirect(url_for("main.contact"))
    gallery_images = GalleryImage.query.filter_by(is_active=True).order_by(GalleryImage.display_order).all()
    return render_template("contact.html", form=form, gallery_images=gallery_images)


@main_bp.route("/order/<order_number>/confirmation")
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("order_confirmation.html", order=order)


@main_bp.route("/order/track/<order_number>")
def track_order(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("order_confirmation.html", order=order, tracking=True)
