import requests
from django.http import JsonResponse
from pharmori_be import settings
import logging

logger = logging.getLogger('django.request')

AUTH_VALIDATION_URL = f"{settings.AUTH_SERVICE_URL}/api/auth/validate"

def validate_user_role(request, allowed_roles):
    """
    Validate user authorization and return user role.

    Parameters:
        request: Django HTTP request object.
        allowed_roles: List of allowed roles.

    Returns:
        (user_data, user_role, None) if authorized
        (None, None, JsonResponse) if unauthorized
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        return None, None, JsonResponse({"status": 401, "success": False, "message": "Unauthorized: Missing or invalid token"}, status=401)

    token = auth_header.split(" ")[1]
    try:
        logger.info(f"Validating token with AUTH service: {AUTH_VALIDATION_URL}")
        response = requests.get(AUTH_VALIDATION_URL, headers={"Authorization": f"Bearer {token}"}, timeout=5)

        logger.info(f"AUTH service response status: {response.status_code}")
        logger.info(f"AUTH service raw response: {response.text}")  # Log full response
        
        if response.status_code != 200:
            return None, None, JsonResponse({"status": 401, "success": False, "message": "Unauthorized: Invalid token"}, status=401)

        response_json = response.json()

        # Pastikan response punya struktur yang benar
        if not response_json.get("success", False) or "data" not in response_json:
            logger.warning(f"Unexpected AUTH response: {response_json}")
            return None, None, JsonResponse({"status": 401, "success": False, "message": "Unauthorized: Invalid response from auth service"}, status=401)

        user_data = response_json["data"]
        user_role = user_data.get("role")

        logger.info(f"User Data Retrieved: {user_data}")

        if allowed_roles and user_role not in allowed_roles:
            return None, None, JsonResponse({"status": 403, "success": False, "message": "Forbidden: Permissions denied"}, status=403)

        return user_data, user_role, None

    except requests.RequestException as e:
        logger.error(f"Authorization service request failed: {e}")
        return None, None, JsonResponse({"status": 500, "success": False, "message": "Authorization service unavailable"}, status=500)
