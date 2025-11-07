import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
import logging

logger = logging.getLogger(__name__)

# News modelleri için import
def init_news_tables(cursor):
    """Habersel tablosunu oluşturur."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS haberler (
            id SERIAL PRIMARY KEY,
            baslik TEXT UNIQUE NOT NULL,
            aciklama TEXT,
            gorsel TEXT,
            kaynak TEXT,
            url TEXT,
            kategori TEXT,
            tarih TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Indexler
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kaynak ON haberler(kaynak)')

def get_db():
    """PostgreSQL bağlantısını döner."""
    try:
        conn = psycopg2.connect(Config.DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"❌ Veritabanına bağlanılamadı. Hata: {e}")
        raise ConnectionError("Veritabanı bağlantısı kurulamadı.")

def init_currency_tables(cursor):
    """KuraBak tablolarını oluşturur."""
    
    # Dövizler
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS currencies (
            id SERIAL PRIMARY KEY,
            code VARCHAR(10) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            rate FLOAT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Altınlar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS golds (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            buying FLOAT NOT NULL,
            selling FLOAT NOT NULL,
            rate FLOAT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Gümüşler
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS silvers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            buying FLOAT NOT NULL,
            selling FLOAT NOT NULL,
            rate FLOAT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Geçmiş Tabloları
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS currency_history (
            id SERIAL PRIMARY KEY,
            code VARCHAR(10) NOT NULL,
            rate FLOAT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gold_history (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            rate FLOAT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS silver_history (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            rate FLOAT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Log Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS update_logs (
            id SERIAL PRIMARY KEY,
            update_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            message VARCHAR(255),
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Indexler
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_currency_code ON currencies(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_gold_name ON golds(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_silver_name ON silvers(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_currency_history_code ON currency_history(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_gold_history_name ON gold_history(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_silver_history_name ON silver_history(name)')


def init_db():
    """Tüm veritabanı tablolarını (Haber + Kur) oluşturur."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Haber tablolarını başlat
        init_news_tables(cursor)
        
        # Kur tablolarını başlat
        init_currency_tables(cursor)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✅ PostgreSQL veritabanı (Kur + Haber) hazır!")
        return True
    except Exception as e:
        logger.error(f"❌ Veritabanı başlatma hatası: {e}")
        return False