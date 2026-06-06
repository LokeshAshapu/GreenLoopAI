from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
import time

from security.encryption import encrypt_value, decrypt_value
from security.hmac_signing import generate_signature, verify_hmac_signature
from users.models import User, Profile, AuditLog

class SecurityTestCase(TestCase):
    
    def setUp(self):
        self.User = get_user_model()
        cache.clear()
        
    def test_argon2_password_hashing(self):
        """
        Verify that password hashing uses the Argon2 hasher configuration.
        """
        user = self.User.objects.create_user(
            username="testsecurityuser",
            password="SecurePassword123!"
        )
        # Check that the password starts with the argon2 identifier
        self.assertTrue(user.password.startswith('argon2'))
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertFalse(user.check_password("WrongPassword"))

    def test_fernet_aes_encryption(self):
        """
        Verify field level encryption helper correctly encrypts and decrypts content.
        """
        secret_message = "Confidential Address 123, Green City"
        encrypted = encrypt_value(secret_message)
        
        # Verify it is encrypted (not plaintext)
        self.assertNotEqual(secret_message, encrypted)
        
        # Verify it can be decrypted back
        decrypted = decrypt_value(encrypted)
        self.assertEqual(secret_message, decrypted)
        
    def test_profile_field_encryption_wrapper(self):
        """
        Verify Profile phone & address setter/getter handles encryption automatically.
        """
        user = self.User.objects.create_user(
            username="encryptprofileuser",
            password="SecurePassword123!"
        )
        profile = Profile.objects.create(user=user)
        
        phone_number = "+1 (555) 019-9231"
        address_text = "456 Solar Avenue"
        
        profile.phone = phone_number
        profile.address = address_text
        profile.save()
        
        # Reload profile from database
        reloaded = Profile.objects.get(id=profile.id)
        
        # Properties should return plaintext
        self.assertEqual(reloaded.phone, phone_number)
        self.assertEqual(reloaded.address, address_text)
        
        # DB fields must store encrypted string
        self.assertNotEqual(reloaded._phone_encrypted, phone_number)
        self.assertNotEqual(reloaded._address_encrypted, address_text)
        self.assertTrue(len(reloaded._phone_encrypted) > 40) # Encrypted string length check

    def test_hmac_request_verification(self):
        """
        Verify that signature validation correctly verifies or rejects request payloads.
        """
        # Create a mock Django request-like object
        class MockRequest:
            def __init__(self, headers, body, method="POST", path="/api/secure/data/"):
                self.headers = headers
                self.body = body
                self.method = method
                self.path = path
                
        secret = settings.HMAC_SECRET_KEY
        timestamp = str(int(time.time()))
        body = b'{"report_id": 42, "category": "toxic_waste"}'
        
        valid_sig = generate_signature(
            secret=secret,
            timestamp=timestamp,
            method="POST",
            path="/api/secure/data/",
            body=body
        )
        
        # Check valid request
        req_ok = MockRequest(
            headers={'X-Signature': valid_sig, 'X-Signature-Timestamp': timestamp},
            body=body
        )
        self.assertTrue(verify_hmac_signature(req_ok))
        
        # Check expired timestamp check (replay attack prevention)
        expired_timestamp = str(int(time.time()) - 400) # Older than 5 minutes window
        old_sig = generate_signature(
            secret=secret,
            timestamp=expired_timestamp,
            method="POST",
            path="/api/secure/data/",
            body=body
        )
        req_expired = MockRequest(
            headers={'X-Signature': old_sig, 'X-Signature-Timestamp': expired_timestamp},
            body=body
        )
        self.assertFalse(verify_hmac_signature(req_expired))
        
        # Check invalid body modification signature rejection
        req_modified = MockRequest(
            headers={'X-Signature': valid_sig, 'X-Signature-Timestamp': timestamp},
            body=b'{"report_id": 42, "category": "fake_data"}' # Tampered body
        )
        self.assertFalse(verify_hmac_signature(req_modified))

    def test_rate_limit_middleware(self):
        """
        Verify simple rate limiting blocks requests after matching limit.
        """
        c = Client()
        # Set settings for test
        settings.DISABLE_RATE_LIMITING = False
        settings.RATE_LIMIT_MAX_REQUESTS = 3
        settings.RATE_LIMIT_WINDOW_SECONDS = 5
        
        # First 3 requests to landing page should return 200
        for _ in range(3):
            response = c.get('/')
            self.assertEqual(response.status_code, 200)
            
        # 4th request must be rate-limited (status 429)
        response = c.get('/')
        self.assertEqual(response.status_code, 429)
