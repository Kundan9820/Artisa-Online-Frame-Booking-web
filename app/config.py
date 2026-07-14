import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

    # --- Database ---
    # Default: SQLite (zero config, great for local dev / quick deploy).
    # For MySQL in production, set DATABASE_URL, e.g.:
    #   mysql+pymysql://user:password@localhost:3306/artista_frame
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'artista_frame.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads ---
    STATIC_FOLDER = os.path.join(basedir, "app", "static")
    PRODUCT_UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, "uploads", "products")
    CUSTOM_UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, "uploads", "custom")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload

    # --- Shop info ---
    SHOP_NAME = "Artista Frame"
    SHOP_OWNER = "Chandan Kumar Saw"
    SHOP_WHATSAPP_NUMBER = os.environ.get("SHOP_WHATSAPP_NUMBER", "919006090994")  # no + or spaces
    SHOP_INSTAGRAM = "https://www.instagram.com/reel/Dao1WB9SZbt/?igsh=enI1OWh0aWgzeDMz"
    SHOP_ADDRESS = "Oppo Hi-tech Nursery, Besides Lalu Hotel & City Care Medical, Canary Hill Road, Dipugarha, Hazaribagh, Jharkhand 825301"
    SHOP_LATITUDE = "24.0049515"
    SHOP_LONGITUDE = "85.3816533"

    # --- Session ---
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # --- Pagination ---
    PRODUCTS_PER_PAGE = 12
