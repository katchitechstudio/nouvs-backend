# NouvsApp Backend

🇫🇷 **Nouvelles** (haberler) + App = NouvsApp

Backend servisi - CollectAPI'den haberleri çeker ve saklar.

## Özellikler
- ⏰ Her 1 saatte otomatik haber çekme
- 📂 6 farklı kategori (rotasyonlu)
- 📅 7 günlük haber arşivi
- 🌐 REST API

## Kategoriler
- General (Genel)
- Sport (Spor)
- Economy (Ekonomi)
- Technology (Teknoloji)
- Health (Sağlık)
- Entertainment (Eğlence)

## Endpoints
- `GET /` - Ana sayfa
- `GET /api/haberler` - Tüm haberleri getir
- `GET /api/haber/{id}` - Tek haber detayı
- `GET /api/kategori/{kategori}` - Kategoriye göre haberler
- `GET /health` - Sağlık kontrolü

## Kullanım
Backend her saatte farklı bir kategoriden haber çeker (rotasyonlu).
Her kategori günde 4 kez güncellenir.

Günlük API kullanımı: 24 istek
Aylık API kullanımı: ~720 istek
```

### **Adım 3: Kaydet**
- **Ctrl+S**

✅ **README.md hazır!**

---

## 📄 DOSYA 4: `.gitignore`

### **Adım 1: Yeni dosya oluştur**
- Sol tarafta `NOUVS-BACKEND` klasörüne **sağ tık**
- **New File** tıkla
- ⚠️ **DİKKAT:** Dosya adı başında **nokta** var!
- Dosya adı: `.gitignore`
- **Enter**

### **Adım 2: İçeriği yapıştır**

Şunu **kopyala** ve dosyaya **yapıştır**:
```
__pycache__/
*.pyc
*.db
.env
venv/
.DS_Store
```

### **Adım 3: Kaydet**
- **Ctrl+S**

✅ **.gitignore hazır!**

---

## ✅ SON KONTROL!

Şimdi sol tarafta **4 dosya** görünüyor olmalı:
```
📁 nouvs-backend
  📄 .gitignore
  📄 README.md
  📄 requirements.txt
  📄 server.py