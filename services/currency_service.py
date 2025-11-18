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
            'int': '10',  # 10 USD bazında
            'tag': 'USD'  # USD'den diğer para birimlerine
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
        added = 0
        
        for row in items:
            code = row.get("code")
            name = row.get("name")
            
            try:
                # 🔥 YENİ: rate = 1 USD'nin TL karşılığı
                usd_rate = float(row.get("rate"))  # 1 USD = X döviz
                
                # TRY için özel hesaplama
                if code == "TRY":
                    price_tl = 1.0  # 1 TL = 1 TL
                    try_to_usd = usd_rate  # Referans için sakla
                else:
                    # Diğer dövizler: TRY üzerinden hesapla
                    # Önce TRY/USD oranını bul
                    cur.execute("SELECT rate FROM currencies WHERE code = 'TRY'")
                    try_data = cur.fetchone()
                    
                    if try_data and try_data[0]:
                        try_to_usd = float(try_data[0])
                        # Örnek: EUR -> (1 EUR = 0.86 USD) * (42.35 TRY/USD) = 36.42 TRY
                        price_tl = (1 / usd_rate) * try_to_usd
                    else:
                        # TRY henüz yok, atla
                        logger.warning(f"TRY bulunamadı, {code} atlanıyor")
                        continue
                
            except Exception as e:
                logger.error(f"{code} hesaplama hatası: {e}")
                continue
            
            # Değişim oranı için önceki fiyatı al
            cur.execute("SELECT rate FROM currencies WHERE code = %s", (code,))
            old_data = cur.fetchone()
            
            if old_data and old_data[0]:
                old_price = float(old_data[0])
                # Yüzde değişim hesapla
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
        
        logger.info(f"✅ {added} döviz güncellendi")
        return True
        
    except Exception as e:
        logger.error(f"Döviz çekme hatası: {e}")
        return False
