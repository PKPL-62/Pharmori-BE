import json
import logging
import requests
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser

from core.utils import validate_user_role

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Just log that authentication is being bypassed
        logging.info("Skipping JWT authentication, allowing all requests.")

        # Simulate user data for testing logging
        request.auth_data = {"user_id": "anonymous", "role": "guest"}

# class JWTAuthenticationMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         token = request.headers.get("Authorization")

#         if not token or not token.startswith("Bearer "):
#             request.user = AnonymousUser()  # Assign an anonymous user
#             return JsonResponse({"error": "Missing or invalid token"}, status=401)

#         jwt_token = token.split(" ")[1]  # Extract JWT token after "Bearer"
#         auth_service_url = "http://your-golang-auth-service/auth/validate"
#         response = requests.post(auth_service_url, json={"token": jwt_token})

#         if response.status_code != 200:
#             request.user = AnonymousUser()
#             return JsonResponse({"error": "Invalid or expired token"}, status=403)

#         # Attach user data
#         user_data = response.json()
#         request.auth_data = user_data  # Store validated user data
        
#         # Simulate a user object
#         class AuthenticatedUser:
#             is_authenticated = True
#             username = user_data.get("username", "UnknownUser")

#         request.user = AuthenticatedUser()  # Assign a custom user-like object

logger = logging.getLogger('django.request')

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Debugging: Log Authorization header
        auth_header = request.headers.get('Authorization')
        logger.info(f"Authorization Header: {auth_header}")

        user_data, _, _ = validate_user_role(request, allowed_roles=[])
        
        # Debugging: Log user_data
        logger.info(f"User Data: {user_data}")

        user = user_data.get("email") if user_data else None
        ip = self.get_client_ip(request)
        body = request.body.decode('utf-8') if request.body else "No Body"

        extra_info = {
            'remote_addr': ip or 'Unknown',
            'method': request.method,
            'path': request.get_full_path(),
        }

        logger.info(f"User: {user}, Body: {body}, Extra: {json.dumps(extra_info)}")

        return self.get_response(request)

    def get_client_ip(self, request):
        """Extract client IP address from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', 'Unknown')