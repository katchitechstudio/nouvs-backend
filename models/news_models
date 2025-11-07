# models/news_models.py

def init_news_tables(cursor):
    """Habersel tablosunu oluşturur."""
    # TIMESTAMPTZ: Saat dilimi bilgisi içeren zaman damgası (önerilen)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS haberler (
            id SERIAL PRIMARY KEY,
            baslik TEXT UNIQUE NOT NULL,
            aciklama TEXT,
            gorsel TEXT,
            kaynak TEXT,
            url TEXT,
            kategori TEXT,
            tarih TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Indexler
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tarih ON haberler(tarih DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kategori ON haberler(kategori)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kaynak ON haberler(kaynak)')
