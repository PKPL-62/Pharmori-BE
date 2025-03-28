from django.http import JsonResponse

def ratelimit_exceeded_view(request, exception=None):
    return JsonResponse({
        "status": 429,
        "success": False,
        "message": "Too many requests. Please try again later."
    }, status=429)
