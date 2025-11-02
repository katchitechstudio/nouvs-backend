from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# ⚙️ AYARLAR - API TOKEN
# ─────────────────────────────────────────────

COLLECTAPI_TOKEN = os.environ.get('COLLECTAPI_TOKEN', '6QjqaX2e4cRQVH16F3SZZP:1uNWjCyfHX7OZC5OHzbviV')

# ─────────────────────────────────────────────

# SQLite veritabanı
def get_db():
    conn = sqlite3.connect('haberler.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Veritabanı tablosu oluştur
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS haberler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT UNIQUE,
            aciklama TEXT,
            gorsel TEXT,
            kaynak TEXT,
            url TEXT,
            kategori TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)')
    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır!")

# Kategoriler
KATEGORILER = ["general", "sport", "economy", "technology", "health", "entertainment"]

# Haberleri API'den çek
def haberleri_cek():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Haberler çekiliyor...")
    
    # Saate göre kategori seç (rotasyon)
    saat = datetime.now().hour
    kategori = KATEGORILER[saat % len(KATEGORILER)]
    
    print(f"  📂 Kategori: {kategori}")
    
    try:
        # CollectAPI'den çek
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
                        cursor.execute('''
                            INSERT INTO haberler (baslik, aciklama, gorsel, kaynak, url, kategori)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            haber.get('name'),
                            haber.get('description'),
                            haber.get('image'),
                            haber.get('source'),
                            haber.get('url'),
                            kategori
                        ))
                        eklenen += 1
                    except sqlite3.IntegrityError:
                        pass  # Haber zaten var
                
                conn.commit()
                
                # Eski haberleri sil (7 günden eski)
                silme_tarihi = datetime.now() - timedelta(days=7)
                cursor.execute('DELETE FROM haberler WHERE tarih < ?', (silme_tarihi,))
                silinen = cursor.rowcount
                conn.commit()
                
                cursor.close()
                conn.close()
                
                print(f"  ✅ {eklenen} yeni haber eklendi")
                print(f"  🗑️  {silinen} eski haber silindi")
            else:
                print(f"  ❌ API hatası: {data.get('message')}")
        else:
            print(f"  ❌ HTTP Hatası: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Hata: {e}")

# API Endpoints
@app.route('/')
def home():
    return jsonify({
        'app': 'NouvsApp Backend',
        'status': 'running',
        'version': '1.0',
        'description': 'Nouvelles (News) API Service',
        'endpoints': {
            '/api/haberler': 'Tüm haberleri getir',
            '/api/haber/<id>': 'Tek haber detayı',
            '/api/kategori/<kategori>': 'Kategoriye göre haberler',
            '/health': 'Sağlık kontrolü'
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
            SELECT id, baslik, aciklama, gorsel, kaynak, url, kategori, tarih
            FROM haberler 
            ORDER BY tarih DESC 
            LIMIT ?
        ''', (limit,))
        
        haberler = []
        for row in cursor.fetchall():
            haberler.append({
                'id': row['id'],
                'baslik': row['baslik'],
                'aciklama': row['aciklama'],
                'gorsel': row['gorsel'],
                'kaynak': row['kaynak'],
                'url': row['url'],
                'kategori': row['kategori'],
                'tarih': row['tarih']
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(haberler),
            'haberler': haberler
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/haber/<int:haber_id>', methods=['GET'])
def get_haber_detay(haber_id):
    """Tek haber detayı"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, baslik, aciklama, gorsel, kaynak, url, kategori, tarih
            FROM haberler 
            WHERE id = ?
        ''', (haber_id,))
        
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if row:
            haber = {
                'id': row['id'],
                'baslik': row['baslik'],
                'aciklama': row['aciklama'],
                'gorsel': row['gorsel'],
                'kaynak': row['kaynak'],
                'url': row['url'],
                'kategori': row['kategori'],
                'tarih': row['tarih']
            }
            return jsonify({
                'success': True,
                'haber': haber
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Haber bulunamadı'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/kategori/<kategori>', methods=['GET'])
def get_kategori_haberleri(kategori):
    """Kategoriye göre haberler"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, baslik, aciklama, gorsel, kaynak, url, kategori, tarih
            FROM haberler 
            WHERE kategori = ?
            ORDER BY tarih DESC 
            LIMIT ?
        ''', (kategori, limit))
        
        haberler = []
        for row in cursor.fetchall():
            haberler.append({
                'id': row['id'],
                'baslik': row['baslik'],
                'aciklama': row['aciklama'],
                'gorsel': row['gorsel'],
                'kaynak': row['kaynak'],
                'url': row['url'],
                'kategori': row['kategori'],
                'tarih': row['tarih']
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'kategori': kategori,
            'count': len(haberler),
            'haberler': haberler
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Sağlık kontrolü"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM haberler')
    count = cursor.fetchone()[0]
    
    # Kategori bazlı sayım
    cursor.execute('SELECT kategori, COUNT(*) FROM haberler GROUP BY kategori')
    kategoriler = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'status': 'healthy',
        'app': 'NouvsApp Backend',
        'timestamp': datetime.now().isoformat(),
        'toplam_haber': count,
        'kategoriler': kategoriler
    })

if __name__ == '__main__':
    # Veritabanını hazırla
    init_db()
    
    # İlk haberleri çek
    haberleri_cek()
    
    # Scheduler başlat (her 1 saatte)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=haberleri_cek,
        trigger="interval",
        hours=1
    )
    scheduler.start()
    
    print("\n🚀 NouvsApp Backend başlatıldı!")
    print("📊 Her 1 saatte haber çekiliyor...")
    print("🔄 Kategoriler otomatik rotasyon: ", KATEGORILER)
    print("🌐 API hazır: /api/haberler\n")
    
    # Flask'ı başlat
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)