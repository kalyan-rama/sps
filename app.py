import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_migrate import Migrate
from slugify import slugify  # pip install python-slugify
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from models import db, Product, User, Order

# ---------------------------
# Flask App Initialization
# ---------------------------
app = Flask(__name__)
app.config.from_object("config")

# ✅ Upload folder for product images
app.config["UPLOAD_FOLDER"] = os.path.join("static", "images")

# Initialize DB
db.init_app(app)
migrate = Migrate(app, db)

# ---------------------------
# Flask-Mail Setup
# ---------------------------
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("GMAIL_USER"),
    MAIL_PASSWORD=os.environ.get("GMAIL_PASS")
)
MAIL_OWNER = os.environ.get("SHOP_OWNER_EMAIL")
mail = Mail(app)

# Ensure data folder exists
os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

# ---------------------------
# Helpers
# ---------------------------
def get_cart():
    return session.setdefault("cart", {})

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    products = Product.query.filter(Product.name.ilike(f"%{q}%")).all() if q else Product.query.all()
    return render_template("index.html", products=[p.to_dict() for p in products], q=q)


@app.route("/product/<slug>")
def product_detail(slug):
    p = Product.query.filter_by(slug=slug).first_or_404()
    return render_template("product.html", product=p.to_dict())


@app.route("/cart")
def cart_page():
    cart = get_cart()
    product_ids = [int(pid) for pid in cart.keys()]
    items = Product.query.filter(Product.id.in_(product_ids)).all() if product_ids else []
    display, total = [], 0.0
    for it in items:
        qty = cart.get(str(it.id), 0)
        subtotal = it.price * qty
        total += subtotal
        # ✅ Pass actual Product object (not dict)
        display.append({"product": it, "qty": qty, "subtotal": subtotal})
    return render_template("cart.html", items=display, total=total)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    cart = get_cart()
    qty = int(request.form.get("qty", 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + qty
    session["cart"] = cart
    return redirect(url_for("cart_page"))


@app.route("/cart/update", methods=["POST"])
def update_cart():
    cart = get_cart()
    for pid, qty in request.form.items():
        if pid.startswith("qty_"):
            idnum = pid.split("_", 1)[1]
            q = int(qty) if qty and int(qty) > 0 else 0
            if q == 0:
                cart.pop(idnum, None)
            else:
                cart[idnum] = q
    session["cart"] = cart
    return redirect(url_for("cart_page"))


@app.route("/cart/delete/<int:product_id>", methods=["POST"])
def delete_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)  # ✅ remove product safely
    session["cart"] = cart
    flash("🗑️ Product removed from cart.", "info")
    return redirect(url_for("cart_page"))

# ---------------------------
# ✅ Admin Update Order Status
# ---------------------------
@app.route("/admin/orders/update/<int:order_id>", methods=["POST"])
def update_order(order_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get("status", order.status)
    db.session.commit()
    flash("✅ Order status updated!", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------------------
# Checkout Route with Email
# ---------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty!", "warning")
        return redirect(url_for("index"))

    products = []
    total = 0
    for pid, qty in cart.items():
        product = db.session.get(Product, int(pid))
        if product:
            subtotal = product.price * qty
            total += subtotal
            products.append({"product": product, "qty": qty, "subtotal": subtotal})

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        address = request.form["address"]

        # Save orders with default status
        for item in products:
            order = Order(
                product_id=item["product"].id,
                qty=item["qty"],
                customer_name=name,
                customer_email=email,
                customer_phone=phone,
                customer_address=address,
                total=item["subtotal"],
                status="Pending"   # ✅ default status
            )
            db.session.add(order)
        db.session.commit()

        session["cart"] = {}  # clear cart

        # Send emails
        try:
            order_summary = "\n".join([f"{it['product'].name} x{it['qty']} — ₹{it['subtotal']:.2f}" for it in products])
            body = f"""
Your Order is Placed!

Customer: {name}
Email: {email}
Phone: {phone}
Address: {address}

Order Details:
{order_summary}

Total: ₹{total:.2f}
"""

            msg_owner = Message(
                subject="🛒 New Order Received - SPS Sarees",
                sender=app.config["MAIL_USERNAME"],
                recipients=[MAIL_OWNER],
                body=body
            )
            mail.send(msg_owner)

            msg_customer = Message(
                subject="✅ Your Order Details - SPS Sarees",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email],
                body=body
            )
            mail.send(msg_customer)

        except Exception as e:
            print("⚠️ Email sending failed:", e)

        flash("✅ Order placed successfully! Confirmation sent via email.", "success")
        return render_template("checkout.html", success=True, products=products, total=total)

    return render_template("checkout.html", success=False, products=products, total=total)


# ---------------------------
# API Route
# ---------------------------
@app.route("/api/products")
def api_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


# ---------------------------
# Admin Routes
# ---------------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and user.check_password(password):
            session["admin"] = user.username
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    orders = Order.query.all()
    products = Product.query.all()
    return render_template("admin_dashboard.html", orders=orders, products=products)


@app.route("/admin/add_product", methods=["GET", "POST"])
def add_product():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        name = request.form.get("name")
        slug = slugify(name)  # generate slug from name
        description = request.form.get("description")
        price = float(request.form.get("price"))
        stock = int(request.form.get("stock"))

        # ensure slug is unique
        base_slug = slug
        counter = 1
        while Product.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        file = request.files.get("image")
        if file and "." in file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_path = url_for("static", filename=f"images/{filename}", _external=True)
        else:
            image_path = None

        product = Product(
            name=name,
            slug=slug,
            description=description,
            price=price,
            stock=stock,
            image=image_path
        )
        db.session.add(product)
        db.session.commit()

        flash("✅ Product added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_product.html")


@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.name = request.form.get("name")
        new_slug = slugify(product.name)

        # ensure slug is unique (ignore current product)
        base_slug = new_slug
        counter = 1
        while Product.query.filter(Product.slug == new_slug, Product.id != product.id).first():
            new_slug = f"{base_slug}-{counter}"
            counter += 1
        product.slug = new_slug

        product.price = float(request.form.get("price", 0))
        product.stock = int(request.form.get("stock", 0))
        product.description = request.form.get("description", "")

        file = request.files.get("image")
        if file and "." in file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            product.image = url_for("static", filename=f"images/{filename}", _external=True)

        db.session.commit()
        flash("✏️ Product updated successfully", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_product.html", product=product)


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    product = Product.query.get_or_404(product_id)

    if product.orders:
        flash("❌ Cannot delete product because orders exist for it.", "danger")
        return redirect(url_for("admin_dashboard"))

    db.session.delete(product)
    db.session.commit()
    flash("🗑️ Product deleted successfully", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------------------
# Run Server
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)

