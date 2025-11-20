import requests
from datetime import datetime, timedelta
import logging
from config import Config
from models.db import get_db, put_db

logger = logging.getLogger(__name__)

def haberleri_cek():
    """NewsAPI'den EN ÇOK HABER OLAN kategoriden haber çeker (3 popüler kategori)."""
    conn = None
    cursor = None
    
    try:
        # 🔥 Sadece 3 popüler kategoriyi test et (72 istek/gün)
        kategoriler = ["sports", "business", "technology"]
        
        en_cok_kategori = None
        en_cok_sayi = 0
        en_cok_haberler = []
        
        logger.info("📰 Kategoriler test ediliyor...")
        
        for kat in kategoriler:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "country": "tr",
                    "category": kat,
                    "apiKey": Config.NEWS_API_KEY
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                haberler = data.get("articles", [])
                haber_sayisi = len(haberler)
                logger.info(f"  📂 {kat}: {haber_sayisi} haber")
                
                if haber_sayisi > en_cok_sayi:
                    en_cok_sayi = haber_sayisi
                    en_cok_kategori = kat
                    en_cok_haberler = haberler
        
        if not en_cok_kategori or en_cok_sayi == 0:
            logger.warning("⚠ Hiçbir kategoride haber bulunamadı!")
            return 0
        
        logger.info(f"✅ En çok haber: {en_cok_kategori} ({en_cok_sayi} haber)")
        
        # Şimdi en çok haberi olan kategorinin haberlerini kaydet
        conn = get_db()
        cursor = conn.cursor()
        eklenen = 0
        
        for h in en_cok_haberler:
            baslik = h.get("title")
            aciklama = h.get("description")
            gorsel = h.get("urlToImage")
            url = h.get("url")
            kaynak = h.get("source", {}).get("name")
            tarih = h.get("publishedAt")
            
            # None olanları normalize et
            if not baslik or not url:
                continue
            
            # ISO tarih formatını datetime'a çevir
            try:
                tarih_obj = datetime.fromisoformat(tarih.replace("Z", "+00:00"))
            except:
                tarih_obj = datetime.utcnow()
            
            cursor.execute('''
                INSERT INTO haberler (baslik, aciklama, gorsel, kaynak, url, kategori, tarih)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (baslik) DO NOTHING
            ''', (
                baslik,
                aciklama,
                gorsel,
                kaynak,
                url,
                en_cok_kategori,  # ✔ En çok haberi olan kategori
                tarih_obj
            ))
            
            if cursor.rowcount > 0:
                eklenen += 1
        
        # 4 günden eski haberleri sil
        silme_tarihi = datetime.utcnow() - timedelta(days=4)
        cursor.execute('DELETE FROM haberler WHERE tarih < %s', (silme_tarihi,))
        silinen = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"✅ {eklenen} yeni haber kaydedildi ({en_cok_kategori}). 🗑 {silinen} eski haber silindi.")
        return eklenen
        
    except Exception as e:
        logger.error(f"❌ Haber çekme hatası: {e}")
        if conn:
            conn.rollback()
        return 0
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            put_db(conn)
