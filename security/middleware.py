import time
import logging
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from security.hmac_signing import verify_hmac_signature

logger = logging.getLogger('greenloop.security')

def get_client_ip(request):
    """
    Safely retrieves the user client IP behind reverse proxies (Nginx, Docker, Cloudflare).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class HMACSignatureMiddleware(MiddlewareMixin):
    """
    Middleware that enforces HMAC signature verification on paths starting with /api/secure/
    """
    def process_request(self, request):
        if request.path.startswith('/api/secure/'):
            if not verify_hmac_signature(request):
                logger.warning(
                    f"HMAC validation failed: {request.method} {request.path} from {get_client_ip(request)}"
                )
                return JsonResponse(
                    {"error": "Unauthorized: Invalid or missing request signature"}, 
                    status=401
                )
        return None


class SimpleRateLimitMiddleware(MiddlewareMixin):
    """
    Custom lightweight rate limiting middleware using Django cache.
    Enforces a request rate limit per IP.
    """
    def process_request(self, request):
        # Allow disabling rate limiting in settings
        if getattr(settings, 'DISABLE_RATE_LIMITING', False):
            return None
            
        ip = get_client_ip(request)
        # Skip rate limit for local/admin users if desired, or keep it universal
        # Limit: 100 requests per minute by default
        limit = getattr(settings, 'RATE_LIMIT_MAX_REQUESTS', 100)
        window = getattr(settings, 'RATE_LIMIT_WINDOW_SECONDS', 60)
        
        cache_key = f"rl:{ip}"
        requests_data = cache.get(cache_key, [])
        
        current_time = time.time()
        # Keep only requests within the window
        requests_data = [t for t in requests_data if current_time - t < window]
        
        if len(requests_data) >= limit:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return JsonResponse(
                {"error": "Too many requests. Please try again later."}, 
                status=429
            )
            
        requests_data.append(current_time)
        cache.set(cache_key, requests_data, window)
        return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware that records audit logs for modifying requests (POST, PUT, DELETE, PATCH).
    """
    def process_response(self, request, response):
        # Only log write operations, exclude safe operations
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            user = getattr(request, 'user', None)
            user_str = str(user) if user and user.is_authenticated else "Anonymous"
            ip = get_client_ip(request)
            status_code = response.status_code
            path = request.path
            
            log_msg = f"User: {user_str} | IP: {ip} | Action: {request.method} {path} | Status: {status_code}"
            
            # Print to standard logs
            if status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)
                
            # If we want to record to database, we can do it asynchronously or conditionally
            # to avoid loading DB overhead on every single action. We will import the model
            # inside to prevent circular import issues.
            try:
                if status_code < 400 or status_code in [401, 403]:
                    # To prevent circular imports:
                    from django.apps import apps
                    if apps.is_installed('users'):
                        AuditLog = apps.get_model('users', 'AuditLog')
                        AuditLog.objects.create(
                            user=user if user and user.is_authenticated else None,
                            action=f"{request.method} {path}",
                            ip_address=ip,
                            status=status_code,
                            description=f"Parameters: {list(request.POST.keys())}"
                        )
            except Exception as e:
                # Silently catch database write errors during migration/setup
                pass

        return response
