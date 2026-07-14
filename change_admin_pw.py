# Run this from your project folder: python change_admin_pw.py
from app import create_app
from app.extensions import db
from app.models import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(email="admin@artistaframe.com").first()
    if admin:
        new_password = input("Enter new admin password: ")
        admin.set_password(new_password)
        db.session.commit()
        print("Admin password updated.")
    else:
        print("Admin account not found — run seed.py first.")
