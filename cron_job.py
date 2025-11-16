import time
import logging
from services.news_service import haberleri_cek

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_cron():
    logger.info("🚀 Haber Cron Sistemi Başladı (Her 1 saatte 1 güncelleme)")

    while True:
        try:
            logger.info("⏳ Haberler güncelleniyor...")
            eklenen = haberleri_cek()
            
            logger.info(f"✅ İşlem tamamlandı — Eklenen Haber: {eklenen}")

        except Exception as e:
            logger.error(f"❌ Cron hatası: {e}")

        # 1 SAAT BEKLE
        time.sleep(3600)


if __name__ == "__main__":
    start_cron()
