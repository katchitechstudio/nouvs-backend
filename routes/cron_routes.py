from flask import Blueprint, jsonify
from hizmetler.news_service import haberleri_cek

cron_bp = Blueprint("cron_bp", __name__)

@cron_bp.route("/cron/haber-guncelle", methods=["POST"])
def haber_guncelle():
    eklenen = haberleri_cek()
    return jsonify({
        "status": "ok",
        "eklenen": eklenen
    })
