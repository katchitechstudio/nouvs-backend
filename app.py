# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
import os
import sys

# Garanti amaçlı sys.path düzeltmelerini bırakıyoruz.
# Ancak bu düzeltme ile importları noktasız yapıyoruz.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SRC_DIR) 
sys.path.append(os.path.join(SRC_DIR, 'models'))
sys.path.append(os.path.join(SRC_DIR, 'services'))
sys.path.append(os.path.join(SRC_DIR, 'routes'))
# -------------------------------------------------------------


# Kendi modüllerimizi DÜZ YAPI İLE import et (KRİTİK DEĞİŞİKLİK)
# Örneğin: "from models.currency_models" yerine "from currency_models"
from config import Config
from currency_models import init_db, get_db # <-- DEĞİŞTİ!
from currency_service import fetch_currencies, fetch_golds, fetch_silvers # <-- DEĞİŞTİ!
from news_service import haberleri_cek # <-- DEĞİŞTİ!

# Blueprint (Rota) DÜZ YAPI İLE import et
from currency_routes import currency_bp # <-- DEĞİŞTİ!
from news_routes import news_bp # <-- DEĞİŞTİ!


# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS ayarı
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Blueprint'leri kaydet
app.register_blueprint(currency_bp)
app.register_blueprint(news_bp)


# ------------------------------------
# SCHEDULER VE YARDIMCI FONKSİYONLAR
# ------------------------------------
# ... (Kodun geri kalanı aynı)
# ...
# ...
def update_all():
    """Tüm verileri güncelle"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🔄 FULL UPDATE BAŞLANGIÇ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")
    
    # Tüm servisleri çağır
    haberleri_cek()
    fetch_currencies()
    fetch_golds()
    fetch_silvers()
    
    logger.info(f"\n✅ FULL UPDATE TAMAMLANDI")
    logger.info(f"{'='*60}\n")
    
# ... (Kodun geri kalanı aynı)
# ...

@app.route('/', methods=['GET'])
def home():
# ... (Rotalar ve fonksiyonlar aynı)
# ...
# ...
@app.route('/health', methods=['GET', 'HEAD'])
def health():
# ... (Rotalar ve fonksiyonlar aynı)
# ...
# ...
@app.route('/api/update', methods=['POST'])
def manual_update():
# ... (Rotalar ve fonksiyonlar aynı)
# ...
# ------------------------------------
# BAŞLANGIÇ
# ------------------------------------

if __name__ == '__main__':
    # Veritabanını başlatmaya çalış (tabloları oluşturur)
    if init_db(): 
        # İlk veri çekimi
        update_all()

        try:
            scheduler = BackgroundScheduler()
            
            # Her 1 saatte bir haberler
            scheduler.add_job(func=haberleri_cek, trigger="interval", hours=1, id="haber_job")
            
            # Her 60 dakikada bir döviz/altın/gümüş
            scheduler.add_job(
                func=lambda: [fetch_currencies(), fetch_golds(), fetch_silvers()],
                trigger="interval",
                minutes=60,
                id="kurabak_job"
            )
            scheduler.start()
            logger.info("✅ Scheduler başlatıldı")
        except Exception as e:
            logger.error(f"⚠️  Scheduler başlatılamadı: {e}")
            
        # Sunucuyu başlat (Render/Heroku/Gunicorn için gerekli)
        port = int(os.environ.get('PORT', 5001))
        # KRİTİK: debug=False, Scheduler'ın çift çalışmasını engeller.
        app.run(host='0.0.0.0', port=port, debug=False)
    else:

        logger.error("❌ Uygulama veritabanı hatası nedeniyle başlatılamadı.")
