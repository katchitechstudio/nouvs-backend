# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
import os
import sys

# ------------------------------------
# KRİTİK DÜZELTME: SİSTEM YOLU AYARI
# ------------------------------------
# Python'ın 'models', 'services', 'routes' gibi alt klasörleri paket olarak
# bulabilmesi için projenin kök dizinini sys.path'e ekliyoruz.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# ------------------------------------
# PAKET BAZLI MODÜL İMPORTLARI (GÜNCEL)
# ------------------------------------
from config import Config
from models.currency_models import init_db, get_db
from services.currency_service import fetch_currencies, fetch_golds, fetch_silvers
from services.news_service import haberleri_cek

# Blueprint (Rota) PAKET BAZLI İMPORTLARI (GÜNCEL)
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
    
    # 1. Haberleri Çek (Saate göre kategori döner)
    haberleri_cek()

    # 2. Dövizleri Çek
    fetch_currencies()

    # 3. Altınları Çek
    fetch_golds()
    
    # 4. Gümüşleri Çek
    fetch_silvers()

    logger.info(f"\n✅ FULL UPDATE TAMAMLANDI")
    logger.info(f"{'='*60}\n")
    
def start_scheduler():
    """Uygulama başladıktan sonra scheduler'ı başlatır."""
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
        logger.error(f"⚠️ Scheduler başlatılamadı: {e}")

# ------------------------------------
# ADMIN UÇ NOKTALARI
# ------------------------------------

@app.route('/', methods=['GET'])
def home():
    """Uygulama hakkında bilgi ve endpoint listesi."""
    return jsonify({
        'app': 'Nouvs + KuraBak Backend',
        'status': 'running',
        'version': '5.0 (Modular & Robust - Gunicorn Ready)',
        'database': 'PostgreSQL',
        'services': ['News (Habersel)', 'Currency (KuraBak)'],
        'endpoints': {
            'admin': {
                '/health': 'Sağlık kontrolü',
                '/api/update': 'Manuel tam güncelleme'
            },
            'news': {
                '/api/haberler': 'Tüm haberleri getir',
                '/api/kategori/<kategori>': 'Kategoriye göre haberler',
                '/api/cek-haberler': 'Manuel haber çekme'
            },
            'currency': {
                '/api/currency/all': 'Tüm dövizleri getir',
                '/api/currency/<code>': 'Tek döviz getir',
                '/api/gold/all': 'Tüm altın fiyatlarını getir',
                '/api/silver/all': 'Tüm gümüş fiyatlarını getir'
            }
        }
    })

@app.route('/health', methods=['GET', 'HEAD'])
def health():
    """Sağlık kontrolü ve Veritabanı veri sayımı."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Tablo varlığını kontrol et (eğer tablo yoksa burası hata verecektir)
        cursor.execute('SELECT COUNT(*) as count FROM haberler')
        haberler_count = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM currencies')
        currency_count = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM golds')
        gold_count = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM silvers')
        silver_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'app': 'Nouvs + KuraBak Backend v5.0',
            'database': 'PostgreSQL',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'haberler_count': haberler_count,
                'currencies_count': currency_count,
                'golds_count': gold_count,
                'silvers_count': silver_count
            }
        }), 200
    except Exception as e:
        # Bu kısım, DATABASE_URL hatasını yakalar.
        logger.error(f"❌ Veritabanı bağlantı/tablo hatası: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': f"Veritabanı bağlantı/tablo hatası (Lütfen DATABASE_URL'i kontrol edin): {str(e)}"
        }), 500

@app.route('/api/update', methods=['POST'])
def manual_update():
    """Manuel tam güncelleme"""
    try:
        update_all()
        return jsonify({'success': True, 'message': 'Full update started'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------------------------
# BAŞLANGIÇ VE SCHEDULER
# ------------------------------------

# Gunicorn/Render tarafından dosya yüklendiğinde çalışacak kısım:
if init_db(): 
    # init_db başarılı olursa, ilk veriyi çek ve scheduler'ı başlat.
    # Bu blok Gunicorn çalıştırıldığında bir kez çalışır.
    update_all()
    start_scheduler()
else:
    logger.error("❌ Uygulama veritabanı hatası nedeniyle başlatılamadı.")


if __name__ == '__main__':
    # Geliştirme ortamında çalıştırmak için (Render'da bu çalışmayacak)
    port = int(os.environ.get('PORT', 5001))
    # debug=False, Scheduler'ın çift çalışmasını engeller.
    app.run(host='0.0.0.0', port=port, debug=False)
