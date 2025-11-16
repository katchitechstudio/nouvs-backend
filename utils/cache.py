import time

CACHE = {}
CACHE_TIME = {}

def get_cache(key, max_age_seconds):
    """Cache varsa ve süresi dolmamışsa döndürür."""
    now = time.time()
    if key in CACHE and (now - CACHE_TIME[key] < max_age_seconds):
        return CACHE[key]
    return None

def set_cache(key, value):
    """Cache ekler veya günceller."""
    CACHE[key] = value
    CACHE_TIME[key] = time.time()
