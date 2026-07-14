"""
Seed the database with the shop's initial data:
- One admin account (Chandan Kumar Saw)
- All categories from the project brief (including God Frames subcategories)
- Standard sizes
- A full multi-product catalog: several products per category (Classic /
  Premium / Modern / Elegant style variants), plus one dedicated product per
  God Frames subcategory (Krishna, Ganesh, Sai Baba, etc.) — so browsing
  looks like a real, populated store instead of one item per shelf.
- One homepage slide, one testimonial, one welcome coupon

Run with:  python seed.py
Safe to re-run — it checks for existing records before creating duplicates.

NOTE ON IMAGES: every product image here is generated locally on the fly
(a simple frame-and-mat graphic in the category's brand colors, with the
product name printed on it) — not a photo scraped from the internet. That
means there's zero copyright risk in shipping them, but they are still
placeholders. The owner replaces them with real photos of his own frames
via Admin -> Products -> Edit -> upload new image, exactly the same way
he'll add every new product going forward.
"""
import os
import uuid
from app import create_app
from app.extensions import db
from app.models import (
    User, Category, Size, Product, ProductImage, Slider, Testimonial, Coupon, Setting
)
from app.utils import slugify

app = create_app()

TOP_LEVEL_CATEGORIES = [
    "God Frames", "Horse Frames", "Nature Frames", "Modern Art", "Family Frames",
    "Couple Frames", "Wedding Frames", "Baby Frames", "Motivational Frames",
    "Home Decoration Frames", "Office Decoration Frames", "Wooden Frames",
    "Premium Frames", "LED Frames", "Canvas Frames", "Customized Photo Frames",
    "Festival Collection", "New Arrival", "Best Seller", "Clearance Sale",
]

GOD_FRAME_SUBCATEGORIES = [
    "Krishna", "Radha Krishna", "Ram Darbar", "Shiva", "Hanuman",
    "Durga", "Saraswati", "Ganesh", "Sai Baba",
]

SIZES = ["4x6", "5x7", "6x8", "8x10", "10x12", "12x18", "16x20", "18x24", "24x36"]

# Category -> (frame border color, mat/background color, accent color)
CATEGORY_PALETTE = {
    "god-frames":                ("#B08D57", "#F7E9C6", "#8A1E1E"),
    "horse-frames":               ("#6B4A2C", "#EDE0C8", "#3A2A18"),
    "nature-frames":              ("#2F5D3A", "#E7EFDD", "#1E3D26"),
    "modern-art":                 ("#1F1F1F", "#EDEDED", "#B5522F"),
    "family-frames":              ("#8C6A4A", "#F3EAD9", "#55483A"),
    "couple-frames":              ("#A85C6B", "#F7E4E8", "#6E2B39"),
    "wedding-frames":             ("#C9A227", "#FFF7E3", "#8A6D1A"),
    "baby-frames":                ("#7FA6C9", "#EAF3FA", "#2E5A80"),
    "motivational-frames":        ("#1F4741", "#E9EFE9", "#B08D57"),
    "home-decoration-frames":     ("#8A5A3B", "#F1E4D3", "#4E3320"),
    "office-decoration-frames":   ("#3D5A73", "#E7EEF3", "#22384A"),
    "wooden-frames":              ("#6E4A2E", "#EFE2CC", "#42301D"),
    "premium-frames":             ("#B08D57", "#2A2118", "#EDE6D6"),
    "led-frames":                 ("#1F4741", "#0F1F1D", "#7FE0C8"),
    "canvas-frames":              ("#4A4438", "#F5F1E6", "#8C6A4A"),
    "customized-photo-frames":    ("#B5522F", "#FBF1E7", "#7A3620"),
    "festival-collection":        ("#C9A227", "#FDF3D6", "#8A1E1E"),
    "new-arrival":                 ("#1F4741", "#E3D9C4", "#B08D57"),
    "best-seller":                 ("#B08D57", "#EDE6D6", "#1F4741"),
    "clearance-sale":              ("#B5522F", "#F5E6DE", "#6E2B39"),
}

# Style variants applied to every category to build out a multi-product catalog
STYLE_VARIANTS = [
    dict(prefix="Classic", price_mult=1.0, material="Wooden", discount=0),
    dict(prefix="Premium", price_mult=1.6, material="Premium Wood", discount=5),
    dict(prefix="Modern", price_mult=0.85, material="MDF", discount=15),
    dict(prefix="Elegant", price_mult=1.3, material="Metal + Wood", discount=10),
]

BASE_PRICE_BY_CATEGORY = {
    "God Frames": 799, "Horse Frames": 999, "Nature Frames": 749, "Modern Art": 899,
    "Family Frames": 649, "Couple Frames": 699, "Wedding Frames": 1199, "Baby Frames": 599,
    "Motivational Frames": 499, "Home Decoration Frames": 749, "Office Decoration Frames": 699,
    "Wooden Frames": 949, "Premium Frames": 1599, "LED Frames": 1699, "Canvas Frames": 899,
    "Customized Photo Frames": 799, "Festival Collection": 699, "New Arrival": 649,
    "Best Seller": 799, "Clearance Sale": 349,
}

SIZE_SETS = [["8x10", "12x18"], ["10x12", "16x20"], ["12x18", "16x20", "18x24"], ["8x10"], ["16x20", "24x36"]]

# Real, licensed (Pexels, free-for-commercial-use) sample photos, mapped onto
# specific catalog slots so category pages don't rely solely on generated
# placeholder art. Keyed by (category name, variant_seed) for the general
# style-variant products, and (category name, subcategory) for God Frames'
# deity-specific products. Any slot not listed here falls back to the
# generated frame-and-mat placeholder, same as before.
REAL_PHOTO_BY_VARIANT = {
    ("Horse Frames", 0): "horse-1.jpg",
    ("Horse Frames", 1): "horse-2.jpg",
    ("Nature Frames", 0): "nature-1.jpg",
    ("Nature Frames", 1): "nature-2.jpg",
    ("Modern Art", 0): "modern-art-1.jpg",
    ("Modern Art", 1): "modern-art-2.jpg",
    ("Wedding Frames", 0): "wedding-1.jpg",
    ("Wedding Frames", 1): "wedding-2.jpg",
    ("Couple Frames", 0): "couple-1.jpg",
    ("Baby Frames", 0): "baby-1.jpg",
    ("Baby Frames", 1): "baby-2.jpg",
    ("Family Frames", 0): "family-1.jpg",
    ("Family Frames", 1): "family-2.jpg",
    ("Family Frames", 2): "family-3.jpg",
    ("Family Frames", 3): "family-4.jpg",
    ("Home Decoration Frames", 0): "home-decor-1.jpg",
    ("God Frames", 1): "god-ganesh-2.jpg",  # a general-purpose Premium God Frame variant
}
REAL_PHOTO_BY_SUBCATEGORY = {
    "Radha Krishna": "god-radhakrishna-1.jpg",
    "Ganesh": "god-ganesh-1.jpg",
}
SAMPLE_PHOTOS_DIR = os.path.join("app", "static", "img", "sample_photos")

FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_PATH_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _use_real_photo(filename):
    """Copies a pre-processed real sample photo into the product uploads
    folder (giving it a fresh unique name), so it behaves exactly like any
    other uploaded product image."""
    src = os.path.join(SAMPLE_PHOTOS_DIR, filename)
    if not os.path.exists(src):
        return None
    import shutil
    ext = filename.rsplit(".", 1)[-1]
    dest_name = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(app.config["PRODUCT_UPLOAD_FOLDER"], dest_name)
    shutil.copyfile(src, dest_path)
    return os.path.relpath(dest_path, app.config["STATIC_FOLDER"]).replace("\\", "/")


def _shift_hex(hex_color, amount):
    """Lighten/darken a hex color by `amount` (-60..60) to create visual variety
    between style variants within the same category palette."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = max(0, min(255, r + amount))
    g = max(0, min(255, g + amount))
    b = max(0, min(255, b + amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def _generate_product_image(product_name, frame_col, mat_col, accent, variant_seed=0):
    """Render a simple, original frame-and-mat placeholder graphic with the
    product name on it, and save it directly into the product uploads folder
    (so it behaves exactly like a normal uploaded image)."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 600, 600
    img = Image.new("RGB", (W, H), frame_col)
    draw = ImageDraw.Draw(img)

    border = 46
    draw.rectangle([border, border, W - border, H - border], fill=mat_col)
    inset = border + 18
    draw.rectangle([inset, inset, W - inset, H - inset], outline=accent, width=4)

    tick = 26
    for (x, y, dx, dy) in [(border, border, 1, 1), (W - border, border, -1, 1),
                            (border, H - border, 1, -1), (W - border, H - border, -1, -1)]:
        draw.line([x, y, x + dx * tick, y], fill=accent, width=4)
        draw.line([x, y, x, y + dy * tick], fill=accent, width=4)

    cx, cy = W // 2, H // 2 - 20
    shape = variant_seed % 3
    if shape == 0:
        r = 70
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent, width=3)
        draw.ellipse([cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18], outline=accent, width=2)
    elif shape == 1:
        r = 75
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], outline=accent, width=3)
    else:
        r = 68
        draw.rectangle([cx - r, cy - r, cx + r, cy + r], outline=accent, width=3)

    try:
        font_title = ImageFont.truetype(FONT_PATH_BOLD, 22)
        font_small = ImageFont.truetype(FONT_PATH_REG, 15)
    except Exception:
        font_title = ImageFont.load_default()
        font_small = font_title

    # Wrap product name onto up to 2 lines
    words = product_name.split()
    line1, line2 = product_name, ""
    if len(words) > 3:
        mid = len(words) // 2
        line1, line2 = " ".join(words[:mid]), " ".join(words[mid:])

    for i, line in enumerate([line1, line2]):
        if not line:
            continue
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, cy + 90 + i * 28), line, fill=accent, font=font_title)

    footer = "Artista Frame"
    bbox = draw.textbbox((0, 0), footer, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H - border - 28), footer, fill=accent, font=font_small)

    dest_name = f"{uuid.uuid4().hex}.jpg"
    dest_path = os.path.join(app.config["PRODUCT_UPLOAD_FOLDER"], dest_name)
    img.save(dest_path, quality=88)
    return os.path.relpath(dest_path, app.config["STATIC_FOLDER"]).replace("\\", "/")


def _build_catalog():
    """Builds the full list of products to seed: several style variants per
    top-level category, plus one product per God Frames subcategory."""
    catalog = []  # list of dicts

    for cat_name in TOP_LEVEL_CATEGORIES:
        base_price = BASE_PRICE_BY_CATEGORY[cat_name]
        singular = cat_name.replace(" Frames", "").replace(" Frame", "").replace(" Collection", "").replace(" Sale", "").replace(" Art", " Art").replace(" Arrival", "")
        for i, variant in enumerate(STYLE_VARIANTS):
            name = f"{variant['prefix']} {singular} Wall Frame".replace("  ", " ")
            catalog.append(dict(
                category=cat_name,
                name=name,
                price=round(base_price * variant["price_mult"], -1),
                discount=variant["discount"],
                material=variant["material"],
                color=None,  # let color rotate per palette below
                sizes=SIZE_SETS[i % len(SIZE_SETS)],
                variant_seed=i,
                featured=(i == 1),       # "Premium" variant featured
                new_arrival=(cat_name == "New Arrival" or i == 2),
                best_seller=(cat_name == "Best Seller" or i == 0),
                clearance=(cat_name == "Clearance Sale"),
                customizable=True,
            ))

    # God Frames: one dedicated product per deity subcategory
    for i, deity in enumerate(GOD_FRAME_SUBCATEGORIES):
        catalog.append(dict(
            category="God Frames",
            subcategory=deity,
            name=f"{deity} Divine Wall Frame",
            price=699 + (i * 40),
            discount=[10, 0, 5, 15, 0, 10, 0, 20, 5][i % 9],
            material="Wooden" if i % 2 == 0 else "Premium Wood",
            color="Golden" if i % 2 == 0 else "Antique Brown",
            sizes=SIZE_SETS[i % len(SIZE_SETS)],
            variant_seed=i,
            featured=(i < 2),
            new_arrival=(i in (4, 5)),
            best_seller=(i in (0, 7)),
            clearance=False,
            customizable=True,
        ))

    return catalog


def seed():
    with app.app_context():
        db.create_all()

        # --- Admin account ---
        admin_email = "admin@artistaframe.com"
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                full_name="Chandan Kumar Saw",
                email=admin_email,
                mobile="+919006090994",
                is_admin=True,
                email_verified=True,
            )
            admin.set_password("ArtistaFrame@2026")  # CHANGE THIS after first login
            db.session.add(admin)
            print(f"Created admin account: {admin_email} / ArtistaFrame@2026 (please change this password!)")

        # --- Categories ---
        category_objs = {}
        for i, name in enumerate(TOP_LEVEL_CATEGORIES):
            slug = slugify(name)
            cat = Category.query.filter_by(slug=slug).first()
            if not cat:
                cat = Category(name=name, slug=slug, display_order=i, is_active=True)
                db.session.add(cat)
                db.session.flush()
            category_objs[name] = cat

        god_frames = category_objs["God Frames"]
        subcat_objs = {}
        for i, name in enumerate(GOD_FRAME_SUBCATEGORIES):
            slug = slugify(f"god-frames-{name}")
            sc = Category.query.filter_by(slug=slug).first()
            if not sc:
                sc = Category(name=name, slug=slug, parent_id=god_frames.id, display_order=i, is_active=True)
                db.session.add(sc)
                db.session.flush()
            subcat_objs[name] = sc

        db.session.commit()

        # --- Category cover images ---
        for name, cat in category_objs.items():
            if not cat.image:
                frame_col, mat_col, accent = CATEGORY_PALETTE[cat.slug]
                cat.image = _generate_product_image(name, frame_col, mat_col, accent, variant_seed=0)
        db.session.commit()

        # --- Sizes ---
        size_objs = {}
        for i, label in enumerate(SIZES):
            sz = Size.query.filter_by(label=label).first()
            if not sz:
                sz = Size(label=label, display_order=i)
                db.session.add(sz)
                db.session.flush()
            size_objs[label] = sz
        if not Size.query.filter_by(label="Custom Size").first():
            db.session.add(Size(label="Custom Size", is_custom=True, display_order=99))
        db.session.commit()

        # --- Full catalog ---
        catalog = _build_catalog()
        created_count = 0
        for idx, p in enumerate(catalog):
            cat = category_objs[p["category"]]
            sku = f"AF-{slugify(p['category'])[:6].upper().replace('-', '')}-{idx:03d}"
            if Product.query.filter_by(sku=sku).first():
                continue

            slug = slugify(p["name"]) + "-" + sku.lower()
            if Product.query.filter_by(slug=slug).first():
                slug = slug + "-" + uuid.uuid4().hex[:4]

            frame_col, mat_col, accent = CATEGORY_PALETTE[cat.slug]
            variant_seed = p.get("variant_seed", 0)
            # Slightly vary the palette per variant so products in the same
            # category are visually distinguishable from one another.
            frame_col_v = _shift_hex(frame_col, (variant_seed - 1) * 12)
            mat_col_v = _shift_hex(mat_col, (variant_seed - 1) * 8)

            product = Product(
                name=p["name"], sku=sku, slug=slug,
                description=f"A beautiful {p['name'].lower()}, crafted with care by Artista Frame. "
                            f"Perfect for {p['category'].lower()}.",
                price=p["price"], discount_percent=p.get("discount", 0), stock=25,
                category_id=cat.id, subcategory=p.get("subcategory"),
                frame_material=p.get("material"), frame_color=p.get("color") or "Brown",
                is_featured=p.get("featured", False), is_new_arrival=p.get("new_arrival", False),
                is_best_seller=p.get("best_seller", False), is_clearance=p.get("clearance", False),
                is_customizable=p.get("customizable", True),
            )
            db.session.add(product)
            db.session.flush()

            product.sizes = [size_objs[s] for s in p.get("sizes", []) if s in size_objs]

            img_path = None
            subcat = p.get("subcategory")
            if subcat and subcat in REAL_PHOTO_BY_SUBCATEGORY:
                img_path = _use_real_photo(REAL_PHOTO_BY_SUBCATEGORY[subcat])
            elif (p["category"], variant_seed) in REAL_PHOTO_BY_VARIANT:
                img_path = _use_real_photo(REAL_PHOTO_BY_VARIANT[(p["category"], variant_seed)])

            if not img_path:
                img_path = _generate_product_image(p["name"], frame_col_v, mat_col_v, accent, variant_seed=variant_seed)
            db.session.add(ProductImage(product_id=product.id, image_path=img_path, is_primary=True))

            created_count += 1

        db.session.commit()

        # --- Testimonial ---
        if not Testimonial.query.first():
            db.session.add(Testimonial(
                customer_name="Priya Sharma", rating=5,
                comment="Beautiful frame quality and quick delivery! The Radha Krishna frame looks stunning in our living room.",
                is_active=True,
            ))

        # --- Welcome coupon ---
        if not Coupon.query.filter_by(code="WELCOME10").first():
            db.session.add(Coupon(code="WELCOME10", discount_percent=10, min_order_amount=500, is_active=True))

        db.session.commit()
        print(f"Database seeded successfully! ({created_count} new products created, "
              f"{Product.query.count()} total in catalog across {len(category_objs)} categories)")


if __name__ == "__main__":
    seed()
