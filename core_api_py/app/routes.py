from flask import Blueprint, request, jsonify, current_app
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from app.decorators import log_api_call, log_and_store_api_call
from app.models import PricingLog

main_bp = Blueprint('main', __name__)

RUST_TIMEOUT_SECONDS = 5
MAX_BASE_PRICE = 1_000_000


class ValidationError(Exception):
    pass

def validate_price_input(data: Optional[Dict[str, Any]]) -> None:
    if not data:
        raise ValidationError("Request body is required")
    
    # Check required fields
    required_fields = ['base_price', 'factor']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate and convert types
    try:
        base_price = float(data['base_price'])
        factor = float(data['factor'])
    except (ValueError, TypeError) as e:
        raise ValidationError("'base_price' and 'factor' must be valid numbers") from e
    
    # Validate ranges
    if base_price < 0:
        raise ValidationError("'base_price' must be non-negative")
    
    if factor < 0:
        raise ValidationError("'factor' must be non-negative")
    
    if base_price > MAX_BASE_PRICE:
        raise ValidationError(f"'base_price' exceeds maximum allowed value ({MAX_BASE_PRICE})")


def call_rust_service(data: Dict[str, Any]) -> Dict[str, Any]:
    rust_url = f"{current_app.config['RUST_SERVICE_URL']}/calculate"
    
    response = requests.post(
        rust_url,
        json=data,
        timeout=RUST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()


def save_to_mongodb(input_data: Dict[str, Any], result_data: Dict[str, Any]) -> None:
    try:
        mongo_client = current_app.config.get('MONGO_CLIENT')
        if not mongo_client:
            return
            
        db = mongo_client.pyrust_db
        pricing_log = PricingLog(input_data=input_data, result_data=result_data)
        db.logs.insert_one(pricing_log.to_dict())
    except Exception as db_error:
        current_app.logger.warning(f"MongoDB logging failed: {db_error}")

@main_bp.route('/')
@log_api_call
def home():
    #Service information endpoint
    return jsonify({
        "message": "Core API Python (Mongo Edition) is running!",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/calculate_price", "method": "POST", "description": "Calculate price using Rust engine"}
        ]
    }), 200


# @main_bp.route('/health')
# @log_api_call
# def health():
#     return jsonify({"status": "healthy", "service": "core_api"}), 200


@main_bp.route('/calculate_price', methods=['POST'])
@log_and_store_api_call
def calculate_price():
    data = request.get_json(silent=True)

    try:
        validate_price_input(data)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    
    if data is None:
        return jsonify({"error": "Invalid request"}), 400
    
    # Call Rust service
    try:
        rust_result = call_rust_service(data)
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
        current_app.logger.error(f"Rust service error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal service error"
        }), 500
    
    save_to_mongodb(input_data=data, result_data=rust_result)
    
    return jsonify({
        "success": True,
        "api_source": "Python Flask Layer",
        "db_type": "MongoDB",
        "rust_computation": rust_result
    }), 200
