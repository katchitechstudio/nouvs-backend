import os

class Config:
    """Uygulama Ayarları"""
    
    # Veritabanı URL'si (Render/Heroku ortam değişkenlerinden alır)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # CollectAPI Token'ı
    COLLECTAPI_TOKEN = os.environ.get('COLLECTAPI_TOKEN')

    # Habersel Ayarları
    ALLOWED_SOURCES = ['NTV', 'CNN', 'Cumhuriyet', 'HaberTürk']
    KATEGORILER = ["general", "economy", "sport", "health", "technology"]
    
    # KuraBak Ayarları
    CURRENCIES_LIST = [
        'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CNY', 'AED', 'SAR', 'KWD', 'CAD',
        'INR', 'AUD', 'NZD', 'SGD', 'HKD', 'SEK', 'NOK', 'DKK', 'BRL', 'MXN', 'TRY'
    ]
    GOLD_FORMATS = ['Gram Altın', 'Çeyrek Altın', 'Yarım Altın', 'Tam Altın', 'Cumhuriyet Altını']
    SILVER_FORMATS = ['Gümüş']