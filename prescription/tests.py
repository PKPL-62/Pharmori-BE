from unittest.mock import patch
import uuid
import json
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from medicine.models import Medicine
from prescription.models import MedicineQuantity, Payment, Prescription

class PrescriptionTestCase(TestCase):
    def setUp(self):
        self.patient_id = "11111111-1111-1111-1111-111111111111"
        self.medicine1 = Medicine.objects.create(id="MED-0001", name="Paracetamol", price=1000, stock=50)
        self.medicine2 = Medicine.objects.create(id="MED-0002", name="Ibuprofen", price=1500, stock=30)
        self.prescription = Prescription.objects.create(patient_id=self.patient_id, created_at=timezone.now())
        self.create_url = "/prescription/create"
        self.delete_url = f"/prescription/delete/{self.prescription.id}"
        self.process_url = f"/prescription/process/{self.prescription.id}"
        self.pay_url = f"/prescription/pays/{self.prescription.id}"
        self.update_url = f"/prescription/update/{self.prescription.id}"

    def test_create_prescription(self):
        prescription = Prescription.objects.create(patient_id=self.patient_id, created_at=timezone.now())
        self.assertIsNotNone(prescription.id)
        self.assertEqual(prescription.status, "CREATED")
    
    def test_create_prescription_success(self):
        data = {
            "patientId": str(self.patient_id),
            "medicines": [
                {"id": "MED-0001", "needed_qty": 10},
                {"id": "MED-0002", "needed_qty": 5}
            ]
        }
        response = self.client.post(self.create_url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["status"], 201)
        self.assertEqual(response_data["data"]["patient_id"], str(self.patient_id))
        self.assertEqual(response_data["data"]["total_price"], 1000 * 10 + 1500 * 5)

    def test_create_prescription_missing_patient_id(self):
        data = {"medicines": [{"id": "MED-0001", "needed_qty": 10}]}
        response = self.client.post(self.create_url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Missing required fields")
    
    def test_create_prescription_invalid_medicine(self):
        data = {
            "patientId": str(self.patient_id),
            "medicines": [{"id": "MED-9999", "needed_qty": 10}]
        }
        response = self.client.post(self.create_url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Medicine MED-9999 not found")

    def test_create_prescription_invalid_json(self):
        response = self.client.post(self.create_url, "invalid json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid JSON format")

    def test_create_prescription_empty_medicines(self):
        data = {"patientId": str(self.patient_id), "medicines": []}
        response = self.client.post(self.create_url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Missing required fields")

    def test_add_medicine_to_prescription(self):
        medicine_qty = MedicineQuantity.objects.create(
            prescription=self.prescription, medicine=self.medicine1, needed_qty=10, fulfilled_qty=0
        )
        self.assertEqual(medicine_qty.needed_qty, 10)
        self.assertEqual(medicine_qty.fulfilled_qty, 0)

    def test_view_prescription(self):
        response = self.client.get(f"/prescription/detail/{self.prescription.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.json()["data"])

    def test_delete_prescription(self):
        response = self.client.delete(f"/prescription/delete/{self.prescription.id}")
        self.assertEqual(response.status_code, 200)
        self.prescription.refresh_from_db()
        self.assertIsNotNone(self.prescription.deleted_at)

    def test_process_prescription(self):
        MedicineQuantity.objects.create(
            prescription=self.prescription, medicine=self.medicine1, needed_qty=5, fulfilled_qty=0
        )
        response = self.client.post(f"/prescription/process/{self.prescription.id}")
        self.assertEqual(response.status_code, 200)
        self.prescription.refresh_from_db()
        self.assertIn(self.prescription.status, ["ON PROCESS", "FINISHED"])
    
    def test_prescription_str(self):
        expected_str = f"Prescription {self.prescription.id} (Deleted: False)"
        self.assertEqual(str(self.prescription), expected_str)

        self.prescription.deleted_at = timezone.now()
        self.prescription.save()

        expected_str_deleted = f"Prescription {self.prescription.id} (Deleted: True)"
        self.assertEqual(str(self.prescription), expected_str_deleted)

    def test_medicine_quantity_str(self):
        medicine_qty = MedicineQuantity.objects.create(
            prescription=self.prescription, medicine=self.medicine1, needed_qty=5, fulfilled_qty=2
        )
        expected_str = f"5 of {self.medicine1.name} for Prescription {self.prescription.id} (Fulfilled: 2)"
        self.assertEqual(str(medicine_qty), expected_str)

    def test_payment_str(self):
        payment = Payment.objects.create(
            prescription=self.prescription, total_price=5000, user_id=uuid.uuid4()
        )
        expected_str = f"Payment {payment.id} - Prescription {self.prescription.id} - Amount: 5000"
        self.assertEqual(str(payment), expected_str)

    def test_viewall_prescriptions(self):
        MedicineQuantity.objects.create(
            prescription=self.prescription, medicine=self.medicine1, needed_qty=10, fulfilled_qty=5
        )
        MedicineQuantity.objects.create(
            prescription=self.prescription, medicine=self.medicine2, needed_qty=5, fulfilled_qty=5
        )

        response = self.client.get("/prescription/viewall")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], 200)
        self.assertEqual(len(data["data"]["prescriptions"]), 1)

        prescription_data = data["data"]["prescriptions"][0]
        self.assertEqual(prescription_data["id"], self.prescription.id)
        self.assertEqual(prescription_data["total_price"], self.prescription.total_price)
        self.assertEqual(prescription_data["status"], self.prescription.status)
        self.assertEqual(prescription_data["patient_id"], str(self.prescription.patient_id))
        self.assertEqual(len(prescription_data["medicines"]), 2)

        for medicine in prescription_data["medicines"]:
            self.assertIn("medicine__id", medicine)
            self.assertIn("medicine__name", medicine)
            self.assertIn("needed_qty", medicine)
            self.assertIn("fulfilled_qty", medicine)
    
    def test_delete_invalid_method(self):
        """Test sending GET request to delete endpoint"""
        response = self.client.get(reverse("prescription:delete", args=["PRES-00001"]))

        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Method not allowed")
    
    def test_create_prescription_method_not_allowed(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["message"], "Method not allowed")
    
    def test_create_prescription_invalid_medicine_data(self):
        data = {
            "patientId": str(self.patient_id),
            "medicines": [
                {"id": "MED-0001", "needed_qty": 0},
                {"id": "MED-0002", "needed_qty": -5}
            ]
        }
        response = self.client.post(self.create_url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid medicine data")
    
    def test_create_prescription_internal_server_error(self):
        with patch("prescription.models.Prescription.objects.create", side_effect=Exception("Database error")):
            response = self.client.post(self.create_url, json.dumps({
                "patientId": str(uuid.uuid4()), 
                "medicines": [{"id": str(uuid.uuid4()), "needed_qty": 1}]
            }), content_type="application/json")

            self.assertEqual(response.status_code, 500)
            self.assertFalse(response.json()["success"])
            self.assertIn("message", response.json())
            self.assertEqual(response.json()["message"], "Database error")

    def test_delete_prescription_invalid_method(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["message"], "Method not allowed")

    def test_delete_prescription_non_existent(self):
        response = self.client.delete("/prescription/delete/invalid-id")
        self.assertEqual(response.status_code, 404)

    def test_delete_prescription_finished(self):
        self.prescription.status = "FINISHED"
        self.prescription.save()
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], f"Prescription {self.prescription.id} cannot be deleted as it is already finished.")

    def test_delete_prescription_on_process_stock_restore(self):
        self.prescription.status = "ON PROCESS"
        self.prescription.save()
        medicine_qty = MedicineQuantity.objects.create(
            prescription=self.prescription, medicine=self.medicine1, needed_qty=5, fulfilled_qty=5
        )
        stock_before = self.medicine1.stock
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], f"Prescription {self.prescription.id} cancelled and deleted successfully.")
        self.medicine1.refresh_from_db()
        self.assertEqual(self.medicine1.stock, stock_before + 5)

    def test_delete_prescription_success(self):
        self.prescription = Prescription.objects.create(patient_id=self.patient_id, created_at=timezone.now())
        response = self.client.delete(f"/prescription/delete/{self.prescription.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], f"Prescription {self.prescription.id} cancelled and deleted successfully.")

    @patch("prescription.views.get_object_or_404", side_effect=ValueError)
    def test_delete_prescription_value_error(self, mock_get_object):
        """Test that a ValueError is properly handled when deleting a prescription"""
        response = self.client.delete("/prescription/delete/PRES-INVALID")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Prescription not found")
    
    @patch("prescription.views.Prescription.save", side_effect=Exception("Unexpected error"))
    def test_delete_prescription_unexpected_exception(self, mock_save):
        """Test that an unexpected exception is properly handled when deleting a prescription"""
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["message"], "Unexpected error")
    
    def test_process_prescription_invalid_status(self):
        self.prescription.status = "FINISHED"
        self.prescription.save()
        response = self.client.post(self.process_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Prescription cannot be processed in its current status.")

    def test_process_prescription_success(self):
        self.prescription.status = "CREATED"
        self.prescription.save()
        MedicineQuantity.objects.create(prescription=self.prescription, medicine=self.medicine1, needed_qty=5, fulfilled_qty=0)
        response = self.client.post(self.process_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], 200)

    def test_process_prescription_insufficient_stock(self):
        self.prescription.status = "CREATED"
        self.prescription.save()
        MedicineQuantity.objects.create(prescription=self.prescription, medicine=self.medicine1, needed_qty=100, fulfilled_qty=0)
        response = self.client.post(self.process_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], 200)
        self.assertEqual(response.json()["data"]["status"], "ON PROCESS")

    def test_update_prescription_invalid_status(self):
        self.prescription.status = "FINISHED"
        self.prescription.save()

        session = self.client.session
        session["user_data"] = {"id": "doctor-id"}
        session["user_role"] = "DOCTOR"
        session.save()

        data = {
            "patientId": str(self.patient_id),
            "medicines": [{"id": self.medicine1.id, "needed_qty": 2}]
        }

        response = self.client.post(f"/prescription/update/{self.prescription.id}", json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Invalid prescription status to update")

    def test_pay_prescription_method_not_allowed(self):
        response = self.client.get(f"/prescription/pays/{self.prescription.id}")
        self.assertEqual(response.status_code, 405)

    def test_pay_prescription_invalid_format(self):
        response = self.client.post("/prescription/pays/INVALID-ID")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid prescription ID format", response.json()["message"])

    def test_pay_prescription_not_found(self):
        response = self.client.post("/prescription/pays/PRES-999999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Prescription not found", response.json()["message"])

    def test_pay_prescription_not_owned(self):
        self.prescription.status = "FINISHED"
        self.prescription.save()

        session = self.client.session
        session["user_data"] = {"id": str(uuid.uuid4())}
        session["user_role"] = "PATIENT"
        session.save()

        response = self.client.post(f"/prescription/pays/{self.prescription.id}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Cannot pays prescription that not yours")

    def test_update_prescription_method_not_allowed(self):
        response = self.client.get(f"/prescription/update/{self.prescription.id}")
        self.assertEqual(response.status_code, 405)

    def test_update_prescription_invalid_json(self):
        session = self.client.session
        session["user_data"] = {"id": str(uuid.uuid4())}
        session["user_role"] = "DOCTOR"
        session.save()

        response = self.client.post(
            f"/prescription/update/{self.prescription.id}",
            "invalid json",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid JSON format")

    def test_update_prescription_not_found(self):
        session = self.client.session
        session["user_data"] = {"id": str(uuid.uuid4())}
        session["user_role"] = "DOCTOR"
        session.save()

        data = {"patientId": str(uuid.uuid4()), "medicines": []}
        response = self.client.post(
            f"/prescription/update/{self.prescription.id}",
            json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Prescription not found")

    def test_update_prescription_wrong_status(self):
        self.prescription.status = "FINISHED"
        self.prescription.save()

        session = self.client.session
        session["user_data"] = {"id": str(uuid.uuid4())}
        session["user_role"] = "DOCTOR"
        session.save()

        data = {
            "patientId": str(self.patient_id),
            "medicines": [{"id": self.medicine1.id, "needed_qty": 2}]
        }
        response = self.client.post(
            f"/prescription/update/{self.prescription.id}",
            json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Invalid prescription status to update")

    def test_update_prescription_invalid_medicine_data(self):
        self.prescription.status = "CREATED"
        self.prescription.save()

        session = self.client.session
        session["user_data"] = {"id": str(uuid.uuid4())}
        session["user_role"] = "DOCTOR"
        session.save()

        data = {
            "patientId": str(self.patient_id),
            "medicines": [{"id": None, "needed_qty": 0}]
        }

        response = self.client.post(
            f"/prescription/update/{self.prescription.id}",
            json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid medicine data")

    def test_update_prescription_medicine_not_found(self):
        self.prescription.status = "CREATED"
        self.prescription.save()

        session = self.client.session
        session["user_data"] = {"id": str(uuid.uuid4())}
        session["user_role"] = "DOCTOR"
        session.save()

        data = {
            "patientId": str(self.patient_id),
            "medicines": [{"id": str(uuid.uuid4()), "needed_qty": 2}]
        }

        response = self.client.post(
            f"/prescription/update/{self.prescription.id}",
            json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.json()["message"].startswith("Medicine"))
