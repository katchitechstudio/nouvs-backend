from flask import Blueprint, jsonify, request
from datetime import datetime
from currency_models import get_db
from news_service import haberleri_cek
from config import Config

news_bp = Blueprint('news', __name__, url_prefix='/api')

@news_bp.route('/haberler', methods=['GET'])
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
        ''', (Config.ALLOWED_SOURCES, limit))
        
        haberler = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(haberler),
            'sources': Config.ALLOWED_SOURCES,
            'haberler': haberler
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@news_bp.route('/haber/<int:haber_id>', methods=['GET'])
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
        ''', (haber_id, Config.ALLOWED_SOURCES))
        
        haber = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if haber:
            return jsonify({'success': True, 'haber': haber})
        else:
            return jsonify({'success': False, 'error': 'Haber bulunamadı'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@news_bp.route('/kategori/<kategori>', methods=['GET'])
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
        ''', (kategori, Config.ALLOWED_SOURCES, limit))
        
        haberler = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'kategori': kategori,
            'sources': Config.ALLOWED_SOURCES,
            'count': len(haberler),
            'haberler': haberler
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@news_bp.route('/cek-haberler', methods=['GET', 'POST', 'HEAD'])
def cek_haberler_manual():
    """Manuel haber çekme"""
    result = haberleri_cek()
    
    return jsonify({
        'success': True,
        'message': f'{result} haber eklendi',
        'eklenen': result,
        'timestamp': datetime.now().isoformat()
    })