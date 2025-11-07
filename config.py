import os

# Uygulama Ayarları
class Config:
    # Veritabanı URL'si (Render/Heroku ortam değişkenlerinden alır)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # CollectAPI Token'ı (Ortam değişkenlerinden alır)
    # Token'ınızın Render ortam değişkenlerinde ayarlandığından emin olun.
    COLLECTAPI_TOKEN = os.environ.get('COLLECTAPI_TOKEN')

    # Habersel Ayarları
    # 4 kaliteli kaynak
    ALLOWED_SOURCES = ['NTV', 'CNN', 'Cumhuriyet', 'HaberTürk']
    # 5 kategori rotasyonu
    KATEGORILER = ["general", "economy", "sport", "health", "technology"]
    
    # KuraBak Ayarları
    # 21 döviz kodu
    CURRENCIES_LIST = [
        'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CNY', 'AED', 'SAR', 'KWD', 'CAD',
        'INR', 'AUD', 'NZD', 'SGD', 'HKD', 'SEK', 'NOK', 'DKK', 'BRL', 'MXN', 'TRY'
    ]
    # 5 altın formatı
    GOLD_FORMATS = ['Gram Altın', 'Çeyrek Altın', 'Yarım Altın', 'Tam Altın', 'Cumhuriyet Altını']
    # 1 gümüş formatı
    SILVER_FORMATS = ['Gümüş']