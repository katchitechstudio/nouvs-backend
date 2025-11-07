from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import logging

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─────────────────────────────────────────────
# ⚙️ AYARLAR - HABERSELv3
# ─────────────────────────────────────────────

COLLECTAPI_TOKEN = os.environ.get('COLLECTAPI_TOKEN', '7DO9zDxEEcnOASXEwou6np:0wARGCUrkfYSvQcQaQV3lM')
DATABASE_URL = os.environ.get('DATABASE_URL')

# ✅ GÜNCEL: 4 kaliteli kaynak
ALLOWED_SOURCES = ['NTV', 'CNN', 'Cumhuriyet', 'HaberTürk']

# ✅ GÜNCEL: 5 kategori rotasyonu
KATEGORILER = ["general", "economy", "sport", "health", "technology"]

# ─────────────────────────────────────────────
# ⚙️ AYARLAR - KURABAK
# ─────────────────────────────────────────────

# Dövizler (20 para)
CURRENCIES_LIST = [
    'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CNY', 'AED', 'SAR', 'KWD', 'CAD',
    'INR', 'AUD', 'NZD', 'SGD', 'HKD', 'SEK', 'NOK', 'DKK', 'BRL', 'MXN', 'TRY'
]

# Altın formatları (5)
GOLD_FORMATS = [
    'Gram Altın',
    'Çeyrek Altın',
    'Yarım Altın',
    'Tam Altın',
    'Cumhuriyet Altını'
]

# Gümüş formatları (1)
SILVER_FORMATS = ['Gümüş']

# ─────────────────────────────────────────────
# 🗄️ DATABASE FUNCTIONS
# ─────────────────────────────────────────────

def get_db():
    """PostgreSQL bağlantısı"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Veritabanı tablolarını oluştur"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Habersel tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS haberler (
                id SERIAL PRIMARY KEY,
                baslik TEXT UNIQUE NOT NULL,
                aciklama TEXT,
                gorsel TEXT,
                kaynak TEXT,
                url TEXT,
                kategori TEXT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # KuraBak tabloları
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS currencies (
                id SERIAL PRIMARY KEY,
                code VARCHAR(10) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                rate FLOAT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS golds (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                buying FLOAT NOT NULL,
                selling FLOAT NOT NULL,
                rate FLOAT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS silvers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                buying FLOAT NOT NULL,
                selling FLOAT NOT NULL,
                rate FLOAT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS currency_history (
                id SERIAL PRIMARY KEY,
                code VARCHAR(10) NOT NULL,
                rate FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gold_history (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                rate FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS silver_history (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                rate FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS update_logs (
                id SERIAL PRIMARY KEY,
                update_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                message VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Indexler
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kaynak ON haberler(kaynak)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_currency_code ON currencies(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gold_name ON golds(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_silver_name ON silvers(name)')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ PostgreSQL veritabanı hazır!")
        return True
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        return False

# ─────────────────────────────────────────────
# 🔄 HABERSEL FUNCTIONS
# ─────────────────────────────────────────────

def haberleri_cek():
    """CollectAPI'den haberler çek"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Haberler çekiliyor...")
    
    saat = datetime.now().hour
    kategori = KATEGORILER[saat % len(KATEGORILER)]
    
    print(f"  📂 Kategori: {kategori}")
    print(f"  🎯 Kaynaklar: {', '.join(ALLOWED_SOURCES)}")
    
    try:
        response = requests.get(
            "https://api.collectapi.com/news/getNews",
            headers={
                "authorization": f"apikey {COLLECTAPI_TOKEN}",
                "content-type": "application/json"
            },
            params={
                "country": "tr",
                "tag": kategori
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                haberler = data.get('result', [])
                
                conn = get_db()
                cursor = conn.cursor()
                
                eklenen = 0
                
                for haber in haberler:
                    try:
                        kaynak = haber.get('source', '').strip()
                        
                        if kaynak not in ALLOWED_SOURCES:
                            continue
                        
                        cursor.execute('''
                            INSERT INTO haberler (baslik, aciklama, gorsel, kaynak, url, kategori, tarih)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            haber.get('name'),
                            haber.get('description'),
                            haber.get('image'),
                            kaynak,
                            haber.get('url'),
                            kategori,
                            haber.get('date') 
                        ))
                        eklenen += 1
                    except psycopg2.IntegrityError:
                        conn.rollback()
                        pass
                
                conn.commit()
                
                silme_tarihi = datetime.now() - timedelta(days=7)
                cursor.execute('''
                    DELETE FROM haberler 
                    WHERE tarih < %s
                ''', (silme_tarihi,))
                silinen = cursor.rowcount
                conn.commit()
                
                cursor.close()
                conn.close()
                
                print(f"  ✅ {eklenen} yeni haber eklendi")
                print(f"  🗑️  {silinen} eski haber silindi")
                return eklenen
            else:
                print(f"  ❌ API başarısız")
                return 0
        else:
            print(f"  ❌ HTTP Hatası: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"  ❌ Hata: {e}")
        return 0

# ─────────────────────────────────────────────
# 💱 KURABAK FUNCTIONS
# ─────────────────────────────────────────────

def _get_try_rate(headers):
    """TRY/USD oranını al"""
    try:
        url = "https://api.collectapi.com/economy/currencyToAllv1"
        params = {
            'base': 'USD',
            'int': 1
        }
        
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
        logger.error(f"Error getting TRY rate: {str(e)}")
        return None

def fetch_currencies():
    """Dövizleri çek ve cache'le"""
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 💱 Dövizler çekiliyor...")
        
        headers = {
            'authorization': f'apikey {COLLECTAPI_TOKEN}'
        }
        
        try_rate = _get_try_rate(headers)
        if not try_rate:
            logger.error("TRY rate couldn't be fetched")
            return False
        
        print(f"  TRY/USD: {try_rate}")
        
        url = "https://api.collectapi.com/economy/currencyToAllv1"
        params = {
            'base': 'USD',
            'int': len(CURRENCIES_LIST)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            logger.error(f"CollectAPI error: {data}")
            return False
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Eski verileri sil
        cursor.execute('DELETE FROM currencies')
        
        added = 0
        for item in data.get('result', {}).get('data', []):
            code = item.get('code')
            
            if code not in CURRENCIES_LIST:
                continue
            
            usd_rate = float(item.get('rate', 0))
            try_rate_value = float(try_rate)
            
            if code == 'USD':
                final_rate = try_rate_value
            elif code == 'TRY':
                final_rate = 1.0
            else:
                final_rate = usd_rate * try_rate_value
            
            cursor.execute('''
                INSERT INTO currencies (code, name, rate)
                VALUES (%s, %s, %s)
            ''', (code, item.get('name'), final_rate))
            
            # Geçmişe kaydet
            cursor.execute('''
                INSERT INTO currency_history (code, rate)
                VALUES (%s, %s)
            ''', (code, final_rate))
            
            added += 1
        
        conn.commit()
        
        # Log kaydı
        cursor.execute('''
            INSERT INTO update_logs (update_type, status, message)
            VALUES (%s, %s, %s)
        ''', ('currency', 'success', f'{added} currencies updated'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"  ✅ {added} döviz eklendi")
        return True
        
    except Exception as e:
        logger.error(f"Error fetching currencies: {str(e)}")
        return False

def fetch_golds():
    """Altınları çek"""
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🥇 Altınlar çekiliyor...")
        
        headers = {
            'authorization': f'apikey {COLLECTAPI_TOKEN}'
        }
        
        url = "https://api.collectapi.com/economy/goldPrice"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            logger.error(f"CollectAPI error: {data}")
            return False
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM golds')
        
        added = 0
        for item in data.get('result', []):
            name = item.get('name')
            
            if name not in GOLD_FORMATS:
                continue
            
            cursor.execute('''
                INSERT INTO golds (name, buying, selling, rate)
                VALUES (%s, %s, %s, %s)
            ''', (name, float(item.get('buying', 0)), float(item.get('selling', 0)), float(item.get('rate', 0))))
            
            # Geçmişe kaydet
            cursor.execute('''
                INSERT INTO gold_history (name, rate)
                VALUES (%s, %s)
            ''', (name, float(item.get('rate', 0))))
            
            added += 1
        
        conn.commit()
        
        cursor.execute('''
            INSERT INTO update_logs (update_type, status, message)
            VALUES (%s, %s, %s)
        ''', ('gold', 'success', f'{added} golds updated'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"  ✅ {added} altın eklendi")
        return True
        
    except Exception as e:
        logger.error(f"Error fetching golds: {str(e)}")
        return False

def fetch_silvers():
    """Gümüşleri çek"""
    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🥈 Gümüşler çekiliyor...")
        
        headers = {
            'authorization': f'apikey {COLLECTAPI_TOKEN}'
        }
        
        url = "https://api.collectapi.com/economy/silverPrice"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            logger.error(f"CollectAPI error: {data}")
            return False
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM silvers')
        
        added = 0
        for item in data.get('result', []):
            name = item.get('name')
            
            if name not in SILVER_FORMATS:
                continue
            
            cursor.execute('''
                INSERT INTO silvers (name, buying, selling, rate)
                VALUES (%s, %s, %s, %s)
            ''', (name, float(item.get('buying', 0)), float(item.get('selling', 0)), float(item.get('rate', 0))))
            
            # Geçmişe kaydet
            cursor.execute('''
                INSERT INTO silver_history (name, rate)
                VALUES (%s, %s)
            ''', (name, float(item.get('rate', 0))))
            
            added += 1
        
        conn.commit()
        
        cursor.execute('''
            INSERT INTO update_logs (update_type, status, message)
            VALUES (%s, %s, %s)
        ''', ('silver', 'success', f'{added} silvers updated'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"  ✅ {added} gümüş eklendi")
        return True
        
    except Exception as e:
        logger.error(f"Error fetching silvers: {str(e)}")
        return False

def update_all():
    """Tüm verileri güncelle"""
    print(f"\n{'='*60}")
    print(f"🔄 FULL UPDATE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    haberleri_cek()
    fetch_currencies()
    fetch_golds()
    fetch_silvers()
    
    print(f"\n✅ Tüm veriler güncellendi!")
    print(f"{'='*60}\n")

# ─────────────────────────────────────────────
# 🌐 API ENDPOINTS - HABERSEL
# ─────────────────────────────────────────────

@app.route('/')
def home():
    return jsonify({
        'app': 'Nouvs + KuraBak Backend',
        'status': 'running',
        'version': '4.0 (Integrated)',
        'database': 'PostgreSQL',
        'services': ['News (Habersel)', 'Currency (KuraBak)'],
        'endpoints': {
            'news': {
                '/api/haberler': 'Tüm haberleri getir',
                '/api/haber/<id>': 'Tek haber detayı',
                '/api/kategori/<kategori>': 'Kategoriye göre haberler',
                '/api/cek-haberler': 'Manuel haber çekme'
            },
            'currency': {
                '/api/currency/all': 'Tüm dövizleri getir',
                '/api/currency/<code>': 'Tek döviz getir',
                '/api/currency/history/<code>': 'Döviz geçmişi',
                '/api/gold/all': 'Tüm altın fiyatlarını getir',
                '/api/gold/<name>': 'Tek altın formatı getir',
                '/api/gold/history/<name>': 'Altın geçmişi',
                '/api/silver/all': 'Tüm gümüş fiyatlarını getir',
                '/api/silver/history/<name>': 'Gümüş geçmişi'
            },
            'admin': {
                '/health': 'Sağlık kontrolü',
                '/api/update': 'Manuel tam güncelleme'
            }
        }
    })

@app.route('/api/haberler', methods=['GET'])
def get_haberler():
    """Tüm haberleri getir"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, baslik, aciklama, gorsel, kaynak, url, kategori, 
            to_char(tarih, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as tarih
            FROM haberler 
            WHERE kaynak = ANY(%s)
            ORDER BY tarih DESC 
            LIMIT %s
        ''', (ALLOWED_SOURCES, limit))
        
        haberler = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(haberler),
            'sources': ALLOWED_SOURCES,
            'haberler': haberler
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/haber/<int:haber_id>', methods=['GET'])
def get_haber_detay(haber_id):
    """Tek haber detayı"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, baslik, aciklama, gorsel, kaynak, url, kategori, 
            to_char(tarih, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as tarih
            FROM haberler 
            WHERE id = %s AND kaynak = ANY(%s)
        ''', (haber_id, ALLOWED_SOURCES))
        
        haber = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if haber:
            return jsonify({'success': True, 'haber': haber})
        else:
            return jsonify({'success': False, 'error': 'Haber bulunamadı'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kategori/<kategori>', methods=['GET'])
def get_kategori_haberleri(kategori):
    """Kategoriye göre haberler"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, baslik, aciklama, gorsel, kaynak, url, kategori, 
            to_char(tarih, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as tarih
            FROM haberler 
            WHERE kategori = %s AND kaynak = ANY(%s)
            ORDER BY tarih DESC 
            LIMIT %s
        ''', (kategori, ALLOWED_SOURCES, limit))
        
        haberler = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'kategori': kategori,
            'sources': ALLOWED_SOURCES,
            'count': len(haberler),
            'haberler': haberler
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cek-haberler', methods=['GET', 'POST'])
def cek_haberler_manual():
    """Manuel haber çekme"""
    result = haberleri_cek()
    
    return jsonify({
        'success': True,
        'message': f'{result} haber eklendi',
        'eklenen': result,
        'timestamp': datetime.now().isoformat()
    })

# ─────────────────────────────────────────────
# 💱 API ENDPOINTS - KURABAK
# ─────────────────────────────────────────────

@app.route('/api/currency/all', methods=['GET'])
def get_all_currencies():
    """Tüm dövizleri getir"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, name, rate, 
            to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at
            FROM currencies 
            ORDER BY code
        ''')
        
        currencies = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not currencies:
            return jsonify({
                'success': False,
                'message': 'No currency data available',
                'data': []
            }), 404
        
        return jsonify({
            'success': True,
            'count': len(currencies),
            'data': currencies
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/currency/<code>', methods=['GET'])
def get_currency(code):
    """Tek döviz getir"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, name, rate,
            to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at
            FROM currencies 
            WHERE code = %s
        ''', (code.upper(),))
        
        currency = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not currency:
            return jsonify({'success': False, 'message': f'Currency {code} not found'}), 404
        
        return jsonify({'success': True, 'data': currency}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/currency/history/<code>', methods=['GET'])
def get_currency_history(code):
    """Döviz geçmişi"""
    try:
        days = request.args.get('days', 7, type=int)
        since = datetime.utcnow() - timedelta(days=days)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, rate,
            to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
            FROM currency_history 
            WHERE code = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        ''', (code.upper(), since))
        
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not history:
            return jsonify({
                'success': False,
                'message': f'No history found for {code}',
                'data': []
            }), 404
        
        return jsonify({
            'success': True,
            'code': code.upper(),
            'count': len(history),
            'data': history
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/gold/all', methods=['GET'])
def get_all_golds():
    """Tüm altın fiyatlarını getir"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, buying, selling, rate,
            to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at
            FROM golds 
            ORDER BY name
        ''')
        
        golds = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not golds:
            return jsonify({
                'success': False,
                'message': 'No gold data available',
                'data': []
            }), 404
        
        return jsonify({
            'success': True,
            'count': len(golds),
            'data': golds
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/gold/<name>', methods=['GET'])
def get_gold(name):
    """Tek altın formatı getir"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, buying, selling, rate,
            to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at
            FROM golds 
            WHERE name = %s
        ''', (name,))
        
        gold = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not gold:
            return jsonify({'success': False, 'message': f'Gold {name} not found'}), 404
        
        return jsonify({'success': True, 'data': gold}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/gold/history/<name>', methods=['GET'])
def get_gold_history(name):
    """Altın geçmişi"""
    try:
        days = request.args.get('days', 7, type=int)
        since = datetime.utcnow() - timedelta(days=days)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, rate,
            to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
            FROM gold_history 
            WHERE name = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        ''', (name, since))
        
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not history:
            return jsonify({
                'success': False,
                'message': f'No history found for {name}',
                'data': []
            }), 404
        
        return jsonify({
            'success': True,
            'name': name,
            'count': len(history),
            'data': history
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/silver/all', methods=['GET'])
def get_all_silvers():
    """Tüm gümüş fiyatlarını getir"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, buying, selling, rate,
            to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at
            FROM silvers 
            ORDER BY name
        ''')
        
        silvers = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not silvers:
            return jsonify({
                'success': False,
                'message': 'No silver data available',
                'data': []
            }), 404
        
        return jsonify({
            'success': True,
            'count': len(silvers),
            'data': silvers
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/silver/history/<name>', methods=['GET'])
def get_silver_history(name):
    """Gümüş geçmişi"""
    try:
        days = request.args.get('days', 7, type=int)
        since = datetime.utcnow() - timedelta(days=days)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, rate,
            to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
            FROM silver_history 
            WHERE name = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        ''', (name, since))
        
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not history:
            return jsonify({
                'success': False,
                'message': f'No history found for {name}',
                'data': []
            }), 404
        
        return jsonify({
            'success': True,
            'name': name,
            'count': len(history),
            'data': history
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─────────────────────────────────────────────
# 🔧 ADMIN ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/health', methods=['GET', 'HEAD'])
def health():
    """Sağlık kontrolü"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Haberler
        cursor.execute(
            'SELECT COUNT(*) as count FROM haberler WHERE kaynak = ANY(%s)',
            (ALLOWED_SOURCES,)
        )
        haberler_count = cursor.fetchone()['count']
        
        # Dövizler
        cursor.execute('SELECT COUNT(*) as count FROM currencies')
        currency_count = cursor.fetchone()['count']
        
        # Altınlar
        cursor.execute('SELECT COUNT(*) as count FROM golds')
        gold_count = cursor.fetchone()['count']
        
        # Gümüşler
        cursor.execute('SELECT COUNT(*) as count FROM silvers')
        silver_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'app': 'Nouvs + KuraBak Backend v4.0',
            'database': 'PostgreSQL',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'haberler': haberler_count,
                'currencies': currency_count,
                'golds': gold_count,
                'silvers': silver_count
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/update', methods=['POST'])
def manual_update():
    """Manuel tam güncelleme"""
    try:
        update_all()
        
        return jsonify({
            'success': True,
            'message': 'Full update started',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─────────────────────────────────────────────
# 🚀 MAIN
# ─────────────────────────────────────────────

if __name__ == '__main__':
    # Veritabanını hazırla
    if init_db():
        # İlk güncelleme
        print("\n🚀 Backend başlatılıyor...")
        print(f"📦 Version: 4.0 (Integrated)")
        print(f"🎯 Services: Habersel + KuraBak")
        
        update_all()
        
        # Scheduler başlat
        try:
            scheduler = BackgroundScheduler()
            
            # Her 1 saatte bir haberler
            scheduler.add_job(
                func=haberleri_cek,
                trigger="interval",
                hours=1,
                id="haber_job"
            )
            
            # Her 1 saatte bir dövizler/altın/gümüş (60 dakika)
            scheduler.add_job(
                func=lambda: [fetch_currencies(), fetch_golds(), fetch_silvers()],
                trigger="interval",
                minutes=60,
                id="kurabak_job"
            )
            
            scheduler.start()
            print("✅ Scheduler başlatıldı")
            print("   - Haberler: Her 1 saatte")
            print("   - Döviz/Altın/Gümüş: Her 60 dakikada")
        except Exception as e:
            print(f"⚠️  Scheduler başlatılamadı: {e}")
        
        print("\n🌐 API hazır!")
        print("📊 Habersel: /api/haberler")
        print("💱 KuraBak: /api/currency/all, /api/gold/all, /api/silver/all")
        print("✅ Sağlık: /health")
        print("\n")
    else:
        print("❌ Veritabanı başlatılamadı!")
    
    # Flask'ı başlat
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
