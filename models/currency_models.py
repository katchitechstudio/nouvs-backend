from models.db import get_db, put_db
import logging

logger = logging.getLogger(__name__)

# ==========================================
# HABER TABLOLARI
# ==========================================
def init_news_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS haberler (
            id SERIAL PRIMARY KEY,
            baslik TEXT UNIQUE NOT NULL,
            aciklama TEXT,
            gorsel TEXT,
            kaynak TEXT,
            url TEXT,
            kategori TEXT,
            tarih TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kaynak ON haberler(kaynak);")

# ==========================================
# KUR TABLOLARI
# ==========================================
def init_currency_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS currencies (
            code VARCHAR(10) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            rate FLOAT NOT NULL,
            change_percent FLOAT DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS currency_history (
            id SERIAL PRIMARY KEY,
            code VARCHAR(10),
            rate FLOAT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS golds (
            name VARCHAR(100) PRIMARY KEY,
            buying FLOAT,
            selling FLOAT,
            rate FLOAT,
            change_percent FLOAT DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_history (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            rate FLOAT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS silvers (
            name VARCHAR(100) PRIMARY KEY,
            buying FLOAT,
            selling FLOAT,
            rate FLOAT,
            change_percent FLOAT DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS silver_history (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            rate FLOAT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS update_logs (
            id SERIAL PRIMARY KEY,
            update_type VARCHAR(50),
            status VARCHAR(20),
            message VARCHAR(255),
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)

# ==========================================
# INIT DB
# ==========================================
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        init_news_tables(cur)
        init_currency_tables(cur)
        conn.commit()
        cur.close()
        put_db(conn)
        logger.info("✅ Veritabanı tabloları oluşturuldu.")
        return True
    except Exception as e:
        logger.error(f"❌ Veritabanı başlatma hatası: {e}")
        return False
