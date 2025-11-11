import requests
import logging
from models.db import get_db, put_db
from config import Config

logger = logging.getLogger(__name__)


def fetch_currencies():
    try:
        logger.info("💱 Dövizler çekiliyor...")

        headers = {
            'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'
        }
        url = "https://api.collectapi.com/economy/allCurrency"

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        # ✅ API success kontrolü
        if not data.get("success"):
            logger.error(f"API hata: {data}")
            return False

        # ✅ Gerçek format: result → LIST
        items = data.get("result", [])

        if not isinstance(items, list) or len(items) == 0:
            logger.error("API döviz listesi boş veya hatalı.")
            return False

        # ✅ USD → TRY ORANI BUL
        usd_try = None
        for row in items:
            if row.get("code") == "TRY":
                try:
                    usd_try = float(row.get("rate"))
                except:
                    usd_try = None
                break

        if not usd_try:
            logger.error("TRY oranı bulunamadı.")
            return False

        conn = get_db()
        cur = conn.cursor()
        added = 0

        # ✅ TÜM DÖVİZLERİ İŞLE
        for row in items:
            code = row.get("code")
            name = row.get("name")

            try:
                rate_usd_to_x = float(row.get("rate"))
            except:
                continue

            # ✅ Oranı 1 TRY bazlı hesapla
            final_rate = rate_usd_to_x / usd_try

            cur.execute("""
                INSERT INTO currencies (code, name, rate, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code) DO UPDATE SET
                    name=EXCLUDED.name,
                    rate=EXCLUDED.rate,
                    updated_at=CURRENT_TIMESTAMP
            """, (code, name, final_rate))

            cur.execute("""
                INSERT INTO currency_history (code, rate)
                VALUES (%s, %s)
            """, (code, final_rate))

            added += 1

        conn.commit()
        cur.close()
        put_db(conn)

        logger.info(f"✅ {added} döviz güncellendi")
        return True

    except Exception as e:
        logger.error(f"Döviz çekme hatası: {e}")
        return False
