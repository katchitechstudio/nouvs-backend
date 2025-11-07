from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
import os
import sys

# ==========================================
# SYS.PATH SETUP - Modülleri bulmak için
# ==========================================
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC_DIR)  # app.py'nin bulunduğu klasör
sys.path.insert(0, os.path.join(SRC_DIR, 'models'))
sys.path.insert(0, os.path.join(SRC_DIR, 'services'))
sys.path.insert(0, os.path.join(SRC_DIR, 'routes'))

# ==========================================
# İMPORTLAR - Düz yapı (models. yok!)
# ==========================================
from config import Config
from currency_models import init_db, get_db
from currency_service import fetch_currencies, fetch_golds, fetch_silvers
from news_service import haberleri_cek
from currency_routes import currency_bp
from news_routes import news_bp

# ==========================================
# LOGGING SETUP
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# FLASK APP SETUP
# ==========================================
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Blueprint'leri kaydet
app.register_blueprint(currency_bp)
app.register_blueprint(news_bp)

# ==========================================
# SCHEDULER VE YARDIMCI FONKSİYONLAR
# ==========================================

def update_all():
    """Tüm verileri güncelle"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🔄 FULL UPDATE BAŞLANGIÇ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")
    
    try:
        haberleri_cek()
    except Exception as e:
        logger.error(f"❌ Haber çekme hatası: {e}")
    
    try:
        fetch_currencies()
    except Exception as e:
        logger.error(f"❌ Döviz çekme hatası: {e}")
    
    try:
        fetch_golds()
    except Exception as e:
        logger.error(f"❌ Altın çekme hatası: {e}")
    
    try:
        fetch_silvers()
    except Exception as e:
        logger.error(f"❌ Gümüş çekme hatası: {e}")
    
    logger.info(f"\n✅ FULL UPDATE TAMAMLANDI")
    logger.info(f"{'='*60}\n")

# ==========================================
# ADMIN UÇNOKTALARI
# ==========================================

@app.route('/', methods=['GET'])
def home():
    """Uygulama hakkında bilgi ve endpoint listesi."""
    return jsonify({
        'app': 'Habersel + KuraBak Backend',
        'status': 'running',
        'version': '6.0 (Stable & Production)',
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
                '/api/currency/history/<code>': 'Döviz geçmişi',
                '/api/currency/gold/all': 'Tüm altın fiyatlarını getir',
                '/api/currency/silver/all': 'Tüm gümüş fiyatlarını getir'
            }
        }
    })

@app.route('/health', methods=['GET', 'HEAD'])
def health():
    """Sağlık kontrolü ve Veritabanı veri sayımı."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
            'app': 'Habersel + KuraBak Backend v6.0',
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
        logger.error(f"Health check hatası: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': f"Veritabanı bağlantı/tablo hatası: {str(e)}"
        }), 500

@app.route('/api/update', methods=['POST'])
def manual_update():
    """Manuel tam güncelleme"""
    try:
        update_all()
        return jsonify({'success': True, 'message': 'Full update started'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==========================================
# BAŞLANGIÇ
# ==========================================

if __name__ == '__main__':
    logger.info("🚀 Uygulama başlatılıyor...")
    
    # Veritabanını başlatmaya çalış
    if init_db():
        logger.info("✅ Veritabanı hazır!")
        
        # İlk veri çekimi
        try:
            update_all()
        except Exception as e:
            logger.warning(f"⚠️ İlk veri çekimi sırasında sorun: {e}")

        try:
            scheduler = BackgroundScheduler()
            
            # Her 1 saatte bir haberler
            scheduler.add_job(
                func=haberleri_cek,
                trigger="interval",
                hours=1,
                id="haber_job"
            )
            
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
            logger.error(f"⚠️ Scheduler başlatma hatası: {e}")
            
        # Sunucuyu başlat
        port = int(os.environ.get('PORT', 5001))
        logger.info(f"🌐 Server başlıyor: 0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.error("❌ Uygulama veritabanı hatası nedeniyle başlatılamadı.")
        sys.exit(1)