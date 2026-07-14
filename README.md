# Artista Frame — E-Commerce Website

A Flask e-commerce platform for **Artista Frame**, a photo frame and wall decor
shop run by Chandan Kumar Saw in Hazaribagh, Jharkhand. Customers browse and
customize photo frames, and orders are placed directly to the shop's WhatsApp
(+91 9006090994) — no online payment gateway required.

---

## What's included

- **Storefront**: home page (hero slider, categories, featured/new/best-seller
  products), category browsing with filters & sorting, product detail pages
  with image gallery and reviews, search, contact page with embedded map.
- **Accounts**: register/login/logout, OTP email verification flow, forgot/reset
  password, profile with saved addresses, order history, wishlist.
- **Cart & checkout**: add/update/remove items, apply coupon codes, checkout
  that builds a pre-filled WhatsApp order message and redirects straight to
  `wa.me`.
- **Custom photo frame**: customers upload their own photo, choose frame style/
  color/size/orientation, then confirm delivery address — sent to the shop as
  a WhatsApp order with a link to the uploaded photo.
- **Shop location & gallery**: the Contact page now uses the shop's verified
  address and exact coordinates for a precise Google Maps embed, plus a
  "Visit Our Shop" photo gallery — fully admin-manageable (Admin → Shop
  Gallery → Add Photo). It starts empty with a friendly placeholder message
  until the owner uploads real photos of the shop front, workshop, or team.
- **Admin panel** (`/admin`): dashboard with live stats and analytics charts
  (30-day sales & order trend, order status breakdown, 6-month revenue trend,
  top-selling products, monthly new customer signups — all via Chart.js), full
  product & category CRUD (with image upload), size management, order pipeline
  (Pending → Accepted → Processing → Printing → Framing → Packed → Delivered /
  Cancelled), custom photo frame request queue with photo downloads, coupon
  management, homepage slider management, testimonials, review moderation,
  customer list, notifications, site settings, CSV order export, SQLite
  backup download.
- **Security**: bcrypt password hashing, CSRF protection (Flask-WTF) on every
  form, server-side input validation, secure randomized filenames for uploads,
  role-based admin access via `is_admin` + a dedicated `@admin_required`
  decorator.

## What is intentionally not included (and how to add it)

To avoid handing you hollow placeholder code, some items from the original
wishlist were left as clear extension points rather than faked:

| Feature | Status | How to add it |
|---|---|---|
| Real OTP / password-reset emails | OTP & reset link are shown directly in the UI (no SMTP configured) | Wire up `Flask-Mail` or an API like SendGrid/Postmark in `app/auth/routes.py` where the `NOTE:` comments are |
| Wishlist "compare products" | Wishlist works; comparison view doesn't exist | Add a new route/template that reads multiple `WishlistItem`/`Product` rows side by side |
| "Frequently bought together" | Not implemented | Needs order-history analysis (co-occurrence of products in `OrderItem`) |
| Dark mode toggle | Not implemented | Add a CSS class toggle + a couple of dark-mode CSS variable overrides in `style.css` |
| Automatic image compression | Images are saved as-is | Pipe uploads through Pillow (already in `requirements.txt`) before saving in `app/utils.py::save_image` |
| Zipping all custom photos for bulk download | Each photo has an individual download link | Add `zipfile` handling to `admin.download_custom_photos` |

None of these require re-architecting anything — the models, blueprints and
templates are already structured to extend cleanly.

---

## Project structure

```
artista_frame/
├── app/
│   ├── __init__.py          # App factory, blueprint registration
│   ├── config.py            # Settings (reads from environment variables)
│   ├── extensions.py        # db, login_manager, bcrypt, csrf, migrate
│   ├── models.py            # All SQLAlchemy models
│   ├── forms.py             # All WTForms (validation + CSRF)
│   ├── utils.py             # Image saving, WhatsApp message builder, slugify, etc.
│   ├── main/routes.py       # Storefront: home, category, product, search, contact
│   ├── auth/routes.py       # Register, login, OTP, password reset, profile
│   ├── cart/routes.py       # Cart + checkout + WhatsApp order flow
│   ├── custom_frame/routes.py  # Custom photo frame upload & order flow
│   ├── admin/routes.py      # Admin panel (dashboard + all CRUD)
│   ├── templates/           # Jinja2 templates (storefront + admin)
│   └── static/
│       ├── css/style.css    # Full design system (see "Design" below)
│       ├── js/main.js
│       └── uploads/         # Product images & customer photo uploads land here
├── run.py                   # Local dev entry point
├── seed.py                  # Populates categories, sizes, admin user, sample products
├── requirements.txt
├── .env.example
├── database.sql             # MySQL schema (optional — see Database section)
└── README.md
```

---

## Local setup

```bash
cd artista_frame
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # then edit .env if needed
python seed.py                  # creates tables + admin account + sample data
python run.py
```

Visit **http://localhost:5000** for the storefront and
**http://localhost:5000/admin/login** for the admin panel.

**Default admin login** (created by `seed.py` — change the password immediately):
- Email: `admin@artistaframe.com`
- Password: `ArtistaFrame@2026`

## Shop location

Your Google share link resolved to **Artista Studio** on Google Places — the
listing's phone number matches the shop's WhatsApp number exactly, so this
is confirmed to be the same business:

- **Address:** Oppo Hi-tech Nursery, Besides Lalu Hotel & City Care Medical,
  Canary Hill Road, Dipugarha, Hazaribagh, Jharkhand 825301
- **Coordinates:** 24.0049515, 85.3816533
- Currently rated 5.0 on Google with reviews mentioning wedding photography
  and photo framing/editing work.

This address and exact coordinates now power the Contact page's Google Maps
embed (`app/static/css` unaffected — this lives in `app/models.py`'s
`Setting.get_settings()` defaults and `app/config.py`). If the business ever
moves or the listing changes, update it at **Admin → Settings**, or edit the
defaults in those two files.

## Adding real products (for the shop owner)

The catalog now mixes two kinds of images:
- **Real sample photos** (licensed, free-for-commercial-use Pexels photos)
  for Horse, Nature, Modern Art, Wedding, Couple, Baby, Family, Home
  Decoration, and two God Frames deities (Radha Krishna, Ganesh) — these
  live in `app/static/img/sample_photos/` and are wired up in `seed.py`'s
  `REAL_PHOTO_BY_VARIANT` / `REAL_PHOTO_BY_SUBCATEGORY` dictionaries.
- **Generated placeholder graphics** (a simple frame-and-mat design with the
  product name on it, not a photo of anything) for every other product slot,
  so the whole catalog still has *something* to show even where no licensed
  photo was available.

Either way, these are demonstration images — not the shop's real inventory.

**The images are generated locally** (a simple frame-and-mat graphic in the
category's brand colors, with the product name printed on it) — **not
photos scraped from the internet** — so there's no copyright risk in
shipping them. They're purely placeholders to demonstrate the catalog layout
and prove every page works; they are not meant to look like real product
photography.

To add the shop's real inventory, the owner (or you, on his behalf) goes to
**Admin → Products → Add Product** and fills in:
- **Type of frame** — choose a Category (God Frames, Wedding Frames, etc.)
  and optionally a free-text Subcategory / Frame Material (Wooden, Metal, MDF...)
- **Image of frame** — upload a real photo (can add more than one over time)
- **Cost** — Price, plus an optional Discount %
- **Size** — tick every size this frame is offered in, from a checklist
  (sizes themselves are managed at **Admin → Sizes**, so the owner can add
  new ones like "20x30" any time)

Once saved, the product appears immediately on the storefront — in its
category page, in **Shop All** (`/shop`), and in Featured/New Arrival/Best
Seller sections on the homepage if those flags are checked — always showing
the price. No coding needed for any of this.

## Database

By default the app uses **SQLite** (`artista_frame.db`, created automatically) —
zero configuration, perfect for getting started or small-scale deployment.

To use **MySQL** instead:
1. Create a database: `CREATE DATABASE artista_frame CHARACTER SET utf8mb4;`
   (or run the provided `database.sql`, which does this and creates all tables).
2. Set `DATABASE_URL` in your `.env`:
   ```
   DATABASE_URL=mysql+pymysql://youruser:yourpassword@localhost:3306/artista_frame
   ```
3. Run `python seed.py` again — SQLAlchemy will create/populate the MySQL tables.

## WhatsApp ordering

No payment gateway is used. When a customer checks out (from the cart or the
custom photo frame flow), the app:
1. Saves the order in the database (visible immediately in the admin panel).
2. Builds a formatted order message (customer details, items, prices, photo
   link for custom orders).
3. Redirects the customer's browser straight to `https://wa.me/<number>?text=...`
   with the message pre-filled, ready to send to **+91 9006090994**.

Change the number any time via **Admin → Settings → WhatsApp Number**.

## Deployment

The app is a standard Flask app and runs anywhere Python + (SQLite or MySQL)
is available. A `gunicorn` entry point is included in `requirements.txt`.

**Render / Railway** (both auto-detect Python):
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn run:app`
- Add environment variables from `.env.example` in the dashboard (set
  `DATABASE_URL` if using their managed MySQL/Postgres add-on — note: for
  Postgres you'd swap `PyMySQL` for `psycopg2-binary` in requirements.txt).
- After first deploy, run `python seed.py` once via the platform's shell/console.

**PythonAnywhere**:
- Upload the project, create a virtualenv, `pip install -r requirements.txt`.
- Set the WSGI file to import `app` from `run.py` (`from run import app as application`).
- Configure a MySQL database in their dashboard and set `DATABASE_URL` accordingly.
- Run `python seed.py` from a Bash console.

**AWS / DigitalOcean (VPS)**:
- Install Python 3.11+, MySQL (or use SQLite for lower traffic), nginx.
- `gunicorn --workers 3 --bind unix:artista_frame.sock run:app` behind nginx
  as a reverse proxy, managed by `systemd` or `supervisor`.
- Point nginx at `/static` directly for performance.

In all cases:
- Set a strong random `SECRET_KEY`.
- Set `FLASK_DEBUG=0`.
- Make sure `app/static/uploads/` is writable and persists across deploys
  (on ephemeral-filesystem hosts like some Render free tiers, use an attached
  disk or move uploads to S3-compatible storage for production).

## Design

The visual identity ("gallery-wall" palette — deep teal, brass and warm
plaster tones, Fraunces + Inter type pairing, and a mitred picture-frame
corner used as a recurring signature motif) lives entirely in
`app/static/css/style.css`. Change `--teal`, `--brass`, `--plaster` etc. at
the top of that file to re-theme the whole site.

## Notes on scope

This is a genuinely working, deployable project — not a demo. Every route,
model, and template shown above functions end-to-end. The items in the
"intentionally not included" table are the honest exceptions, called out so
you know exactly what to expect before showing this to your brother.
"# Artisa-Online-Frame-Booking-web" 
