from models.db import get_db, put_db
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# ALTIN VERİSİ MODELİ
# -------------------------------------------------------------

def create_gold_tables():
    """Altın tablolarını oluşturur (bir defaya mahsus)."""
    try:
        conn = get_db()
        cur = conn.cursor()

        # Altın ana tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS golds (
                name VARCHAR(80) PRIMARY KEY,
                buying NUMERIC(15, 4),
                selling NUMERIC(15, 4),
                rate NUMERIC(15, 4),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Altın geçmiş tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_history (
                id SERIAL PRIMARY KEY,
                name VARCHAR(80),
                rate NUMERIC(15, 4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cur.close()
        put_db(conn)

        logger.info("✅ Gold tabloları oluşturuldu.")
    except Exception as e:
        logger.error(f"Gold tablo oluşturma hatası: {e}")


# -------------------------------------------------------------
# ALTIN SORGULARI
# -------------------------------------------------------------

def get_all_golds():
    """Tüm altın fiyatlarını döndürür."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT name, buying, selling, rate, updated_at
            FROM golds
            ORDER BY name ASC
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
        logger.error(f"Gold listesi alınamadı: {e}")
        return []


def get_gold_history(name: str, limit: int = 50):
    """Bir altın türünün geçmiş fiyatlarını döndürür."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT rate, created_at
            FROM gold_history
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
        logger.error(f"Gold geçmişi alınamadı: {e}")
        return []
