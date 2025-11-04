from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# ⚙️ AYARLAR
# ─────────────────────────────────────────────

COLLECTAPI_TOKEN = os.environ.get('COLLECTAPI_TOKEN', '6QjqaX2e4cRQVH16F3SZZP:1uNWjCyfHX7OZC5OHzbviV')
DATABASE_URL = os.environ.get('DATABASE_URL')

# PostgreSQL bağlantısı
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# Veritabanı tablosu oluştur
def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ PostgreSQL veritabanı hazır!")
        return True
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        return False

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
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            haber.get('name'),
                            haber.get('description'),
                            haber.get('image'),
                            haber.get('source'),
                            haber.get('url'),
                            kategori
                        ))
                        eklenen += 1
                    except psycopg2.IntegrityError:
                        conn.rollback()
                        pass  # Haber zaten var
                
                conn.commit()
                
                # Eski haberleri sil (7 günden eski)
                silme_tarihi = datetime.now() - timedelta(days=7)
                cursor.execute('DELETE FROM haberler WHERE tarih < %s', (silme_tarihi,))
                silinen = cursor.rowcount
                conn.commit()
                
                cursor.close()
                conn.close()
                
                print(f"  ✅ {eklenen} yeni haber eklendi")
                print(f"  🗑️  {silinen} eski haber silindi")
                return eklenen
            else:
                print(f"  ❌ API hatası: {data.get('message')}")
                return 0
        else:
            print(f"  ❌ HTTP Hatası: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"  ❌ Hata: {e}")
        return 0

# API Endpoints
@app.route('/')
def home():
    return jsonify({
        'app': 'NouvsApp Backend',
        'status': 'running',
        'version': '2.0',
        'database': 'PostgreSQL',
        'description': 'Nouvelles (News) API Service',
        'endpoints': {
            '/api/haberler': 'Tüm haberleri getir',
            '/api/haber/<id>': 'Tek haber detayı',
            '/api/kategori/<kategori>': 'Kategoriye göre haberler',
            '/api/cek-haberler': 'Manuel haber çekme (tüm kategoriler)',
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
            LIMIT %s
        ''', (limit,))
        
        haberler = cursor.fetchall()
        
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
            WHERE id = %s
        ''', (haber_id,))
        
        haber = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if haber:
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
            WHERE kategori = %s
            ORDER BY tarih DESC 
            LIMIT %s
        ''', (kategori, limit))
        
        haberler = cursor.fetchall()
        
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

@app.route('/api/cek-haberler', methods=['GET'])
def cek_haberler_manuel():
    """
    🔥 MANUEL HABER ÇEKME - TÜM KATEGORİLER
    Test ve ilk kurulum için kullanılır
    """
    try:
        print("\n" + "="*50)
        print("🚀 MANUEL HABER ÇEKME BAŞLATILDI")
        print("="*50)
        
        toplam_eklenen = 0
        sonuclar = {}
        
        # Tüm kategorilerden haber çek
        for kategori in KATEGORILER:
            print(f"\n📂 Kategori: {kategori}")
            
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
                                cursor.execute('''
                                    INSERT INTO haberler (baslik, aciklama, gorsel, kaynak, url, kategori)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                ''', (
                                    haber.get('name'),
                                    haber.get('description'),
                                    haber.get('image'),
                                    haber.get('source'),
                                    haber.get('url'),
                                    kategori
                                ))
                                eklenen += 1
                            except psycopg2.IntegrityError:
                                conn.rollback()
                                pass  # Haber zaten var
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        toplam_eklenen += eklenen
                        sonuclar[kategori] = {
                            'success': True,
                            'eklenen': eklenen,
                            'toplam': len(haberler)
                        }
                        print(f"  ✅ {eklenen}/{len(haberler)} haber eklendi")
                    else:
                        sonuclar[kategori] = {
                            'success': False,
                            'error': data.get('message', 'Bilinmeyen hata')
                        }
                        print(f"  ❌ API hatası")
                else:
                    sonuclar[kategori] = {
                        'success': False,
                        'error': f'HTTP {response.status_code}'
                    }
                    print(f"  ❌ HTTP Hatası: {response.status_code}")
                    
            except Exception as e:
                sonuclar[kategori] = {
                    'success': False,
                    'error': str(e)
                }
                print(f"  ❌ Hata: {e}")
        
        print("\n" + "="*50)
        print(f"🎉 TAMAMLANDI: {toplam_eklenen} HABER EKLENDİ")
        print("="*50 + "\n")
        
        return jsonify({
            'success': True,
            'message': f'Toplam {toplam_eklenen} haber eklendi',
            'toplam_eklenen': toplam_eklenen,
            'kategori_sayisi': len(KATEGORILER),
            'detaylar': sonuclar
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Sağlık kontrolü"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM haberler')
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        # Kategori bazlı sayım
        cursor.execute('SELECT kategori, COUNT(*) as count FROM haberler GROUP BY kategori')
        rows = cursor.fetchall()
        kategoriler = {row['kategori']: row['count'] for row in rows}
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'app': 'NouvsApp Backend',
            'database': 'PostgreSQL',
            'timestamp': datetime.now().isoformat(),
            'toplam_haber': count,
            'kategoriler': kategoriler
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Veritabanını hazırla
    if init_db():
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
        print("💾 Database: PostgreSQL")
        print("📊 Her 1 saatte haber çekiliyor...")
        print("🔄 Kategoriler otomatik rotasyon: ", KATEGORILER)
        print("🌐 API hazır: /api/haberler")
        print("🔥 Manuel çekme: /api/cek-haberler\n")
    else:
        print("❌ Veritabanı başlatılamadı!")
    
    # Flask'ı başlat
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
