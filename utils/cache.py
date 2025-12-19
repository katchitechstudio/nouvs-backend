import redis
import logging
from config import Config

logger = logging.getLogger(__name__)

# Redis client
redis_client = None

def init_redis():
    """Redis bağlantısını başlat"""
    global redis_client
    
    if not Config.REDIS_URL:
        logger.warning("⚠️ REDIS_URL bulunamadı, cache devre dışı")
        return False
    
    try:
        redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis bağlantısı başarılı")
        return True
    except Exception as e:
        logger.error(f"❌ Redis bağlantı hatası: {e}")
        redis_client = None
        return False

def get_cache(key):
    """
    Cache'den veri al
    
    Args:
        key: Cache anahtarı (prefix ile kullan: "nouvsapp:currencies")
    
    Returns:
        Cached data or None
    """
    if not redis_client:
        return None
    
    try:
        data = redis_client.get(key)
        if data:
            logger.debug(f"🎯 Cache hit: {key}")
        return data
    except Exception as e:
        logger.error(f"❌ Cache get hatası ({key}): {e}")
        return None

def set_cache(key, data, ttl=None):
    """
    Cache'e veri kaydet
    
    Args:
        key: Cache anahtarı (prefix ile kullan: "nouvsapp:currencies")
        data: Kaydedilecek veri (string olmalı, JSON.stringify edilmiş)
        ttl: Time-to-live (saniye), None ise Config.CACHE_TIMEOUT kullanılır
    """
    if not redis_client:
        return False
    
    try:
        if ttl is None:
            ttl = Config.CACHE_TIMEOUT
        
        redis_client.setex(key, ttl, data)
        logger.debug(f"💾 Cache set: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"❌ Cache set hatası ({key}): {e}")
        return False

def clear_cache(pattern="nouvsapp:*"):
    """
    Cache'i temizle (sadece NouvsApp keylerini)
    
    Args:
        pattern: Silinecek key pattern'i (default: nouvsapp:*)
    """
    if not redis_client:
        logger.warning("⚠️ Redis bağlantısı yok, cache temizlenemedi")
        return False
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"🗑️ {len(keys)} cache key temizlendi ({pattern})")
        else:
            logger.info(f"✅ Temizlenecek cache key yok ({pattern})")
        return True
    except Exception as e:
        logger.error(f"❌ Cache temizleme hatası: {e}")
        return False

# Redis'i başlat (import edildiğinde)
init_redis()
