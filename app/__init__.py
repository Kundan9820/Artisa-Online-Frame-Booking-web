import os
from flask import Flask, render_template
from .config import Config
from .extensions import db, login_manager, bcrypt, csrf, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist
    os.makedirs(app.config["PRODUCT_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CUSTOM_UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .main.routes import main_bp
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .cart.routes import cart_bp
    from .custom_frame.routes import custom_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(custom_bp, url_prefix="/custom-frame")

    # Context processor: make site settings + cart count available in all templates
    from .models import Setting, CartItem, Category
    from datetime import datetime

    @app.context_processor
    def inject_globals():
        settings = Setting.get_settings()
        cart_count = 0
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        except Exception:
            pass

        def nav_categories():
            return Category.query.filter_by(is_active=True, parent_id=None).order_by(Category.display_order).limit(15).all()

        def now_year():
            return datetime.utcnow().year

        return dict(site=settings, cart_count=cart_count, nav_categories=nav_categories, now_year=now_year)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
