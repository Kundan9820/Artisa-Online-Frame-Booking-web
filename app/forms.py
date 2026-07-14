from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, TextAreaField, IntegerField, DecimalField,
    SelectField, BooleanField, SelectMultipleField, HiddenField,
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional, Regexp


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(2, 150)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    mobile = StringField("Mobile Number", validators=[
        DataRequired(), Regexp(r"^\+?\d{10,15}$", message="Enter a valid mobile number")
    ])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Registered Email", validators=[DataRequired(), Email()])


class OTPVerifyForm(FlaskForm):
    email = HiddenField(validators=[DataRequired()])
    otp = StringField("OTP Code", validators=[DataRequired(), Length(min=4, max=8)])


class ResetPasswordForm(FlaskForm):
    token = HiddenField(validators=[DataRequired()])
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )


class AddressForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(2, 150)])
    mobile = StringField("Mobile Number", validators=[DataRequired(), Length(10, 20)])
    email = StringField("Email", validators=[Optional(), Email()])
    address_line = TextAreaField("Complete Address", validators=[DataRequired(), Length(5, 255)])
    city = StringField("City", validators=[DataRequired(), Length(2, 100)])
    state = StringField("State", validators=[DataRequired(), Length(2, 100)])
    pincode = StringField("Pincode", validators=[DataRequired(), Regexp(r"^\d{5,6}$")])
    landmark = StringField("Landmark", validators=[Optional(), Length(max=150)])
    is_default = BooleanField("Set as default address")


class CustomFrameForm(FlaskForm):
    photo = FileField("Upload Your Photo", validators=[
        DataRequired(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only!")
    ])
    frame_style = SelectField("Frame Style", validators=[DataRequired()])
    frame_color = SelectField("Frame Color", validators=[DataRequired()])
    frame_size = SelectField("Frame Size", validators=[DataRequired()])
    orientation = SelectField("Orientation", choices=[("Portrait", "Portrait"), ("Landscape", "Landscape")])
    quantity = IntegerField("Quantity", default=1, validators=[DataRequired(), NumberRange(min=1, max=100)])
    special_instructions = TextAreaField("Special Instructions", validators=[Optional(), Length(max=500)])
    customer_name = StringField("Your Name", validators=[DataRequired(), Length(2, 150)])
    customer_mobile = StringField("Mobile Number", validators=[DataRequired(), Length(10, 20)])


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(2, 150)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    mobile = StringField("Mobile", validators=[Optional(), Length(max=20)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(5, 1000)])


class ReviewForm(FlaskForm):
    rating = SelectField("Rating", choices=[("5", "5 - Excellent"), ("4", "4 - Good"),
                                             ("3", "3 - Average"), ("2", "2 - Below Average"),
                                             ("1", "1 - Poor")], validators=[DataRequired()])
    comment = TextAreaField("Your Review", validators=[DataRequired(), Length(5, 1000)])
    image = FileField("Add a Photo (optional)", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])


class CouponApplyForm(FlaskForm):
    code = StringField("Coupon Code", validators=[DataRequired()])


# --- Admin forms ---
class ProductForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired(), Length(2, 200)])
    sku = StringField("SKU", validators=[DataRequired(), Length(2, 50)])
    description = TextAreaField("Description", validators=[Optional()])
    price = DecimalField("Price (Rs.)", validators=[DataRequired(), NumberRange(min=0)])
    discount_percent = IntegerField("Discount %", default=0, validators=[Optional(), NumberRange(min=0, max=90)])
    stock = IntegerField("Stock", default=0, validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    subcategory = StringField("Subcategory", validators=[Optional(), Length(max=120)])
    frame_material = StringField("Frame Material", validators=[Optional(), Length(max=100)])
    frame_color = StringField("Frame Color", validators=[Optional(), Length(max=60)])
    delivery_time_days = StringField("Delivery Time", default="3-5 days")
    is_available = BooleanField("Available", default=True)
    is_featured = BooleanField("Featured")
    is_new_arrival = BooleanField("New Arrival")
    is_best_seller = BooleanField("Best Seller")
    is_clearance = BooleanField("Clearance Sale")
    is_customizable = BooleanField("Customer Can Customize")
    images = FileField("Product Images", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    sizes = SelectMultipleField("Available Sizes", coerce=int, validators=[Optional()])


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(2, 120)])
    description = TextAreaField("Description", validators=[Optional()])
    parent_id = SelectField("Parent Category", coerce=int, validators=[Optional()])
    image = FileField("Category Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    is_active = BooleanField("Active", default=True)


class SizeForm(FlaskForm):
    label = StringField("Size Label (e.g. 8x10)", validators=[DataRequired(), Length(1, 50)])
    is_custom = BooleanField("Custom Size Option")


class CouponForm(FlaskForm):
    code = StringField("Coupon Code", validators=[DataRequired(), Length(2, 50)])
    discount_percent = IntegerField("Discount %", validators=[DataRequired(), NumberRange(min=1, max=100)])
    max_discount_amount = DecimalField("Max Discount (Rs.)", validators=[Optional()])
    min_order_amount = DecimalField("Min Order Amount (Rs.)", default=0, validators=[Optional()])
    usage_limit = IntegerField("Usage Limit", validators=[Optional()])
    is_active = BooleanField("Active", default=True)


class SliderForm(FlaskForm):
    title = StringField("Title", validators=[Optional(), Length(max=200)])
    subtitle = StringField("Subtitle", validators=[Optional(), Length(max=255)])
    link_url = StringField("Link URL", validators=[Optional(), Length(max=255)])
    button_text = StringField("Button Text", default="Shop Now")
    image = FileField("Slider Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    is_active = BooleanField("Active", default=True)


class TestimonialForm(FlaskForm):
    customer_name = StringField("Customer Name", validators=[DataRequired(), Length(2, 150)])
    rating = SelectField("Rating", choices=[("5", "5"), ("4", "4"), ("3", "3"), ("2", "2"), ("1", "1")])
    comment = TextAreaField("Testimonial", validators=[DataRequired()])
    image = FileField("Customer Photo", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    is_active = BooleanField("Active", default=True)


class GalleryImageForm(FlaskForm):
    image = FileField("Shop Photo", validators=[DataRequired(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    caption = StringField("Caption (optional)", validators=[Optional(), Length(max=150)])
    is_active = BooleanField("Show on website", default=True)


class AdminLoginForm(FlaskForm):
    email = StringField("Admin Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
