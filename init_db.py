from app import app, db
from models import User, Product
from werkzeug.security import generate_password_hash
import os

with app.app_context():
    # remove old DB only if you want a clean start:
    # WARNING: This will delete all data
    # db.drop_all()
    db.create_all()

    # create admin if missing
    if not User.query.filter_by(username="admin").first():
        admin = User(username="sps", is_admin=True)
        admin.password_hash = generate_password_hash("sps123")
        db.session.add(admin)

    # add sample products if none
    if Product.query.count() == 0:
        samples = [
            Product(name="Silk Kanchipuram Saree", slug="silk-kanchipuram", description="Pure silk with zari border", price=12999.0, image="kanchipuram.jpg", stock=5),
            Product(name="Cotton Handloom Saree", slug="cotton-handloom", description="Light, breathable cotton", price=2499.0, image="cotton.jpg", stock=20),
            Product(name="Banarasi Saree", slug="banarasi-saree", description="Rich Banarasi brocade", price=15999.0, image="banarasi.jpg", stock=3),
        ]
        db.session.bulk_save_objects(samples)
        print("Sample products added")

    db.session.commit()
    print("DB initialized")