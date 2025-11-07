# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
import os

# Kendi modüllerimizi import et
from config import Config
# DÜZELTME: Klasör yapısına uygun olarak paketten import etme
from models.currency_models import init_db, get_db
from services.currency_service import fetch_currencies, fetch_golds, fetch_silvers 
from services.news_service import haberleri_cek 

# Blueprint (Rota) import et
from routes.currency_routes import currency_bp
from routes.news_routes import news_bp 


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

def update_all():
    """Tüm verileri güncelle"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🔄 FULL UPDATE BAŞLANGIÇ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Sırayla çek
    fetch_currencies()
    fetch_golds()
    fetch_silvers()
    haberleri_cek()
    
    logger.info(f"✅ FULL UPDATE BİTTİ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}\n")

@app.route('/api/update', methods=['POST'])
def manual_update():
    """Manuel güncelleme tetikleyici"""
    if request.remote_addr != '127.0.0.1' and request.host.split(':')[0] != 'localhost':
        return jsonify({'success': False, 'message': 'Erişim reddedildi'}), 403
        
    logger.info("⚡️ Manuel güncelleme isteği alındı...")
    try:
        update_all()
        return jsonify({'success': True, 'message': 'Full update started'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        # Gunicorn kullanılıyorsa bu kısım çalışmaz, ancak yerel testler için önemlidir.
        # Render'da Procfile üzerinden Gunicorn'un kendisi başlatılır.
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.critical("❌ Veritabanı başlatılamadığı için uygulama başlatılmadı.")
