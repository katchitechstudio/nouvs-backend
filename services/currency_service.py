import requests
from datetime import datetime
import logging
from config import Config
from currency_models import get_db

logger = logging.getLogger(__name__)

def _log_update(update_type, status, message):
    """Veritabanına güncelleme logu kaydeder."""
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

def fetch_currencies():
    """Dövizleri çeker ve veritabanına kaydeder."""
    try:
        logger.info(f"💱 Dövizler çekiliyor...")
        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        
        # ✅ YENİ API: base=TRY, int=10 kullan
        url = "https://api.collectapi.com/economy/currencyToAll"
        params = {'base': 'TRY', 'int': 10}  # ✅ 10 TRY miktar
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('success'):
            _log_update('currency', 'error', f"API hata: {data}")
            return False
        
        conn = get_db()
        cursor = conn.cursor()
        added = 0
        
        # ✅ LOG: İlk 3 veriyi göster
        logger.info("📊 API'den gelen ilk 3 veri (10 TRY bazlı):")
        for item in data.get('result', {}).get('data', [])[:3]:
            code = item.get('code')
            rate = item.get('rate')
            final = 10.0 / rate if rate > 0 else 0
            logger.info(f"  {code}: rate={rate:.6f} → 1 {code} = {final:.4f} ₺")
        
        for item in data.get('result', {}).get('data', []):
            code = item.get('code')
            if code not in Config.CURRENCIES_LIST: 
                continue
            
            # ✅ FORMÜL: 10 TRY = rate Currency
            # Dolayısıyla: 1 Currency = (10 / rate) TRY
            rate = float(item.get('rate', 0))
            if rate <= 0:
                logger.warning(f"⚠️ {code} için geçersiz rate: {rate}")
                continue
                
            final_rate = 10.0 / rate
            
            # Atomik Kayıt/Güncelleme
            cursor.execute('''
                INSERT INTO currencies (code, name, rate, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    rate = EXCLUDED.rate,
                    updated_at = CURRENT_TIMESTAMP
            ''', (code, item.get('name'), final_rate))
            
            # Geçmişe kaydet
            cursor.execute('INSERT INTO currency_history (code, rate) VALUES (%s, %s)', (code, final_rate))
            added += 1

        conn.commit()
        cursor.close()
        conn.close()
        _log_update('currency', 'success', f'{added} currencies updated')
        logger.info(f"  ✅ {added} döviz güncellendi/eklendi")
        return True
        
    except Exception as e:
        logger.error(f"Döviz çekme hatası: {str(e)}")
        _log_update('currency', 'error', f'Çekme hatası: {e}')
        return False

def fetch_golds():
    """Altınları çeker ve veritabanına kaydeder."""
    try:
        logger.info(f"🥇 Altınlar çekiliyor...")
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
        
        for item in data.get('result', []):
            name = item.get('name')
            if name not in Config.GOLD_FORMATS: 
                continue

            # Atomik Kayıt/Güncelleme
            cursor.execute('''
                INSERT INTO golds (name, buying, selling, rate, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE SET
                    buying = EXCLUDED.buying,
                    selling = EXCLUDED.selling,
                    rate = EXCLUDED.rate,
                    updated_at = CURRENT_TIMESTAMP
            ''', (name, float(item.get('buying', 0)), float(item.get('selling', 0)), float(item.get('rate', 0))))
            
            # Geçmişe kaydet
            cursor.execute('INSERT INTO gold_history (name, rate) VALUES (%s, %s)', (name, float(item.get('rate', 0))))
            added += 1
            
        conn.commit()
        cursor.close()
        conn.close()
        _log_update('gold', 'success', f'{added} golds updated')
        logger.info(f"  ✅ {added} altın güncellendi/eklendi")
        return True
    except Exception as e:
        logger.error(f"Altın çekme hatası: {str(e)}")
        _log_update('gold', 'error', f'Çekme hatası: {e}')
        return False

def fetch_silvers():
    """Gümüşleri çeker ve veritabanına kaydeder."""
    try:
        logger.info(f"🥈 Gümüşler çekiliyor...")
        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        url = "https://api.collectapi.com/economy/silverPrice"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get('success'):
            _log_update('silver', 'error', f"API hata: {data}")
            return False
        
        conn = get_db()
        cursor = conn.cursor()
        added = 0
        
        for item in data.get('result', []):
            name = item.get('name')
            if name not in Config.SILVER_FORMATS: 
                continue

            # Atomik Kayıt/Güncelleme
            cursor.execute('''
                INSERT INTO silvers (name, buying, selling, rate, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE SET
                    buying = EXCLUDED.buying,
                    selling = EXCLUDED.selling,
                    rate = EXCLUDED.rate,
                    updated_at = CURRENT_TIMESTAMP
            ''', (name, float(item.get('buying', 0)), float(item.get('selling', 0)), float(item.get('rate', 0))))
            
            # Geçmişe kaydet
            cursor.execute('INSERT INTO silver_history (name, rate) VALUES (%s, %s)', (name, float(item.get('rate', 0))))
            added += 1
            
        conn.commit()
        cursor.close()
        conn.close()
        _log_update('silver', 'success', f'{added} silvers updated')
        logger.info(f"  ✅ {added} gümüş güncellendi/eklendi")
        return True
    except Exception as e:
        logger.error(f"Gümüş çekme hatası: {str(e)}")
        _log_update('silver', 'error', f'Çekme hatası: {e}')
        return False
