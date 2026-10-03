import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "orders.db")
app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SMS_MODE"] = "demo"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL DEFAULT 1,
            customer_id INTEGER NOT NULL DEFAULT 1,
            phone TEXT NOT NULL,
            total_amount REAL NOT NULL,
            cargo_company TEXT NOT NULL,
            tracking_token TEXT NOT NULL UNIQUE,
            cargo_status TEXT NOT NULL DEFAULT 'Hazirlanıyor',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def make_tracking_url(token):
    return url_for("track_order", token=token, _external=True)


def send_sms(phone_number, link):
    if not phone_number:
        return False, "Telefon numarasi eksik."

    if app.config["SMS_MODE"] == "demo":
        return True, f"Demo SMS basariyla gonderildi."

    return False, "SMS servisi kapali."


def create_order_record(data):
    if not data:
        raise ValueError("Istek bos.")

    seller_id = int(data.get("seller_id", 1))
    customer_id = int(data.get("customer_id", 1))
    total_amount = data.get("total_amount")
    phone = str(data.get("phone", "")).strip()
    cargo_company = str(data.get("cargo_company", "Yurtici Kargo")).strip() or "Yurtici Kargo"

    if total_amount is None or total_amount == "":
        raise ValueError("Toplam tutar zorunludur.")

    try:
        total_amount = float(total_amount)
    except (TypeError, ValueError):
        raise ValueError("Toplam tutar sayi olmalidir.")

    if not phone:
        raise ValueError("Telefon numarasi zorunludur.")

    tracking_token = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO orders (
            seller_id,
            customer_id,
            phone,
            total_amount,
            cargo_company,
            tracking_token,
            cargo_status,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'Hazirlanıyor', ?, ?)
        """,
        (
            seller_id,
            customer_id,
            phone,
            total_amount,
            cargo_company,
            tracking_token,
            timestamp,
            timestamp,
        ),
    )
    conn.commit()
    conn.close()

    tracking_link = make_tracking_url(tracking_token)
    sms_status = ""

    if str(data.get("send_sms", "false")).lower() in {"true", "1", "on", "yes"}:
        _, sms_status = send_sms(phone, tracking_link)

    return {
        "status": "success",
        "tracking_token": tracking_token,
        "tracking_link": tracking_link,
        "sms_status": sms_status,
        "message": "Siparis basariyla olusturuldu.",
    }


@app.route("/")
def index():
    return redirect("/seller")


@app.route("/seller", methods=["GET", "POST"])
def seller_dashboard():
    if request.method == "POST":
        payload = {
            "seller_id": request.form.get("seller_id", 1),
            "customer_id": request.form.get("customer_id", 1),
            "phone": request.form.get("phone", ""),
            "total_amount": request.form.get("total_amount", ""),
            "cargo_company": request.form.get("cargo_company", "Yurtici Kargo"),
            "send_sms": request.form.get("send_sms", "false"),
        }
        try:
            create_order_record(payload)
            return redirect("/seller")
        except ValueError as exc:
            return render_template("seller_dashboard.html", error=str(exc), orders=[], stats={"total_revenue": 0, "total_orders": 0}), 400

    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()

    total_revenue = 0
    for order in orders:
        total_revenue += float(order["total_amount"])

    stats = {
        "total_revenue": total_revenue,
        "total_orders": len(orders),
    }

    return render_template("seller_dashboard.html", orders=orders, stats=stats, error=None)


@app.route("/api/orders/create", methods=["POST"])
def api_create_order():
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        result = create_order_record(data)
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "Beklenmeyen bir hata olustudu."}), 500


@app.route("/api/dashboard/stats")
def api_dashboard_stats():
    conn = get_db_connection()
    orders = conn.execute("SELECT total_amount FROM orders").fetchall()
    conn.close()

    total_revenue = 0
    for order in orders:
        total_revenue += float(order["total_amount"])

    return jsonify({
        "role": "seller",
        "total_revenue": total_revenue,
        "total_orders": len(orders),
    })


@app.route("/t/<token>")
def track_order(token):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE tracking_token = ?", (token,)).fetchone()
    conn.close()

    if order is None:
        return render_template("track.html", not_found=True, order=None)

    order_data = dict(order)
    order_data["tracking_link"] = make_tracking_url(token)
    return render_template("track.html", order=order_data, not_found=False)


@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Sayfa bulunamadi"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Sunucu hatasi"}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
