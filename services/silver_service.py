import requests
import logging
from models.db import get_db, put_db
from config import Config

logger = logging.getLogger(__name__)

def fetch_silvers():
    try:
        logger.info("🥈 Gümüş çekiliyor...")

        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/silverPrice"

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get("success"):
            logger.error("Gümüş API hatası.")
            return False

        item = data["result"]  # ✅ Dict

        name = "Gümüş"
        buying = float(item["buying"])
        selling = float(item["selling"])
        rate = buying

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO silvers (name, buying, selling, rate, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (name) DO UPDATE SET
                buying=EXCLUDED.buying,
                selling=EXCLUDED.selling,
                rate=EXCLUDED.rate,
                updated_at=CURRENT_TIMESTAMP
        """, (name, buying, selling, rate))

        cur.execute("INSERT INTO silver_history (name, rate) VALUES (%s, %s)", 
                    (name, rate))

        conn.commit()
        cur.close()
        put_db(conn)

        logger.info("✅ 1 gümüş güncellendi")
        return True

    except Exception as e:
        logger.error(f"Gümüş çekme hatası: {e}")
        return False
