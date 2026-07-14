import random
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db
from ..models import User, Address, Order, WishlistItem
from ..forms import (
    RegisterForm, LoginForm, ForgotPasswordForm, OTPVerifyForm,
    ResetPasswordForm, AddressForm,
)
from ..utils import notify

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            mobile=form.mobile.data,
        )
        user.set_password(form.password.data)
        user.otp_code = f"{random.randint(100000, 999999)}"
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.session.add(user)
        db.session.commit()

        notify("new_customer", f"New customer registered: {user.full_name}")

        # NOTE: No SMTP is configured in this project by default. In production,
        # send `user.otp_code` to the user's email here (see README "Email/OTP" section).
        flash(
            f"Account created! Your OTP verification code is {user.otp_code} "
            f"(shown here because email sending isn't configured yet).",
            "info",
        )
        return redirect(url_for("auth.verify_otp", email=user.email))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = request.args.get("email", "")
    form = OTPVerifyForm(email=email)

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if not user:
            flash("Account not found.", "danger")
            return redirect(url_for("auth.register"))

        if user.otp_code == form.otp.data and user.otp_expires_at and user.otp_expires_at > datetime.utcnow():
            user.email_verified = True
            user.otp_code = None
            user.otp_expires_at = None
            db.session.commit()
            login_user(user)
            flash("Email verified! Welcome to Artista Frame.", "success")
            return redirect(url_for("main.home"))
        else:
            flash("Invalid or expired OTP. Please try again.", "danger")

    return render_template("auth/verify_otp.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.full_name.split(' ')[0]}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.home"))
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            user.reset_token = secrets.token_urlsafe(32)
            user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            reset_link = url_for("auth.reset_password", token=user.reset_token, _external=True)
            # NOTE: Send `reset_link` by email in production. Shown here directly
            # since SMTP isn't configured by default.
            flash(f"Password reset link (email sending not configured): {reset_link}", "info")
        else:
            flash("If that email exists, a reset link has been generated.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm(token=token)
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expires_at = None
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/profile")
@login_required
def profile():
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    wishlist = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template("auth/profile.html", addresses=addresses, orders=orders, wishlist=wishlist)


@auth_bp.route("/address/add", methods=["GET", "POST"])
@login_required
def add_address():
    form = AddressForm()
    if form.validate_on_submit():
        if form.is_default.data:
            Address.query.filter_by(user_id=current_user.id).update({"is_default": False})
        addr = Address(
            user_id=current_user.id, full_name=form.full_name.data, mobile=form.mobile.data,
            email=form.email.data, address_line=form.address_line.data, city=form.city.data,
            state=form.state.data, pincode=form.pincode.data, landmark=form.landmark.data,
            is_default=form.is_default.data,
        )
        db.session.add(addr)
        db.session.commit()
        flash("Address saved.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/address_form.html", form=form)


@auth_bp.route("/address/<int:address_id>/delete", methods=["POST"])
@login_required
def delete_address(address_id):
    addr = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    db.session.delete(addr)
    db.session.commit()
    flash("Address removed.", "info")
    return redirect(url_for("auth.profile"))


@auth_bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):
    existing = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Removed from wishlist.", "info")
    else:
        db.session.add(WishlistItem(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        flash("Added to wishlist.", "success")
    return redirect(request.referrer or url_for("main.home"))
