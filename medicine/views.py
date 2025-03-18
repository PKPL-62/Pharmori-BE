import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from medicine.models import Medicine
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='GET', block=True)
def viewall(request):
    medicines = Medicine.objects.filter(deleted_at__isnull=True)
    response_data = {
        "status": 200,
        "success": True,
        "message": "Successfully retrieved active medicines",
        "data": {"medicines": [
            {
                "id": med.id,
                "name": med.name,
                "stock": med.stock,
                "price": med.price,
                "created_at": med.created_at,
            }
            for med in medicines
        ]},
    }
    return JsonResponse(response_data, status=200)

@ratelimit(key='ip', rate='5/m', method='GET', block=True)
def detail(request, medicine_id):
    medicine = get_object_or_404(Medicine, id=medicine_id, deleted_at__isnull=True)
    response_data = {
        "status": 200,
        "success": True,
        "message": "Successfully retrieved medicine details",
        "data": {
            "id": medicine.id,
            "name": medicine.name,
            "stock": medicine.stock,
            "price": medicine.price,
            "created_at": medicine.created_at,
        }
    }
    return JsonResponse(response_data, status=200)

@csrf_exempt
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def create(request):
    if request.method != "POST":
        return JsonResponse({"status": 405, "success": False, "message": "Method Not Allowed"}, status=405)
    try:
        data = json.loads(request.body)
        name = data.get("name")
        stock = data.get("stock")
        price = data.get("price")

        if not name or stock is None or price is None:
            return JsonResponse({"status": 400, "success": False, "message": "Missing required fields"}, status=400)

        if stock < 0 or price < 0:
            return JsonResponse({"status": 400, "success": False, "message": "Stock and price must be >= 0"}, status=400)

        last_medicine = Medicine.objects.order_by("-id").first()
        if last_medicine:
            last_id_number = int(last_medicine.id.split("-")[1])
        else:
            last_id_number = 0
        
        new_id = f"MED-{last_id_number + 1:05d}"

        medicine = Medicine.objects.create(id=new_id, name=name, stock=stock, price=price)

        response_data = {
            "status": 201,
            "success": True,
            "message": "Medicine created successfully",
            "data": {
                "id": medicine.id,
                "name": medicine.name,
                "stock": medicine.stock,
                "price": medicine.price,
                "created_at": medicine.created_at,
            }
        }
        return JsonResponse(response_data, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"status": 400, "success": False, "message": "Invalid JSON"}, status=400)

    except Exception as e:
        return JsonResponse({"status": 500, "success": False, "message": str(e)}, status=500)

@csrf_exempt
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def restock(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            medicine_id = data.get("id")
            stock_to_add = data.get("stock")

            if not medicine_id or stock_to_add is None:
                return JsonResponse({"status": 400, "success": False, "message": "ID and stock are required"}, status=400)

            if stock_to_add < 0:
                return JsonResponse({"status": 400, "success": False, "message": "Stock cannot be negative"}, status=400)

            try:
                medicine = Medicine.objects.get(id=medicine_id, deleted_at__isnull=True)
            except Medicine.DoesNotExist:
                return JsonResponse({"status": 404, "success": False, "message": "Medicine not found"}, status=404)

            medicine.stock += stock_to_add
            medicine.save()

            return JsonResponse({
                "status": 200,
                "success": True,
                "message": "Stock updated successfully",
                "data": {
                    "id": medicine.id,
                    "name": medicine.name,
                    "stock": medicine.stock,
                    "price": medicine.price
                }
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"status": 400, "success": False, "message": "Invalid JSON format"}, status=400)

    return JsonResponse({"status": 405, "success": False, "message": "Method not allowed"}, status=405)

@csrf_exempt
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def delete(request, medicine_id):
    if request.method == "POST":
        try:
            try:
                medicine = Medicine.objects.get(id=medicine_id, deleted_at__isnull=True)
            except Medicine.DoesNotExist:
                return JsonResponse({"status": 404, "success": False, "message": "Medicine not found"}, status=404)

            medicine.deleted_at = now()
            medicine.save()

            return JsonResponse({
                "status": 200,
                "success": True,
                "message": "Medicine deleted successfully"
            }, status=200)

        except Exception as e:
            return JsonResponse({"status": 500, "success": False, "message": str(e)}, status=500)

    return JsonResponse({"status": 405, "success": False, "message": "Method not allowed"}, status=405)
