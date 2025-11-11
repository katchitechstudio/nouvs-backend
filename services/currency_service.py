import requests
import logging
from models.db import get_db, put_db
from config import Config

logger = logging.getLogger(__name__)

def fetch_currencies():
    try:
        logger.info("💱 Dövizler çekiliyor...")

        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/allCurrency"

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get("success"):
            logger.error(f"API hata: {data}")
            return False

        items = data["result"]["data"]

        # USD → TRY bul
        usd_try = None
        for row in items:
            if row["code"] == "TRY":
                usd_try = float(row["rate"])
                break

        if not usd_try:
            logger.error("TRY bulunamadı.")
            return False

        conn = get_db()
        cur = conn.cursor()
        added = 0

        for row in items:
            code = row["code"]
            name = row["name"]
            rate_usd_to_x = float(row["rate"])
            final_rate = rate_usd_to_x / usd_try  

            cur.execute("""
                INSERT INTO currencies (code, name, rate, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code) DO UPDATE SET
                    name=EXCLUDED.name,
                    rate=EXCLUDED.rate,
                    updated_at=CURRENT_TIMESTAMP
            """, (code, name, final_rate))

            cur.execute("""INSERT INTO currency_history (code, rate) VALUES (%s, %s)""",
                        (code, final_rate))
            added += 1

        conn.commit()
        cur.close()
        put_db(conn)

        logger.info(f"✅ {added} döviz güncellendi")
        return True

    except Exception as e:
        logger.error(f"Döviz çekme hatası: {e}")
        return False
