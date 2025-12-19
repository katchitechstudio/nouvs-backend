from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
import os
import atexit

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# IMPORTS
# ==========================================
from config import Config

from services.currency_service import fetch_currencies
from services.gold_service import fetch_golds
from services.silver_service import fetch_silvers
from services.news_service import haberleri_cek
from services.maintenance_service import weekly_maintenance

from routes.currency_routes import currency_bp
from routes.gold_routes import gold_bp
from routes.silver_routes import silver_bp
from routes.news_routes import news_bp

from models.db import get_db, put_db, close_all_connections
from models.currency_models import init_db

# ==========================================
# FLASK APP
# ==========================================
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Blueprint register
app.register_blueprint(currency_bp)
app.register_blueprint(gold_bp)
app.register_blueprint(silver_bp)
app.register_blueprint(news_bp)

# ==========================================
# SCHEDULER
# ==========================================
def init_scheduler():
    try:
        scheduler = BackgroundScheduler()

        # Haftalık bakım - Her Pazar sabahı 04:00
        scheduler.add_job(
            weekly_maintenance,
            trigger=CronTrigger(
                day_of_week='sun',
                hour=4,
                minute=0,
                second=0
            ),
            id="weekly_maintenance",
            name="Haftalık Bakım (Temizlik + Optimizasyon)",
            replace_existing=True
        )
        logger.info("📅 Haftalık bakım job'u eklendi (Her Pazar 04:00)")

        # Haberler (30 dakika)
        scheduler.add_job(
            haberleri_cek, 
            "interval", 
            minutes=30, 
            id="haber_job",
            name="Haber güncelleme"
        )

        # Finans güncellemeleri (10 dakika - KuraBak ile aynı)
        scheduler.add_job(
            fetch_currencies, 
            "interval", 
            minutes=10, 
            id="currency_job",
            name="Döviz güncelleme"
        )
        scheduler.add_job(
            fetch_golds, 
            "interval", 
            minutes=10, 
            id="gold_job",
            name="Altın güncelleme"
        )
        scheduler.add_job(
            fetch_silvers, 
            "interval", 
            minutes=10, 
            id="silver_job",
            name="Gümüş güncelleme"
        )

        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
        
        logger.info("🚀 Scheduler başlatıldı (Finans: 10 dakika, Haber: 30 dakika)")

    except Exception as e:
        logger.error(f"❌ Scheduler hata: {e}")


# ==========================================
# STARTUP
# ==========================================
logger.info("🔧 NouvsApp Backend başlıyor...")

# Database connection pool ve tablolar
init_db()

# Scheduler başlat
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    init_scheduler()

# Shutdown sırasında connection'ları kapat
atexit.register(close_all_connections)

# ==========================================
# ENDPOINTS
# ==========================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": "NouvsApp Backend (Optimized)",
        "status": "running",
        "version": "8.0",
        "database": "PostgreSQL + Redis",
        "features": [
            "Redis cache sistemi",
            "Connection pool (2-20)",
            "10 dakikalık finans güncelleme",
            "30 dakikalık haber güncelleme",
            "Haftalık otomatik bakım (Pazar 04:00)",
            "30 günlük veri saklama"
        ],
        "timestamp": datetime.now().isoformat()
    })


@app.route("/health", methods=["GET", "HEAD"])
def health():
    try:
        conn = get_db()
        cur = conn.cursor()

        # Tablo sayılarını al
        counts = {}
        
        tables = ['haberler', 'currencies', 'golds', 'silvers']
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            except:
                counts[table] = 0

        cur.close()
        put_db(conn)

        return jsonify({
            "status": "healthy",
            "counts": counts,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"❌ Health check hatası: {e}")
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route("/api/update", methods=["POST", "GET"])
def manual_update():
    """Manuel güncelleme endpoint'i"""
    try:
        logger.info("⚡ Manuel güncelleme tetiklendi...")
        
        haberleri_cek()
        fetch_currencies()
        fetch_golds()
        fetch_silvers()
        
        return jsonify({
            "success": True,
            "message": "Tüm veriler güncellendi",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Manuel güncelleme hatası: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==========================================
# DEVELOPMENT SERVER
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"🌍 Server aktif → Port: {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
