# Kargo Takip Sistemi

Flask tabanlı kargo takip API uygulamasıdır. Sipariş oluşturma, takip linki üretme ve istatistik sorgulama işlemlerini destekler.

## Özellikler
- Sipariş oluşturma
- Benzersiz takip token üretimi
- SMS gönderimi (isteğe bağlı)
- Satıcı / admin istatistikleri
- SQLite veritabanı desteği

## Gereksinimler
- Python 3.10+
- pip

## Kurulum

1. Proje klasörüne gidin:

```bash
cd kargo
```

2. Sanal ortam oluşturun:

```bash
python -m venv venv
```

3. Sanal ortamı aktif edin:

Linux / macOS:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\activate
```

4. Bağımlılıkları yükleyin:

```bash
pip install -r requirements.txt
```

5. Ortam değişkenlerini ayarlayın:

```bash
cp .env.example .env
```

`.env` dosyasına aşağıdaki değerler otomatik olarak eklenir:

```env
SECRET_KEY=gizli-anahtar-kelime
DATABASE_URL=sqlite:///local.db
```

## Çalıştırma

```bash
python app.py
```

Uygulama varsayılan olarak şu adreste çalışır:

```text
http://127.0.0.1:5000
```

## API Endpoints

### Ana sayfa
```http
GET /
```

Örnek cevap:
```json
{
  "status": "success",
  "message": "Kargo Takip Sistemi API aktif ve çalışıyor!",
  "endpoints": {
    "siparis_olustur": "/api/orders/create (POST)",
    "istatistikler": "/api/dashboard/stats (GET)"
  }
}
```

### Sipariş oluşturma
```http
POST /api/orders/create
```

Body (JSON):
```json
{
  "total_amount": 1500,
  "phone": "+905551234567",
  "customer_id": 7,
  "cargo_company": "Yurtiçi Kargo",
  "send_sms": true
}
```

Örnek cevap:
```json
{
  "status": "success",
  "message": "Sipariş ve kargo kaydı başarıyla oluşturuldu!",
  "tracking_link": "https://kargo-takip-sistemi.vercel.app/kargo-takip/7f18d7b2-6b4d-44fd-8c33-6f0011ac3b9d",
  "sms_status": "SMS başarıyla gönderildi."
}
```

### İstatistikler
```http
GET /api/dashboard/stats
```

Varsayılan olarak `seller` rolü kabul edilir. Oturum `role` değeri `admin` ise toplam gelir ve toplam sipariş sayısı döner. `seller` ise kişinin gelirini ve sipariş adetini döner.

Örnek cevap (seller):
```json
{
  "role": "seller",
  "revenue": 1500.0,
  "orders_count": 2
}
```

## curl ile Test

### Sipariş oluşturma
```bash
curl -X POST http://127.0.0.1:5000/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "total_amount": 1500,
    "phone": "+905551234567",
    "customer_id": 7,
    "cargo_company": "Yurtiçi Kargo",
    "send_sms": true
  }'
```

### Ana sayfa
```bash
curl http://127.0.0.1:5000/
```

### Dashboard istatistikleri
```bash
curl http://127.0.0.1:5000/api/dashboard/stats
```

## Production Çalıştırma

Gunicorn ile çalıştırmak isterseniz:

```bash
pip install gunicorn
```

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```

## Notlar
- `DATABASE_URL` boş bırakılırsa varsayılan olarak `sqlite:///local.db` kullanılır.
- `send_sms` alanı `true`, `1`, `on`, `yes` gibi değerlerle aktif edilir.
- SMS servisinin dışa bağımlı olduğu için ağ hatası durumunda sipariş kaydı yine yapılır, sadece SMS durumu bildirilir.

## .gitignore

Aşağıdaki dosyalar versiyon kontrolüne dahil edilmez:
- `.env`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `local.db`
- `.DS_Store`

## Son Kontrol Listesi
- [x] Flask uygulama dosyası hazır
- [x] `requirements.txt` hazır
- [x] `.env.example` hazır
- [x] `Order` modeli doğru
- [x] sipariş oluşturma validasyonu çalışır
- [x] dashboard istatistikleri çalışır
- [x] SMS hatası yakalanıyor
- [x] proje için README hazır
