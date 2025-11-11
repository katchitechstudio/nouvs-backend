from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
import os

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# IMPORTS (Artık temiz mimari)
# ==========================================
from config import Config

from services.currency_service import fetch_currencies
from services.gold_service import fetch_golds
from services.silver_service import fetch_silvers
from services.news_service import haberleri_cek

from routes.currency_routes import currency_bp
from routes.gold_routes import gold_bp
from routes.silver_routes import silver_bp
from routes.news_routes import news_bp

from models.db import get_db, put_db

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
# UPDATE MANAGER
# ==========================================
def update_all():
    logger.info("\n================ FULL UPDATE ================\n")

    try:
        haberleri_cek()
    except Exception as e:
        logger.error(f"Haber hatası → {e}")

    try:
        fetch_currencies()
    except Exception as e:
        logger.error(f"Döviz hatası → {e}")

    try:
        fetch_golds()
    except Exception as e:
        logger.error(f"Altın hatası → {e}")

    try:
        fetch_silvers()
    except Exception as e:
        logger.error(f"Gümüş hatası → {e}")

    logger.info("\n✅ FULL UPDATE TAMAMLANDI\n")


# ==========================================
# SCHEDULER
# ==========================================
def init_scheduler():
    try:
        scheduler = BackgroundScheduler()

        scheduler.add_job(haberleri_cek, "interval", hours=1, id="haber_job")
        scheduler.add_job(update_all, "interval", minutes=60, id="finance_job")

        scheduler.start()
        logger.info("✅ Scheduler başlatıldı.")
    except Exception as e:
        logger.error(f"Scheduler hata: {e}")


# ==========================================
# STARTUP
# ==========================================
logger.info("🚀 Backend başlatılıyor...")

try:
    update_all()
except Exception as e:
    logger.warning(f"İlk güncelleme sorunlu: {e}")

init_scheduler()


# ==========================================
# ENDPOINTS
# ==========================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": "Habersel + KuraBak Backend",
        "status": "running",
        "version": "7.0",
        "database": "PostgreSQL",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM haberler")
        haber = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM currencies")
        doviz = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM golds")
        altin = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM silvers")
        gumus = cur.fetchone()[0]

        cur.close()
        put_db(conn)

        return jsonify({
            "status": "healthy",
            "haber": haber,
            "doviz": doviz,
            "altin": altin,
            "gumus": gumus
        }), 200

    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/api/update", methods=["POST"])
def manual_update():
    try:
        update_all()
        return {"success": True}, 200
    except:
        return {"success": False}, 500


# ==========================================
# DEVELOPMENT SERVER
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"🌍 Local server aktif → {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
