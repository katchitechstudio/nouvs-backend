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
        try_rate = None
        for x in items:
            if x.get("code") == "TRY":
                try_rate = float(x.get("rate"))
                break
        
        if try_rate:
            logger.info(f"✅ TRY bulundu → {try_rate}")
        else:
            logger.warning("⚠️ TRY bulunamadı → USD bazlı hesaplama kullanılacak")
            try_rate = 1.0  # Fallback
        
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
            
            # 🔥 YENİ: Hem fiyat hem de değişim oranı hesapla
            # API'den gelen rate zaten TL karşılığı gibi görünüyor
            price_tl = rate_raw  # TL fiyatı
            
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
            
            # 🔥 YENİ: rate yerine price ve change_percent kaydet
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
