from flask import Blueprint, jsonify, request
from models.db import get_db, put_db
from datetime import datetime, timedelta

currency_bp = Blueprint('currency', __name__, url_prefix='/api/currency')


def _get_data(table_name, name_col, name_value=None):
    """Veritabanından döviz/altın/gümüş verilerini çeker"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        if table_name in ['golds', 'silvers']:
            select_cols = 'name, buying, selling, rate,'
            name_alias = 'name'
        else:
            select_cols = 'code, name, rate,'
            name_alias = 'code'

        query = f'''
            SELECT {select_cols}
            to_char(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at
            FROM {table_name}
        '''

        params = []
        if name_value:
            query += f" WHERE {name_col} = %s"
            params.append(name_value.upper() if name_col == 'code' else name_value)

        query += f" ORDER BY {name_alias}"

        cursor.execute(query, params)
        data = cursor.fetchall()

        cursor.close()
        put_db(conn)

        if name_value and not data:
            return jsonify({'success': False, 'message': f'{name_value} bulunamadı'}), 404

        return jsonify({
            'success': True,
            'count': len(data),
            'data': data[0] if name_value else data
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def _get_history(table_name, name_col, name_value):
    """Geçmiş verilerini çeker"""
    try:
        days = request.args.get('days', 7, type=int)
        since = datetime.utcnow() - timedelta(days=days)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(f'''
            SELECT {name_col} as name_code, rate,
            to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
            FROM {table_name}_history 
            WHERE {name_col} = %s AND timestamp >= %s
            ORDER BY timestamp ASC
        ''', (name_value.upper() if name_col == 'code' else name_value, since))

        history = cursor.fetchall()
        cursor.close()
        put_db(conn)

        if not history:
            return jsonify({
                'success': False,
                'message': f'No history found for {name_value}',
                'data': []
            }), 404

        return jsonify({
            'success': True,
            'name_code': name_value,
            'count': len(history),
            'data': history
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@currency_bp.route('/all', methods=['GET'])
def get_all_currencies():
    return _get_data('currencies', 'code')

@currency_bp.route('/<code>', methods=['GET'])
def get_currency(code):
    return _get_data('currencies', 'code', code)

@currency_bp.route('/history/<code>', methods=['GET'])
def get_currency_history(code):
    return _get_history('currency', 'code', code)


@currency_bp.route('/gold/all', methods=['GET'])
def get_all_golds():
    return _get_data('golds', 'name')

@currency_bp.route('/gold/<name>', methods=['GET'])
def get_gold(name):
    return _get_data('golds', 'name', name)

@currency_bp.route('/gold/history/<name>', methods=['GET'])
def get_gold_history(name):
    return _get_history('gold', 'name', name)


@currency_bp.route('/silver/all', methods=['GET'])
def get_all_silvers():
    return _get_data('silvers', 'name')

@currency_bp.route('/silver/<name>', methods=['GET'])
def get_silver(name):
    return _get_data('silvers', 'name', name)

@currency_bp.route('/silver/history/<name>', methods=['GET'])
def get_silver_history(name):
    return _get_history('silver', 'name', name)
