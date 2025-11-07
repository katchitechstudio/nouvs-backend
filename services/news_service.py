import requests
from datetime import datetime, timedelta
import logging
from config import Config
from currency_models import get_db

logger = logging.getLogger(__name__)

def haberleri_cek():
    """CollectAPI'den haberler çeker ve veritabanına kaydeder."""
    
    saat = datetime.now().hour
    # Saate göre kategori rotasyonu
    kategori = Config.KATEGORILER[saat % len(Config.KATEGORILER)]
    
    logger.info(f"📄 Haberler çekiliyor...")
    logger.info(f"  📂 Kategori: {kategori}")
    logger.info(f"  🎯 Kaynaklar: {', '.join(Config.ALLOWED_SOURCES)}")
    
    try:
        response = requests.get(
            "https://api.collectapi.com/news/getNews",
            headers={
                "authorization": f"apikey {Config.COLLECTAPI_TOKEN}",
                "content-type": "application/json"
            },
            params={
                "country": "tr",
                "tag": kategori
            },
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"  ❌ HTTP Hatası: {response.status_code}")
            return 0
        
        data = response.json()
        if not data.get('success'):
            logger.warning(f"  ❌ API başarısız: {data.get('message', 'No message')}")
            return 0

        haberler = data.get('result', [])
        conn = get_db()
        cursor = conn.cursor()
        eklenen = 0
        
        for haber in haberler:
            kaynak = haber.get('source', '').strip()
            
            if kaynak not in Config.ALLOWED_SOURCES:
                continue
            
            # Atomik Kayıt: ON CONFLICT (baslik) DO NOTHING ile mükerrer kayıt önlenir
            cursor.execute('''
                INSERT INTO haberler (baslik, aciklama, gorsel, kaynak, url, kategori, tarih)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (baslik) DO NOTHING
            ''', (
                haber.get('name'),
                haber.get('description'),
                haber.get('image'),
                kaynak,
                haber.get('url'),
                kategori,
                haber.get('date') 
            ))
            
            if cursor.rowcount > 0:
                eklenen += 1
        
        # 7 günden eski haberleri sil (Temizlik)
        silme_tarihi = datetime.now() - timedelta(days=7)
        cursor.execute('DELETE FROM haberler WHERE tarih < %s', (silme_tarihi,))
        silinen = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"  ✅ {eklenen} yeni haber eklendi. {silinen} eski haber silindi.")
        return eklenen
            
    except Exception as e:
        logger.error(f"  ❌ Haber çekme hatası: {e}")
        return 0