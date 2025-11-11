import requests
import logging
from models.db import get_db, put_db
from config import Config

logger = logging.getLogger(__name__)

def fetch_golds():
    try:
        logger.info("🥇 Altınlar çekiliyor...")

        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/goldPrice"

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get("success"):
            logger.error("Altın API hatası.")
            return False

        items = data["result"]

        conn = get_db()
        cur = conn.cursor()
        added = 0

        for item in items:
            name = item["name"]

            if name not in Config.GOLD_FORMATS:
                continue

            cur.execute("""
                INSERT INTO golds (name, buying, selling, rate, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE SET
                    buying=EXCLUDED.buying,
                    selling=EXCLUDED.selling,
                    rate=EXCLUDED.rate,
                    updated_at=CURRENT_TIMESTAMP
            """, (name, float(item["buying"]), float(item["selling"]), float(item["rate"])))

            cur.execute("INSERT INTO gold_history (name, rate) VALUES (%s, %s)", 
                        (name, float(item["rate"])))
            added += 1

        conn.commit()
        cur.close()
        put_db(conn)

        logger.info(f"✅ {added} altın güncellendi")
        return True

    except Exception as e:
        logger.error(f"Altın çekme hatası: {e}")
        return False
