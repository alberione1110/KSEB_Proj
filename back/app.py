from flask import Flask
from flask_cors import CORS

# 라우터 불러오기
from routes.recommendIndustry import bp as recommend_industry_bp
from routes.recommendArea import bp as recommend_area_bp
from routes.report import bp as report_bp  # 🔥 NEW

def create_app():
    app = Flask(__name__)
    CORS(app)  # 모든 프론트 요청 허용 (로컬 개발 편의용)

    # 라우터 등록
    app.register_blueprint(recommend_industry_bp, url_prefix='/api')
    app.register_blueprint(recommend_area_bp, url_prefix='/api')
    app.register_blueprint(report_bp, url_prefix='/api')  # 🔥 NEW

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
