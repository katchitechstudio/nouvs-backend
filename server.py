from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import time

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# ⚙️ AYARLAR
# ─────────────────────────────────────────────

# DÜZELTİLDİ: Yeni API anahtarı (7FmauU73yf156Wszw2fTGR:6PeLiyxAGyN8x31F7TO3xH) yedek olarak tanımlandı.
COLLECTAPI_TOKEN = os.environ.get('COLLECTAPI_TOKEN', '7FmauU73yf156Wszw2fTGR:6PeLiyxAGyN8x31F7TO3xH')
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
        
        # Hız için indexler
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

# Haberleri API'den çek (Sadece bir kategori, saatlik rotasyon)
def haberleri_cek():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Haberler çekiliyor...")
    
    # Saate göre kategori seç (sıralı rotasyon 0-23 saat)
    saat = datetime.now().hour
    kategori = KATEGORILER[saat % len(KATEGORILER)]
    
    print(f"  📂 Kategori: {kategori} (Saat: {saat})")
    
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
        
        # 🔥 KRİTİK TEŞHİS LOGLARI (YENİ EKLENEN KISIM)
        print(f"COLLECTAPI STATUS: {response.status_code}")
        # Hata mesajının tamamını görmek için yanıtın ilk 500 karakterini yazdırıyoruz
        print(f"COLLECTAPI RESPONSE: {response.text[:500]}") 
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                haberler = data.get('result', [])
                
                conn = get_db()
                cursor = conn.cursor()
                
                eklenen = 0
                for haber in haberler:
                    try:
                        # GÜNCEL KISIM: Tarih verisi CollectAPI'den çekiliyor.
                        cursor.execute('''
                            INSERT INTO haberler (baslik, aciklama, gorsel, kaynak, url, kategori, tarih)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            haber.get('name'),
                            haber.get('description'),
                            haber.get('image'),
                            haber.get('source'),
                            haber.get('url'),
                            kategori,
                            haber.get('date') 
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
                error_message = data.get('message', 'Bilinmeyen API hatası')
                print(f"  ❌ API başarısız: {error_message}")
                return 0
            
        elif response.status_code == 429:
            print(f"  ❌ HTTP Hatası: 429 TOO MANY REQUESTS. Rate limit aşıldı. (Yanıtın ilk 500 karakteri yukarıda)")
            time.sleep(60)
            return 0
        
        else:
            print(f"  ❌ HTTP Hatası: {response.status_code}. (Yanıtın ilk 500 karakteri yukarıda)")
            return 0
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Ağ/Bağlantı Hatası: {e}")
        return 0
    except Exception as e:
        print(f"  ❌ Beklenmedik Hata: {e}")
        return 0

# API Endpoints
@app.route('/')
def home():
    return jsonify({
        'app': 'NouvsApp Backend',
        'status': 'running',
        'version': '2.2 (Stabil)',
        'database': 'PostgreSQL',
        'description': 'Nouvelles (News) API Service',
        'endpoints': {
            '/api/haberler': 'Tüm haberleri getir',
            '/api/haber/<id>': 'Tek haber detayı',
            '/api/kategori/<kategori>': 'Kategoriye göre haberler',
            '/api/cek-haberler': 'Manuel haber çekme (UptimeRobot için)',
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

# 🔥 YENI: Manuel haber çekme endpoint'i (UptimeRobot için)
@app.route('/api/cek-haberler', methods=['GET', 'POST'])
def cek_haberler_manual():
    """Manuel haber çekme - UptimeRobot her saat bunu çekecek"""
    print(f"\n[MANUEL ÇEKİM] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = haberleri_cek()
    
    return jsonify({
        'success': True,
        'message': f'{result} haber eklendi',
        'eklenen': result,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET', 'HEAD'])
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
        # İlk haberleri çek (uygulama başladığında)
        haberleri_cek()
        
        # Scheduler başlat (backup olarak, ama Render'da her zaman çalışmaz)
        try:
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                func=haberleri_cek,
                trigger="interval",
                hours=1
            )
            scheduler.start()
            print("✅ Scheduler başlatıldı (backup)")
        except Exception as e:
            print(f"⚠️  Scheduler başlatılamadı: {e}")
            print("ℹ️  UptimeRobot /api/cek-haberler endpoint'ini kullanacak")
        
        print("\n🚀 NouvsApp Backend başlatıldı!")
        print("💾 Database: PostgreSQL")
        print("📊 Her 1 saatte haber çekiliyor...")
        print("🔄 Kategoriler sıralı rotasyon:")
        for i, kat in enumerate(KATEGORILER):
            print(f"    Saat {i} → {kat}")
        print("🌐 API hazır: /api/haberler")
        print("🎯 Manuel çekme: /api/cek-haberler")
        print("✅ UptimeRobot /api/cek-haberler endpoint'ini çekecek")
        print("\n")
    else:
        print("❌ Veritabanı başlatılamadı!")
    
    # Flask'ı başlat
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
