from flask import Blueprint, request, jsonify, current_app
import requests
from typing import Dict, Any
from datetime import datetime
from app.decorators import log_api_call, log_and_store_api_call

main_bp = Blueprint('main', __name__)

def validate_price_input(data: Dict[str, Any] | None) -> tuple[bool, str]:
    #Validate pricing calculation input
    if not data:
        return False, "Request body is required"
    
    if 'base_price' not in data:
        return False, "'base_price' field is required"
    
    if 'factor' not in data:
        return False, "'factor' field is required"
    
    try:
        base_price = float(data['base_price'])
        factor = float(data['factor'])
        
        if base_price < 0:
            return False, "'base_price' must be non-negative"
        
        if factor < 0:
            return False, "'factor' must be non-negative"
        
        if base_price > 1_000_000:
            return False, "'base_price' exceeds maximum allowed value"
            
    except (ValueError, TypeError):
        return False, "'base_price' and 'factor' must be valid numbers"
    
    return True, ""

@main_bp.route('/')
@log_api_call
def home():
    return jsonify({
        "message": "Core API Python (Mongo Edition) is running!",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/calculate_price", "method": "POST", "description": "Calculate price using Rust engine"}
        ]
    }), 200

@main_bp.route('/health')
@log_api_call
def health():
    return jsonify({"status": "healthy", "service": "core_api"}), 200

@main_bp.route('/calculate_price', methods=['POST'])
@log_and_store_api_call
def get_price():
    data = request.get_json(silent=True)
    is_valid, error_msg = validate_price_input(data)
    
    if not is_valid:
        return jsonify({"error": error_msg}), 400
    
    rust_url = f"{current_app.config['RUST_SERVICE_URL']}/calculate"
    
    try:
        # Call Rust microservice
        response = requests.post(
            rust_url, 
            json=data,
            timeout=5
        )
        response.raise_for_status()
        rust_result = response.json()

        # Save to MongoDB
        try:
            mongo_client = current_app.config.get('MONGO_CLIENT')
            if mongo_client:
                db = mongo_client.pyrust_db
                db.logs.insert_one({
                    "timestamp": datetime.utcnow(),
                    "input": data, 
                    "output": rust_result
                })
        except Exception as db_error:
            current_app.logger.warning(f"MongoDB logging failed: {str(db_error)}")
        
        return jsonify({
            "success": True,
            "api_source": "Python Flask Layer",
            "db_type": "MongoDB",
            "rust_computation": rust_result
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Rust service timeout"
        }), 504
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "Cannot connect to pricing engine"
        }), 503
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Rust service error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal service error"
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        }), 500
