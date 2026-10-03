import os
import uuid
import logging
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import requests
from requests.exceptions import RequestException

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gizli-anahtar-kelime')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    cargo_company = db.Column(db.String(50), nullable=False)
    tracking_token = db.Column(db.String(36), unique=True, nullable=False)
    cargo_status = db.Column(db.String(50), default='Hazırlanıyor')

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        logging.error(f"Tablo oluşturma hatası: {str(e)}")

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Kargo Takip Sistemi API aktif ve çalışıyor!",
        "endpoints": {
            "siparis_olustur": "/api/orders/create (POST)",
            "istatistikler": "/api/dashboard/stats (GET)"
        }
    }), 200

def send_sms_safe(phone_number, link):
    api_url = "https://api.netgsm.com.tr/json/send"
    payload = {
        "gsm": phone_number,
        "message": f"Sayın müşterimiz, kargonuz yola çıktı. Takip linkiniz: {link}"
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code == 200:
            return True, "SMS başarıyla gönderildi."
        else:
            return False, "SMS servisi geçici olarak yanıt vermedi."
    except RequestException as e:
        logging.error(f"SMS Ağ Hatası: {str(e)}")
        return False, "SMS gönderilemedi, ancak siparişiniz kaydedildi."

@app.route('/api/orders/create', methods=['POST'])
def create_order():
    try:
        data = request.json or request.form
        seller_id = session.get('user_id', 1)
        
        if not data.get('total_amount') or not data.get('phone'):
            return jsonify({"error": "Toplam tutar ve telefon numarası zorunludur."}), 400

        unique_token = str(uuid.uuid4())
        
        new_order = Order(
            seller_id=seller_id,
            customer_id=int(data.get('customer_id', 1)),
            total_amount=float(data['total_amount']),
            cargo_company=data.get('cargo_company', 'Yurtiçi Kargo'),
            tracking_token=unique_token
        )
        
        db.session.add(new_order)
        db.session.commit()
        
        tracking_link = f"kargo-takip-sistemi.vercel.app/kargo-takip/{unique_token}"
        sms_result_message = ""
        
        if data.get('send_sms') in [True, 'true', '1', 'on']:
            _, sms_result_message = send_sms_safe(data['phone'], tracking_link)
            
        return jsonify({
            "status": "success",
            "message": "Sipariş ve kargo kaydı başarıyla oluşturuldu!",
            "tracking_link": tracking_link,
            "sms_status": sms_result_message
        }), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Sipariş oluşturma hatası: {str(e)}")
        return jsonify({"error": "İşlem sırasında beklenmeyen bir hata oluştu."}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        role = session.get('role', 'seller')
        user_id = session.get('user_id', 1)
        
        if role == 'admin':
            total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0.0
            total_orders = Order.query.count()
            return jsonify({"role": "admin", "total_revenue": total_revenue, "total_orders": total_orders}), 200
            
        elif role == 'seller':
            seller_revenue = db.session.query(db.func.sum(Order.total_amount)).filter_by(seller_id=user_id).scalar() or 0.0
            seller_orders = Order.query.filter_by(seller_id=user_id).count()
            return jsonify({"role": "seller", "revenue": seller_revenue, "orders_count": seller_orders}), 200

        return jsonify({"error": "Yetkisiz erişim"}), 403
        
    except Exception as e:
        logging.error(f"İstatistik getirme hatası: {str(e)}")
        return jsonify({"error": "Veriler getirilirken bir hata oluştu."}), 500

if __name__ == '__main__':
    app.run(debug=True)