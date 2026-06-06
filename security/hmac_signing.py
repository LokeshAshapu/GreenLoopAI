import hmac
import hashlib
import time
from django.conf import settings
from django.core.exceptions import PermissionDenied

def generate_signature(secret: str, timestamp: str, method: str, path: str, body: bytes) -> str:
    """
    Generates a SHA256 HMAC signature.
    Message format: timestamp + method + path + body
    """
    message = timestamp.encode('utf-8') + method.encode('utf-8') + path.encode('utf-8') + body
    h = hmac.new(secret.encode('utf-8'), message, hashlib.sha256)
    return h.hexdigest()

def verify_hmac_signature(request) -> bool:
    """
    Verifies that the incoming request has a valid HMAC signature.
    Expected headers:
    - X-Signature-Timestamp: Unix timestamp
    - X-Signature: HMAC SHA256 hex signature
    """
    signature = request.headers.get('X-Signature')
    timestamp_str = request.headers.get('X-Signature-Timestamp')
    
    if not signature or not timestamp_str:
        return False
        
    # Prevent replay attacks by checking timestamp window (e.g., 5 minutes / 300 seconds)
    try:
        request_time = int(timestamp_str)
        current_time = int(time.time())
        if abs(current_time - request_time) > 300:
            return False
    except ValueError:
        return False
        
    secret = getattr(settings, 'HMAC_SECRET_KEY', None)
    if not secret:
        return False
        
    # Read request body
    body = request.body
    
    expected_signature = generate_signature(
        secret=secret,
        timestamp=timestamp_str,
        method=request.method,
        path=request.path,
        body=body
    )
    
    return hmac.compare_digest(expected_signature, signature)
