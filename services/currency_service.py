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

def _get_try_rate(headers):
    """USD'den TRY oranını CollectAPI'den alır."""
    try:
        url = "https://api.collectapi.com/economy/currencyToAllv1"
        params = {'base': 'USD', 'int': 1}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get('success'): 
            return None
        for item in data.get('result', {}).get('data', []):
            if item.get('code') == 'TRY': 
                return item.get('rate')
        return None
    except Exception as e:
        logger.error(f"TRY rate çekilemedi: {str(e)}")
        _log_update('currency_base', 'error', f'TRY rate çekilemedi: {e}')
        return None

def fetch_currencies():
    """Dövizleri çeker ve veritabanına kaydeder."""
    try:
        logger.info(f"💱 Dövizler çekiliyor...")
        headers = {'authorization': f'apikey {Config.COLLECTAPI_TOKEN}'}
        try_rate = _get_try_rate(headers)
        if not try_rate: 
            logger.warning("TRY rate alınamadı")
            return False

        url = "https://api.collectapi.com/economy/currencyToAllv1"
        params = {'base': 'USD', 'int': len(Config.CURRENCIES_LIST)}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('success'):
            _log_update('currency', 'error', f"API hata: {data}")
            return False
        
        conn = get_db()
        cursor = conn.cursor()
        added = 0
        
        for item in data.get('result', {}).get('data', []):
            code = item.get('code')
            if code not in Config.CURRENCIES_LIST: 
                continue
            
            usd_rate = float(item.get('rate', 0))
            try_rate_value = float(try_rate)
            # TRY bazlı oranı hesapla
            final_rate = try_rate_value if code == 'USD' else (1.0 if code == 'TRY' else usd_rate * try_rate_value)
            
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