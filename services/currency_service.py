import requests
import logging
from models.db import get_db, put_db
from config import Config

logger = logging.getLogger(__name__)

def fetch_currencies():
    try:
        logger.info("💱 Dövizler çekiliyor (currencyToAll)...")
        
        headers = {
            'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'
        }
        
        # 🔥 YENİ ENDPOINT: currencyToAll (gerçek fiyatlar)
        url = "https://api.collectapi.com/economy/currencyToAll"
        params = {
            'int': '10',
            'base': 'USD'  # tag değil, base!
        }
        
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if not data.get("success"):
            logger.error(f"API hata: {data}")
            return False
        
        items = data.get("result", {}).get("data", [])
        if not isinstance(items, list) or len(items) == 0:
            logger.error("API döviz listesi boş.")
            return False
        
        logger.info(f"✅ {len(items)} döviz alındı")
        
        conn = get_db()
        cur = conn.cursor()
        
        # 🔥 ÖNCE TRY'Yİ BUL VE KAYDET!
        try_to_usd = None
        for row in items:
            if row.get("code") == "TRY":
                try_to_usd = float(row.get("rate"))  # 1 USD = X TRY
                logger.info(f"✅ TRY bulundu: 1 USD = {try_to_usd} TRY")
                break
        
        if not try_to_usd:
            logger.error("❌ TRY bulunamadı!")
            return False
        
        added = 0
        
        for row in items:
            code = row.get("code")
            name = row.get("name")
            
            try:
                usd_rate = float(row.get("rate"))  # 1 USD = X döviz
                
                # Fiyat hesapla
                if code == "TRY":
                    price_tl = 1.0  # 1 TL = 1 TL
                else:
                    # Diğer dövizler: 
                    # Örnek: EUR rate=0.86 (1 USD = 0.86 EUR)
                    # EUR fiyatı = (1 USD / 0.86 EUR) * 42.35 TRY = 49.24 TRY
                    price_tl = (1.0 / usd_rate) * try_to_usd
                
            except Exception as e:
                logger.error(f"{code} hesaplama hatası: {e}")
                continue
            
            # Değişim oranı için önceki fiyatı al
            cur.execute("SELECT rate FROM currencies WHERE code = %s", (code,))
            old_data = cur.fetchone()
            
            if old_data and old_data[0]:
                old_price = float(old_data[0])
                if old_price > 0:
                    change_percent = ((price_tl - old_price) / old_price) * 100
                else:
                    change_percent = 0.0
            else:
                change_percent = 0.0  # İlk kayıt
            
            # Veritabanına kaydet
            cur.execute("""
                INSERT INTO currencies (code, name, rate, change_percent, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code) DO UPDATE SET
                    name=EXCLUDED.name,
                    rate=EXCLUDED.rate,
                    change_percent=EXCLUDED.change_percent,
                    updated_at=CURRENT_TIMESTAMP
            """, (code, name, price_tl, change_percent))
            
            cur.execute("""
                INSERT INTO currency_history (code, rate)
                VALUES (%s, %s)
            """, (code, price_tl))
            
            added += 1
        
        conn.commit()
        cur.close()
        put_db(conn)
        
        # 🔥 YENİ: Cache'i temizle
        try:
            from utils.cache import clear_cache
            clear_cache()
        except Exception as e:
            logger.warning(f"Cache temizleme hatası: {e}")
        
        logger.info(f"✅ {added} döviz güncellendi")
        return True
        
    except Exception as e:
        logger.error(f"Döviz çekme hatası: {e}")
        return False
