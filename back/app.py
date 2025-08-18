# back/app.py
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- Blueprints ---
from routes.recommendIndustry import bp as recommend_industry_bp
from routes.recommendArea import bp as recommend_area_bp
from routes.report import bp as report_bp
from routes.chat import bp as chat_bp


def create_app():
    app = Flask(__name__)

    # Flask JSON 설정 (한글 깨짐 방지 / 키 정렬 비활성)
    app.config["JSON_AS_ASCII"] = False
    app.config["JSON_SORT_KEYS"] = False

    # CORS 설정 (환경변수 ALLOWED_ORIGINS="https://a.com,https://b.com" 형태 지원)
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
    if allowed_origins == "*":
        CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    else:
        origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
        CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)

    # 블루프린트 등록
    app.register_blueprint(recommend_industry_bp, url_prefix="/api")
    app.register_blueprint(recommend_area_bp, url_prefix="/api")
    app.register_blueprint(report_bp, url_prefix="/api")
    app.register_blueprint(chat_bp, url_prefix="/api")

    # 루트 & 헬스체크
    @app.get("/")
    def root():
        return jsonify(app="KSEB_Proj API", status="ok"), 200

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    # 사전 플라이트(OPTIONS) 로깅/허용 (flask-cors가 처리하지만, 디버그용으로 상태만 반환)
    @app.route("/api/<path:_sub>", methods=["OPTIONS"])
    def cors_preflight(_sub):
        return ("", 204)

    # 공통 에러 핸들러
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not Found", path=request.path), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error="Bad Request", detail=str(e)), 400

    @app.errorhandler(500)
    def server_error(e):
        detail = str(e) if os.getenv("FLASK_DEBUG", "1") == "1" else "Internal Server Error"
        return jsonify(error="Internal Server Error", detail=detail), 500

    return app


if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    port = int(os.getenv("PORT", "5001"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=False,
        threaded=True,
    )
