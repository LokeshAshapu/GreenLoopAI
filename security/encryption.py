import os
import base64
from django.conf import settings
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

_fernet_instance = None

def get_fernet():
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    # Fetch key from settings
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        # Check environment as backup
        key = os.environ.get('ENCRYPTION_KEY')
    
    if not key:
        raise ImproperlyConfigured("ENCRYPTION_KEY settings or env variable must be set.")
        
    try:
        # Fernet keys are 32 bytes base64 encoded url-safe
        _fernet_instance = Fernet(key.encode())
        return _fernet_instance
    except Exception as e:
        raise ImproperlyConfigured(f"Invalid ENCRYPTION_KEY for Fernet: {e}")

def encrypt_value(value: str) -> str:
    """
    Encrypts a string value using Fernet (AES-256 equivalent).
    Returns a url-safe base64 string.
    """
    if not value:
        return ""
    f = get_fernet()
    return f.encrypt(value.encode()).decode()

def decrypt_value(token: str) -> str:
    """
    Decrypts a Fernet encrypted string.
    """
    if not token:
        return ""
    f = get_fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except Exception:
        # In case of tampering or key issues, return a placeholder or raise
        return "[ENCRYPTION ERROR: CANNOT DECRYPT]"
