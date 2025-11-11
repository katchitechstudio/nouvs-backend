import requests
from datetime import datetime
import logging
from config import Config
from currency_models import get_db

logger = logging.getLogger(__name__)

def _log_update(update_type, status, message):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO update_logs (update_type, status, message)
            VALUES (%s, %s, %s)
        ''', (update_type, status, message))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Log kaydı yapılamadı: {e}")


# ----------------------------------------------------------
# ✅ 1) DÖVİZ
# CollectAPI → USD Base
# ----------------------------------------------------------
def fetch_currencies():
    try:
        logger.info("💱 Dövizler çekiliyor...")

        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/allCurrency"  # Doğru endpoint
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            _log_update("currency", "error", f"API hata: {data}")
            return False

        raw = data["result"]["data"]

        # USD→TRY bul
        usd_try = None
        for item in raw:
            if item["code"] == "TRY":
                usd_try = float(item["rate"])
                break

        if not usd_try:
            logger.error("TRY bulunamadı, döviz dönüşümü yapılamadı.")
            return False

        conn = get_db()
        cursor = conn.cursor()
        added = 0

        # LOG ilk 3
        logger.info("📊 İlk 3 döviz (TRY bazlı):")
        for item in raw[:3]:
            rate = float(item["rate"])
            final = rate / usd_try  # 1 TRY = X currency
            logger.info(f"  {item['code']} → 1 TRY = {final:.6f} {item['code']}")

        # Kaydet
        for item in raw:
            code = item["code"]
            if code not in Config.CURRENCIES_LIST:
                continue

            rate_usd_to_x = float(item["rate"])
            final_rate = rate_usd_to_x / usd_try  # 1 TRY = X code

            cursor.execute('''
                INSERT INTO currencies (code, name, rate, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code) DO UPDATE SET
                    name=EXCLUDED.name,
                    rate=EXCLUDED.rate,
                    updated_at=CURRENT_TIMESTAMP
            ''', (code, item.get("name"), final_rate))

            cursor.execute('INSERT INTO currency_history (code, rate) VALUES (%s, %s)',
                           (code, final_rate))

            added += 1

        conn.commit()
        cursor.close()
        conn.close()

        _log_update("currency", "success", f"{added} currencies updated")
        logger.info(f"✅ {added} döviz güncellendi/eklendi")
        return True

    except Exception as e:
        logger.error(f"Döviz çekme hatası: {e}")
        _log_update("currency", "error", f"Hata: {e}")
        return False


# ----------------------------------------------------------
# ✅ 2) ALTIN
# ----------------------------------------------------------
def fetch_golds():
    try:
        logger.info("🥇 Altınlar çekiliyor...")

        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/goldPrice"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            _log_update('gold', 'error', f"API hata: {data}")
            return False

        conn = get_db()
        cursor = conn.cursor()
        added = 0

        for item in data["result"]:
            name = item["name"]
            if name not in Config.GOLD_FORMATS:
                continue

            cursor.execute('''
                INSERT INTO golds (name, buying, selling, rate, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE SET
                    buying=EXCLUDED.buying,
                    selling=EXCLUDED.selling,
                    rate=EXCLUDED.rate,
                    updated_at=CURRENT_TIMESTAMP
            ''', (name, float(item["buying"]), float(item["selling"]), float(item["rate"])))

            cursor.execute('INSERT INTO gold_history (name, rate) VALUES (%s, %s)',
                           (name, float(item["rate"])))

            added += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ {added} altın güncellendi/eklendi")
        return True

    except Exception as e:
        logger.error(f"Altın çekme hatası: {e}")
        _log_update('gold', 'error', str(e))
        return False


# ----------------------------------------------------------
# ✅ 3) GÜMÜŞ  (DÜZELTİLEN KISIM)
# API → result {} TEK NESNE
# ----------------------------------------------------------
def fetch_silvers():
    try:
        logger.info("🥈 Gümüş çekiliyor...")

        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/silverPrice"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            _log_update("silver", "error", f"API hata: {data}")
            return False

        # ✅ TEK NESNE
        item = data["result"]

        name = "Gümüş"
        buying = float(item["buying"])
        selling = float(item["selling"])
        rate = buying

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO silvers (name, buying, selling, rate, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (name) DO UPDATE SET
                buying=EXCLUDED.buying,
                selling=EXCLUDED.selling,
                rate=EXCLUDED.rate,
                updated_at=CURRENT_TIMESTAMP
        ''', (name, buying, selling, rate))

        cursor.execute('INSERT INTO silver_history (name, rate) VALUES (%s, %s)',
                       (name, rate))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ 1 adet gümüş güncellendi")
        return True

    except Exception as e:
        logger.error(f"Gümüş çekme hatası: {e}")
        _log_update("silver", "error", f"Hata: {e}")
        return False
