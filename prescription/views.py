from collections import defaultdict
import json
import uuid
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from django.views.decorators.csrf import csrf_exempt
from medicine.models import Medicine
from django.utils.timezone import now
from prescription.models import MedicineQuantity, Prescription

def viewall(request):
    prescriptions = Prescription.objects.filter(deleted_at__isnull=True)

    response_data = {
        "status": 200,
        "success": True,
        "message": "Successfully retrieved all prescriptions",
        "data": {
            "prescriptions": []
        }
    }

    for prescription in prescriptions:
        medicines = MedicineQuantity.objects.filter(prescription=prescription).values(
            "medicine__id", "medicine__name", "needed_qty", "fulfilled_qty"
        )

        response_data["data"]["prescriptions"].append({
            "id": prescription.id,
            "total_price": prescription.total_price,
            "status": prescription.status,
            "created_at": prescription.created_at,
            "patient_id": str(prescription.patient_id),  # UUID harus dikonversi ke string
            "medicines": list(medicines)
        })

    return JsonResponse(response_data)

def detail(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id, deleted_at__isnull=True)

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
            "patient_id": str(prescription.patient_id),  # UUID harus diubah ke string
            "medicines": list(medicines)
        }
    }

    return JsonResponse(response_data)

@csrf_exempt
def create(request):
    if request.method != "POST":
        return JsonResponse({"status": 405, "success": False, "message": "Method Not Allowed"}, status=405)

    try:
        data = json.loads(request.body)
        patient_id = data.get("patientId")
        medicines_data = data.get("medicines", [])

        if not patient_id or not medicines_data:
            return JsonResponse({"status": 400, "success": False, "message": "Missing required fields"}, status=400)

        # Generate Prescription ID
        latest_prescription = Prescription.objects.order_by("-id").first()
        if latest_prescription:
            last_number = int(latest_prescription.id.split("-")[1])
            new_number = last_number + 1
        else:
            new_number = 1
        prescription_id = f"PRES-{new_number:05d}"

        # Buat Prescription baru
        prescription = Prescription.objects.create(
            id=prescription_id,
            patient_id=uuid.UUID(patient_id),
            created_at=now()
        )

        # Gabungkan medicine quantities dengan defaultdict
        medicine_qty_map = defaultdict(int)
        for medicine_entry in medicines_data:
            medicine_id = medicine_entry.get("id")
            needed_qty = medicine_entry.get("needed_qty", 0)

            if not medicine_id or needed_qty <= 0:
                return JsonResponse({"status": 400, "success": False, "message": "Invalid medicine data"}, status=400)

            # Tambahkan jumlah jika id yang sama sudah ada
            medicine_qty_map[medicine_id] += needed_qty

        total_price = 0
        for medicine_id, total_needed_qty in medicine_qty_map.items():
            # Cek apakah obat tersedia
            medicine = Medicine.objects.filter(id=medicine_id, deleted_at__isnull=True).first()
            if not medicine:
                return JsonResponse({"status": 404, "success": False, "message": f"Medicine {medicine_id} not found"}, status=404)

            # Tambah MedicineQuantity hanya satu kali per ID
            MedicineQuantity.objects.create(
                prescription=prescription,
                medicine=medicine,
                needed_qty=total_needed_qty,
                fulfilled_qty=0
            )

            # Hitung total harga
            total_price += medicine.price * total_needed_qty

        # Simpan total harga Prescription
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

def process(request):
    return "process";

def delete(request):
    return "delete";

def update(request):
    return "update";

def pays(request):
    return "pays";