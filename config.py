import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ---------------------------
# Security
# ---------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey123")

# ---------------------------
# Database (SQLite in /data)
# ---------------------------
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(DATA_DIR, "app.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ---------------------------
# File Uploads
# ---------------------------
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------
# Email Settings (Gmail)
# ---------------------------
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "yourgmail@gmail.com")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "your-app-password")  # ✅ Use App Password, not Gmail password
MAIL_DEFAULT_SENDER = MAIL_USERNAME

# Shop owner email
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "shopowner@gmail.com")
