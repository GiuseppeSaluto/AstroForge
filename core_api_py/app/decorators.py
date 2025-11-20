import logging
import time
from functools import wraps
from flask import request, current_app
from datetime import datetime

logger = logging.getLogger(__name__)

def log_api_call(f):  
    # Decorator to log API calls with request/response details Tracks: method, path, params, execution time, status code
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        logger.info(f"🔵 API Call START: {request.method} {request.path}")
        
        try:
            if request.method == 'GET':
                params = dict(request.args)
                if params:
                    logger.info(f"📥 Query params: {params}")
            elif request.method == 'POST':
                if request.is_json:
                    payload = request.get_json(silent=True)
                    if payload:
                        logger.info(f"📦 JSON payload: {payload}")
        except Exception as e:
            logger.warning(f"⚠️ Could not log parameters: {e}")
        
        try:
            response = f(*args, **kwargs)
            
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            else:
                status_code = 200
            
            execution_time = (time.time() - start_time) * 1000
            
            status_emoji = "✅" if status_code < 400 else "❌"
            logger.info(
                f"{status_emoji} API Call END: {request.method} {request.path} "
                f"| Status: {status_code} | Time: {execution_time:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(
                f"❌ API Call FAILED: {request.method} {request.path} "
                f"| Error: {str(e)} | Time: {execution_time:.2f}ms"
            )
            raise
    
    return wrapper


def log_and_store_api_call(f):
    """
    Extended decorator that also stores API calls in MongoDB
    Use this for endpoints you want to track in the database
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Collect request data
        request_data = {
            "method": request.method,
            "path": request.path,
            "timestamp": datetime.utcnow(),
            "params": dict(request.args) if request.method == 'GET' else None,
            "payload": request.get_json(silent=True) if request.is_json else None,
            "remote_addr": request.remote_addr
        }
        
        logger.info(f"🔵 API Call: {request.method} {request.path}")
        
        try:
            response = f(*args, **kwargs)
            
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            else:
                status_code = 200
            
            execution_time = (time.time() - start_time) * 1000
            
            try:
                mongo_client = current_app.config.get('MONGO_CLIENT')
                if mongo_client:
                    db = mongo_client.pyrust_db
                    db.api_calls.insert_one({
                        **request_data,
                        "status_code": status_code,
                        "execution_time_ms": round(execution_time, 2),
                        "success": status_code < 400
                    })
            except Exception as db_error:
                logger.warning(f"Failed to store API call in MongoDB: {db_error}")
            
            status_emoji = "✅" if status_code < 400 else "❌"
            logger.info(
                f"{status_emoji} {request.method} {request.path} "
                f"| {status_code} | {execution_time:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ {request.method} {request.path} | Error: {str(e)} | {execution_time:.2f}ms")
            raise
    
    return wrapper
