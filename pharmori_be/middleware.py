import logging
import requests
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser

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
        print("Middleware executed")  # Debug print

        user = request.user if request.user.is_authenticated else "Anonymous"
        ip = self.get_client_ip(request)
        
        # Read request body safely
        body = request.body.decode('utf-8') if request.body else "No Body"

        extra_info = {
            'remote_addr': ip,
            'method': request.method,
            'path': request.get_full_path(),
        }

        logger.info(f"User: {user}, Body: {body}", extra=extra_info)

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]  # Get the first IP in the list
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip