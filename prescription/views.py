from collections import defaultdict
import json
from django.utils import timezone
import uuid
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from core.utils import validate_user_role
from django_ratelimit.decorators import ratelimit
from medicine.models import Medicine
from prescription.models import MedicineQuantity, Payment, Prescription
from django.core.exceptions import ObjectDoesNotExist


@ratelimit(key="ip", rate="5/m", method="GET", block=True)
def viewall(request):
    allowed_roles = ["PHARMACIST", "DOCTOR", "PATIENT"]
    user_data, user_role, error_response = validate_user_role(request, allowed_roles)
    if error_response:
        return error_response
        
    prescriptions = Prescription.objects.filter(deleted_at__isnull=True)

    response_data = {
        "status": 200,
        "success": True,
        "message": "Successfully retrieved all prescriptions",
        "data": {"prescriptions": []}
    }

    if user_role == "PATIENT":
        for prescription in prescriptions:
            if str(prescription.patient_id) == str(user_data["id"]):
                medicines = MedicineQuantity.objects.filter(prescription=prescription).values(
                    "medicine__id", "medicine__name", "needed_qty", "fulfilled_qty"
                )

                response_data["data"]["prescriptions"].append({
                    "id": prescription.id,
                    "total_price": prescription.total_price,
                    "status": prescription.status,
                    "created_at": prescription.created_at,
                    "patient_id": str(prescription.patient_id),
                    "medicines": list(medicines)
                })
    else :
        for prescription in prescriptions:
            medicines = MedicineQuantity.objects.filter(prescription=prescription).values(
                "medicine__id", "medicine__name", "needed_qty", "fulfilled_qty"
            )

            response_data["data"]["prescriptions"].append({
                "id": prescription.id,
                "total_price": prescription.total_price,
                "status": prescription.status,
                "created_at": prescription.created_at,
                "patient_id": str(prescription.patient_id),
                "medicines": list(medicines)
            })

    return JsonResponse(response_data)

@ratelimit(key="ip", rate="5/m", method="GET", block=True)
def detail(request, prescription_id):
    allowed_roles = ["PHARMACIST", "DOCTOR", "PATIENT"]
    user_data, user_role, error_response = validate_user_role(request, allowed_roles)
    if error_response:
        return error_response
    
    if not isinstance(prescription_id, str) or not prescription_id.startswith("PRES-") or not prescription_id[5:].isdigit():
        return JsonResponse({"status": 400, "success": False, "message": "Invalid prescription ID format"}, status=400)

    try:
        prescription = Prescription.objects.get(id=prescription_id, deleted_at__isnull=True)
    except ObjectDoesNotExist:
        return JsonResponse({"status": 404, "success": False, "message": "Prescription not found"}, status=404)

    if prescription.patient_id != user_data["id"] and user_role == "PATIENT":
        return JsonResponse({"status": 404, "success": False, "message": "Prescription not found"}, status=404)
    
    medicines = MedicineQuantity.objects.filter(prescription=prescription).values(
        "medicine__id", "medicine__name", "needed_qty", "fulfilled_qty"
    )

    response_data = {
        "status": 200,
        "success": True,
        "message": "Successfully retrieved prescription details",
        "data": {
            "id": prescription.id,
            "total_price": prescription.total_price,
            "status": prescription.status,
            "created_at": prescription.created_at,
            "patient_id": str(prescription.patient_id),
            "medicines": list(medicines)
        }
    }

    return JsonResponse(response_data, status=200)

@csrf_exempt
@ratelimit(key="ip", rate="3/m", method="POST", block=True)
def create(request):
    if request.method != "POST":
        return JsonResponse({"status": 405, "success": False, "message": "Method not allowed"}, status=405)
    
    allowed_roles = ["DOCTOR"]
    user_data, user_role, error_response = validate_user_role(request, allowed_roles)
    if error_response:
        return error_response

    try:
        data = json.loads(request.body)
        patient_id = data.get("patientId")
        medicines_data = data.get("medicines", [])

        if not patient_id or not medicines_data:
            return JsonResponse({"status": 400, "success": False, "message": "Missing required fields"}, status=400)

        latest_prescription = Prescription.objects.order_by("-id").first()
        new_number = int(latest_prescription.id.split("-")[1]) + 1 if latest_prescription else 1
        prescription_id = f"PRES-{new_number:05d}"

        prescription = Prescription.objects.create(
            id=prescription_id,
            patient_id=uuid.UUID(patient_id),
            created_at=now()
        )

        medicine_qty_map = defaultdict(int)
        for medicine_entry in medicines_data:
            medicine_id = medicine_entry.get("id")
            needed_qty = medicine_entry.get("needed_qty", 0)

            if not medicine_id or needed_qty <= 0:
                return JsonResponse({"status": 400, "success": False, "message": "Invalid medicine data"}, status=400)

            medicine_qty_map[medicine_id] += needed_qty

        total_price = 0
        for medicine_id, total_needed_qty in medicine_qty_map.items():
            medicine = Medicine.objects.filter(id=medicine_id, deleted_at__isnull=True).first()
            if not medicine:
                return JsonResponse({"status": 404, "success": False, "message": f"Medicine {medicine_id} not found"}, status=404)

            MedicineQuantity.objects.create(
                prescription=prescription,
                medicine=medicine,
                needed_qty=total_needed_qty,
                fulfilled_qty=0
            )

            total_price += medicine.price * total_needed_qty

        prescription.total_price = total_price
        prescription.save()

        return JsonResponse({
            "status": 201,
            "success": True,
            "message": "Prescription created successfully",
            "data": {
                "id": prescription.id,
                "patient_id": str(prescription.patient_id),
                "total_price": prescription.total_price,
                "status": prescription.status,
                "created_at": prescription.created_at.isoformat()
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"status": 400, "success": False, "message": "Invalid JSON format"}, status=400)

    except Exception as e:
        return JsonResponse({"status": 500, "success": False, "message": str(e)}, status=500)

@csrf_exempt
@ratelimit(key="ip", rate="2/m", method="DELETE", block=True)
def delete(request, prescription_id):
    if request.method != "DELETE":
        return JsonResponse({"status": 405, "success": False, "message": "Method not allowed"}, status=405)
    
    allowed_roles = ["DOCTOR"]
    user_data, user_role, error_response = validate_user_role(request, allowed_roles)
    if error_response:
        return error_response

    try:
        try:
            prescription = get_object_or_404(Prescription, id=prescription_id, deleted_at__isnull=True)
        except Http404:
            return JsonResponse({"status": 404, "success": False, "message": "Prescription not found"}, status=404)

        if prescription.status == "FINISHED" or prescription.status == "PAID":
            return JsonResponse({
                "status": 400,
                "success": False,
                "message": f"Prescription {prescription_id} cannot be deleted as it is already finished."
            }, status=400)

        with transaction.atomic():
            if prescription.status == "ON PROCESS":
                for mq in MedicineQuantity.objects.filter(prescription=prescription):
                    medicine = mq.medicine
                    medicine.stock += mq.fulfilled_qty
                    medicine.save()
                    mq.fulfilled_qty = 0
                    mq.save()

            prescription.status = "CANCELLED"
            prescription.deleted_at = timezone.now()
            prescription.save()

        return JsonResponse({
            "status": 200,
            "success": True,
            "message": f"Prescription {prescription_id} cancelled and deleted successfully."
        })
    
    except ValueError:
        return JsonResponse({"status": 404, "success": False, "message": "Prescription not found"}, status=404)

    except Exception as e:
        return JsonResponse({"status": 500, "success": False, "message": str(e)}, status=500)

@csrf_exempt
@ratelimit(key="ip", rate="3/m", method="POST", block=True)
def process(request, prescription_id):
    allowed_roles = ["PHARMACIST"]
    user_data, user_role, error_response = validate_user_role(request, allowed_roles)
    if error_response:
        return error_response

    if not isinstance(prescription_id, str) or not prescription_id.startswith("PRES-") or not prescription_id[5:].isdigit():
        return JsonResponse({"status": 400, "success": False, "message": "Invalid prescription ID format"}, status=400)

    try:
        prescription = Prescription.objects.get(id=prescription_id)
    except ObjectDoesNotExist:
        return JsonResponse({"status": 404, "success": False, "message": "Prescription not found"}, status=404)

    if prescription.status not in ["CREATED", "ON PROCESS"]:
        return JsonResponse({
            "status": 400,
            "success": False,
            "message": "Prescription cannot be processed in its current status.",
            "data": None
        }, status=400)

    with transaction.atomic():
        all_fulfilled = True
        medicine_data = []

        for mq in MedicineQuantity.objects.filter(prescription=prescription):
            medicine = mq.medicine
            needed_qty = mq.needed_qty
            available_stock = medicine.stock

            qty_to_fulfill = min(needed_qty - mq.fulfilled_qty, available_stock)
            mq.fulfilled_qty += qty_to_fulfill
            medicine.stock -= qty_to_fulfill
            mq.save()
            medicine.save()

            if mq.fulfilled_qty < needed_qty:
                all_fulfilled = False

            medicine_data.append({
                "medicine_id": medicine.id,
                "name": medicine.name,
                "needed_qty": needed_qty,
                "fulfilled_qty": mq.fulfilled_qty,
                "stock_remaining": medicine.stock
            })

        prescription.status = "FINISHED" if all_fulfilled else "ON PROCESS"
        prescription.save()

    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Prescription processed successfully.",
        "data": {
            "prescription_id": prescription.id,
            "status": prescription.status,
            "medicines": medicine_data
        }
    }, status=200)

@csrf_exempt
@ratelimit(key="ip", rate="3/m", method="POST", block=True)
def pays(request, prescription_id):
    if request.method != "POST":
        return JsonResponse({"status": 405, "success": False, "message": "Method not allowed"}, status=405)
    
    allowed_roles = ["PATIENT"]
    user_data, user_role, error_response = validate_user_role(request, allowed_roles)
    if error_response:
        return error_response
    
    if not isinstance(prescription_id, str) or not prescription_id.startswith("PRES-") or not prescription_id[5:].isdigit():
        return JsonResponse({"status": 400, "success": False, "message": "Invalid prescription ID format"}, status=400)

    try:
        prescription = Prescription.objects.get(id=prescription_id)
    except ObjectDoesNotExist:
        return JsonResponse({"status": 404, "success": False, "message": "Prescription not found"}, status=404)
    
    if prescription.patient_id != user_data["id"]:
        return JsonResponse({"status": 400, "success": False, "message": "Cannot pays prescription that not yours"}, status=400)

    if prescription.status != "FINISHED":
        return JsonResponse({"status": 400, "success": False, "message": "Cannot pays prescription that are not finished yet"}, status=400)

    payment = Payment.objects.create(
        prescription=prescription,
        total_price=prescription.total_price,
        user_id=uuid.UUID(user_data["id"])
    )

    payment.save()
    prescription.status = "PAID"
    prescription.save()

    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Prescription paid successfully.",
        "data": {
            "payment": payment
        }
    }, status=200)