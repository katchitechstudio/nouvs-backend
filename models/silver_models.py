from models.db import get_db, put_db
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# GÜMÜŞ TABLOLARI OLUŞTURMA
# -------------------------------------------------------------

def create_silver_tables():
    """Gümüş tablolarını oluşturur (bir defaya mahsus çalıştırılabilir)."""
    try:
        conn = get_db()
        cur = conn.cursor()

        # Ana gümüş tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS silvers (
                name VARCHAR(50) PRIMARY KEY,
                buying NUMERIC(15, 4),
                selling NUMERIC(15, 4),
                rate NUMERIC(15, 4),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Gümüş geçmiş tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS silver_history (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50),
                rate NUMERIC(15, 4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cur.close()
        put_db(conn)

        logger.info("✅ Silver tabloları oluşturuldu.")
    except Exception as e:
        logger.error(f"Silver tablo oluşturma hatası: {e}")


# -------------------------------------------------------------
# GÜMÜŞ VERİ SORGULARI
# -------------------------------------------------------------

def get_all_silvers():
    """Veritabanındaki son gümüş fiyatlarını döndürür."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT name, buying, selling, rate, updated_at
            FROM silvers
        """)

        rows = cur.fetchall()
        cur.close()
        put_db(conn)

        result = []
        for row in rows:
            result.append({
                "name": row[0],
                "buying": float(row[1]),
                "selling": float(row[2]),
                "rate": float(row[3]),
                "updated_at": row[4].isoformat()
            })

        return result

    except Exception as e:
        logger.error(f"Gümüş listesi alınamadı: {e}")
        return []


def get_silver_history(name: str = "Gümüş", limit: int = 50):
    """Gümüş geçmiş fiyat hareketlerini döndürür."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT rate, created_at
            FROM silver_history
            WHERE name = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (name, limit))

        rows = cur.fetchall()
        cur.close()
        put_db(conn)

        return [
            {
                "rate": float(r[0]),
                "created_at": r[1].isoformat()
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"Gümüş geçmişi alınamadı: {e}")
        return []
