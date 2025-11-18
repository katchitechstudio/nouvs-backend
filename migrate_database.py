from models.db import get_db, put_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    try:
        conn = get_db()
        cur = conn.cursor()
        
        logger.info("📊 Kolonlar ekleniyor...")
        
        cur.execute("ALTER TABLE currencies ADD COLUMN IF NOT EXISTS change_percent FLOAT DEFAULT 0.0")
        cur.execute("ALTER TABLE golds ADD COLUMN IF NOT EXISTS change_percent FLOAT DEFAULT 0.0")
        cur.execute("ALTER TABLE silvers ADD COLUMN IF NOT EXISTS change_percent FLOAT DEFAULT 0.0")
        
        conn.commit()
        cur.close()
        put_db(conn)
        
        logger.info("✅ Migration tamamlandı!")
        
    except Exception as e:
        logger.error(f"❌ Hata: {e}")

if __name__ == "__main__":
    migrate()
