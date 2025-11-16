import requests
from datetime import datetime, timedelta
import logging
from config import Config
from models.db import get_db

logger = logging.getLogger(__name__)

def haberleri_cek():
    """NewsAPI'den haber çeker ve veritabanına kaydeder."""

    saat = datetime.now().hour
    kategori = Config.KATEGORILER[saat % len(Config.KATEGORILER)]

    logger.info("📰 Haberler çekiliyor...")
    logger.info(f"  📂 Kategori: {kategori}")

    try:
        response = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "country": "tr",
                "category": kategori,
                "apiKey": Config.NEWS_API_KEY
            },
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"❌ HTTP Hatası: {response.status_code}")
            return 0

        data = response.json()

        if data.get("status") != "ok":
            logger.error(f"❌ API Hatası: {data.get('message')}")
            return 0

        haberler = data.get("articles", [])
        if not haberler:
            logger.warning("⚠ Haber bulunamadı!")
            return 0

        conn = get_db()
        cursor = conn.cursor()
        eklenen = 0

        for h in haberler:
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
                kategori,
                tarih_obj
            ))

            if cursor.rowcount > 0:
                eklenen += 1

        # 7 günden eski haberleri sil
        silme_tarihi = datetime.utcnow() - timedelta(days=7)
        cursor.execute('DELETE FROM haberler WHERE tarih < %s', (silme_tarihi,))
        silinen = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ {eklenen} yeni haber kaydedildi. 🗑 {silinen} eski haber silindi.")
        return eklenen

    except Exception as e:
        logger.error(f"❌ Haber çekme hatası: {e}")
        return 0
