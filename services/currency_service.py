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

        if not data.get("success"):
            logger.error(f"API hata: {data}")
            return False

        items = data.get("result", [])

        if not isinstance(items, list) or len(items) == 0:
            logger.error("API döviz listesi boş.")
            return False

        # ✅ TRY var mı kontrol et
        try_value = None
        for x in items:
            if x.get("code") == "TRY":
                try_value = float(x.get("rate"))
                break

        if try_value:
            logger.info(f"✅ TRY bulundu → {try_value}")
        else:
            logger.warning("⚠️ TRY bulunamadı → USD bazlı hesaplama kullanılacak")

        conn = get_db()
        cur = conn.cursor()
        added = 0

        for row in items:
            code = row.get("code")
            name = row.get("name")

            try:
                rate_raw = float(row.get("rate"))
            except:
                continue

            # ✅ TRY yoksa direk kullan
            if try_value:
                final_rate = rate_raw / try_value
            else:
                final_rate = rate_raw  # fallback

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
