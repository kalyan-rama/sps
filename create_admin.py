from app import app, db
from models import User
from getpass import getpass
from werkzeug.security import generate_password_hash

def create_admin(username, password):
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print("User already exists")
            return
        u = User(username=username, is_admin=True)
        u.password_hash = generate_password_hash(password)
        db.session.add(u)
        db.session.commit()
        print("Admin created:", username)

if __name__ == "__main__":
    username = input("Admin username: ").strip() or "admin"
    password = getpass("Password (input hidden): ").strip() or "admin123"
    create_admin(username, password)