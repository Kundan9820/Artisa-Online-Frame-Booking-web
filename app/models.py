import json
from datetime import datetime
from flask_login import UserMixin
from .extensions import db, bcrypt


# ---------------------------------------------------------------------------
# Users & Auth
# ---------------------------------------------------------------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    mobile = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_account = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(10))
    otp_expires_at = db.Column(db.DateTime)
    reset_token = db.Column(db.String(255))
    reset_token_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    addresses = db.relationship("Address", backref="user", lazy=True, cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="user", lazy=True)
    cart_items = db.relationship("CartItem", backref="user", lazy=True, cascade="all, delete-orphan")
    wishlist_items = db.relationship("WishlistItem", backref="user", lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password):
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150))
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    landmark = db.Column(db.String(150))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(140), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship("Category", backref=db.backref("parent", remote_side=[id]))
    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Size(db.Model):
    __tablename__ = "sizes"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), nullable=False, unique=True)  # e.g. "8x10"
    is_custom = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Integer, default=0)
    stock = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    subcategory = db.Column(db.String(120))
    frame_material = db.Column(db.String(100))
    frame_color = db.Column(db.String(60))
    delivery_time_days = db.Column(db.String(50), default="3-5 days")
    is_available = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_new_arrival = db.Column(db.Boolean, default=False)
    is_best_seller = db.Column(db.Boolean, default=False)
    is_clearance = db.Column(db.Boolean, default=False)
    is_customizable = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship(
        "ProductImage", backref="product", lazy=True, cascade="all, delete-orphan",
        order_by="ProductImage.display_order, ProductImage.id",
    )
    reviews = db.relationship("Review", backref="product", lazy=True, cascade="all, delete-orphan")
    sizes = db.relationship("Size", secondary="product_sizes")

    @property
    def final_price(self):
        if self.discount_percent:
            return round(float(self.price) * (1 - self.discount_percent / 100), 2)
        return float(self.price)

    @property
    def average_rating(self):
        approved = [r.rating for r in self.reviews if r.is_approved]
        if not approved:
            return 0
        return round(sum(approved) / len(approved), 1)

    @property
    def primary_image(self):
        if not self.images:
            return "img/placeholder-frame.svg"
        for img in self.images:
            if img.is_primary:
                return img.image_path
        # No image explicitly marked primary (shouldn't normally happen) -
        # fall back to the first one rather than showing a placeholder.
        return self.images[0].image_path

    def __repr__(self):
        return f"<Product {self.name}>"


product_sizes = db.Table(
    "product_sizes",
    db.Column("product_id", db.Integer, db.ForeignKey("products.id"), primary_key=True),
    db.Column("size_id", db.Integer, db.ForeignKey("sizes.id"), primary_key=True),
)


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)


# ---------------------------------------------------------------------------
# Cart / Wishlist
# ---------------------------------------------------------------------------
class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size_label = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")

    @property
    def subtotal(self):
        return round(self.product.final_price * self.quantity, 2)


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
ORDER_STATUSES = [
    "Pending", "Accepted", "Processing", "Printing",
    "Framing", "Packed", "Delivered", "Cancelled",
]


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    customer_name = db.Column(db.String(150), nullable=False)
    customer_mobile = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(150))
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    landmark = db.Column(db.String(150))

    subtotal = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    delivery_charge = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), default=0)
    coupon_code = db.Column(db.String(50))

    status = db.Column(db.String(30), default="Pending")
    sent_via_whatsapp = db.Column(db.Boolean, default=False)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product_name = db.Column(db.String(200), nullable=False)
    size_label = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    is_custom = db.Column(db.Boolean, default=False)
    custom_photo_id = db.Column(db.Integer, db.ForeignKey("uploaded_photos.id"), nullable=True)

    product = db.relationship("Product")


# ---------------------------------------------------------------------------
# Custom Photo Frame Requests
# ---------------------------------------------------------------------------
class UploadedPhoto(db.Model):
    __tablename__ = "uploaded_photos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    frame_style = db.Column(db.String(100))
    frame_color = db.Column(db.String(60))
    frame_size = db.Column(db.String(50))
    orientation = db.Column(db.String(20))  # Portrait / Landscape
    quantity = db.Column(db.Integer, default=1)
    special_instructions = db.Column(db.Text)
    customer_name = db.Column(db.String(150))
    customer_mobile = db.Column(db.String(20))
    status = db.Column(db.String(30), default="New")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", backref="custom_photo", lazy=True)


# ---------------------------------------------------------------------------
# Reviews / Coupons / Notifications / Content
# ---------------------------------------------------------------------------
class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    image = db.Column(db.String(255))
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    max_discount_amount = db.Column(db.Numeric(10, 2))
    min_order_amount = db.Column(db.Numeric(10, 2), default=0)
    valid_from = db.Column(db.DateTime)
    valid_until = db.Column(db.DateTime)
    usage_limit = db.Column(db.Integer)
    times_used = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def is_valid(self, order_amount=0):
        now = datetime.utcnow()
        if not self.is_active:
            return False, "Coupon is not active"
        if self.valid_from and now < self.valid_from:
            return False, "Coupon not yet valid"
        if self.valid_until and now > self.valid_until:
            return False, "Coupon has expired"
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False, "Coupon usage limit reached"
        if order_amount < float(self.min_order_amount or 0):
            return False, f"Minimum order amount is Rs. {self.min_order_amount}"
        return True, "OK"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # new_order, new_customer, custom_upload, low_stock
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)


class Slider(db.Model):
    __tablename__ = "sliders"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    subtitle = db.Column(db.String(255))
    image = db.Column(db.String(255), nullable=False)
    link_url = db.Column(db.String(255))
    button_text = db.Column(db.String(60), default="Shop Now")
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)


class GalleryImage(db.Model):
    """Photos of the physical shop / workshop / team, managed by the admin
    and shown in the 'Our Shop' gallery section on the Contact page."""
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)

    _cache = None

    @classmethod
    def get_settings(cls):
        """Return a dict-like object of all settings, with sensible defaults."""
        defaults = {
            "shop_name": "Artista Frame",
            "shop_tagline": "Frame Every Memory, Beautifully",
            "whatsapp_number": "919006090994",
            "instagram_url": "https://www.instagram.com/reel/Dao1WB9SZbt/?igsh=enI1OWh0aWgzeDMz",
            "address": "Oppo Hi-tech Nursery, Besides Lalu Hotel & City Care Medical, Canary Hill Road, Dipugarha, Hazaribagh, Jharkhand 825301",
            "shop_latitude": "24.0049515",
            "shop_longitude": "85.3816533",
            "google_maps_url": "https://maps.google.com/?q=24.0049515,85.3816533",
            "business_hours": "Mon - Sat: 10:00 AM - 8:00 PM",
            "delivery_charge": "0",
            "free_delivery_above": "999",
        }
        try:
            rows = {s.key: s.value for s in cls.query.all()}
            defaults.update(rows)
        except Exception:
            pass
        return defaults


class Inventory(db.Model):
    """Simple stock-movement ledger, separate from Product.stock for auditing."""
    __tablename__ = "inventory_logs"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    change = db.Column(db.Integer, nullable=False)  # +ve restock, -ve sale
    reason = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")
