# back/app.py
from flask import Flask
from flask_cors import CORS

from routes.recommendIndustry import bp as recommend_industry_bp
from routes.recommendArea import bp as recommend_area_bp
from routes.report import bp as report_bp
from routes.chat import bp as chat_bp  # ✅ NEW

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(recommend_industry_bp, url_prefix="/api")
    app.register_blueprint(recommend_area_bp, url_prefix="/api")
    app.register_blueprint(report_bp, url_prefix="/api")
    app.register_blueprint(chat_bp, url_prefix="/api")  # ✅ NEW

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
