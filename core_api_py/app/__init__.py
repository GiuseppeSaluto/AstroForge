from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
import logging

def create_app():
    app = Flask(__name__)
    
    from config import Config
    app.config.from_object(Config)
    
    CORS(app, resources={
        r"/*": {
            "origins": ["*"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "max_age": 3600
        }
    })
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.config['MONGO_CLIENT'] = MongoClient(app.config['MONGO_URI'])
    app.logger.info(f"MongoDB connected to: {app.config['MONGO_URI']}")


    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    return app
