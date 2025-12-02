from flask import Flask
from app.routes.nasa import nasa_bp  
from app.routes.analysis import analysis_bp 

def create_app():
    app = Flask(__name__)
    
    app.register_blueprint(nasa_bp)
    app.register_blueprint(analysis_bp)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)