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
    
    # KuraBak Ayarları - SADECE 15 DÖVİZ
    CURRENCIES_LIST = [
        'USD',  # 🇺🇸 Amerikan Doları
        'EUR',  # 🇪🇺 Euro
        'JPY',  # 🇯🇵 Japon Yeni
        'GBP',  # 🇬🇧 İngiliz Sterlini
        'CNY',  # 🇨🇳 Çin Yuanı
        'CHF',  # 🇨🇭 İsviçre Frangı
        'CAD',  # 🇨🇦 Kanada Doları
        'AUD',  # 🇦🇺 Avustralya Doları
        'NZD',  # 🇳🇿 Yeni Zelanda Doları
        'SGD',  # 🇸🇬 Singapur Doları
        'HKD',  # 🇭🇰 Hong Kong Doları
        'SEK',  # 🇸🇪 İsveç Kronu
        'KRW',  # 🇰🇷 Güney Kore Wonu
        'NOK',  # 🇳🇴 Norveç Kronu
        'INR'   # 🇮🇳 Hindistan Rupisi
    ]
    
    # ALTIN FORMATLARI
    GOLD_FORMATS = [
        'Gram Altın',
        'Çeyrek Altın',
        'Yarım Altın',
        'Tam Altın',
        'Cumhuriyet Altını'
    ]
    
    # GÜMÜŞ FORMATLARI
    SILVER_FORMATS = ['Gümüş']
