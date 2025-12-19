import psycopg2
from psycopg2.pool import SimpleConnectionPool
from config import Config
import urllib.parse as urlparse
import os
import logging

logger = logging.getLogger(__name__)

# ==========================================
# DATABASE URL (Render, Heroku, Railway)
# ==========================================
DATABASE_URL = os.environ.get("DATABASE_URL", None)

if DATABASE_URL:
    # URL parse et
    url = urlparse.urlparse(DATABASE_URL)
    DB_USER = url.username
    DB_PASSWORD = url.password
    DB_HOST = url.hostname
    DB_PORT = url.port
    DB_NAME = url.path[1:]   # /dbname → dbname
    logger.info(f"📡 DATABASE_URL kullanılıyor (host: {DB_HOST})")
else:
    # Lokal ortam
    DB_USER = Config.DB_USER
    DB_PASSWORD = Config.DB_PASSWORD
    DB_HOST = Config.DB_HOST
    DB_PORT = Config.DB_PORT
    DB_NAME = Config.DB_NAME
    logger.info(f"📡 Local database kullanılıyor (host: {DB_HOST})")

# ==========================================
# CONNECTION POOL (2-20)
# ==========================================
try:
    db_pool = SimpleConnectionPool(
        minconn=2,   # Minimum 2 connection (KuraBak ile aynı)
        maxconn=20,  # Maximum 20 connection (KuraBak ile aynı)
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )
    logger.info("✅ Database connection pool oluşturuldu (2-20 connection)")
except Exception as e:
    logger.error(f"❌ Connection pool hatası: {e}")
    db_pool = None

# ==========================================
# PUBLIC METHODS
# ==========================================
def get_db():
    """Pool'dan bağlantı al"""
    if not db_pool:
        raise Exception("Connection pool başlatılamadı!")
    
    return db_pool.getconn()

def put_db(conn):
    """Bağlantıyı pool'a geri bırak"""
    if db_pool and conn:
        db_pool.putconn(conn)

def close_all_connections():
    """Tüm connection'ları kapat (shutdown sırasında)"""
    if db_pool:
        db_pool.closeall()
        logger.info("🔌 Tüm database connection'ları kapatıldı")
