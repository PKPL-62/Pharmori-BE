from unittest.mock import patch
from django.db import IntegrityError
from django.http import HttpRequest
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now
from core.utils import get_test_token
from medicine.models import Medicine
import json
import os

from medicine.views import detail

class MedicineViewsTest(TestCase):
    # @classmethod
    # def setUpTestData(cls):
    #     cls.pharmacist_token = get_test_token("PHARMACIST")
    #     cls.doctor_token = get_test_token("DOCTOR")
    #     cls.patient_token = get_test_token("PATIENT")

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.medicine1 = Medicine.objects.create(
            id="MED-0001", name="Paracetamol", stock=10, price=5000
        )
        self.medicine2 = Medicine.objects.create(
            id="MED-0002", name="Ibuprofen", stock=20, price=8000, deleted_at=now()
        )
        

    def test_viewall_medicines(self):
        """Test retrieving all active medicines with authentication"""
        response = self.client.get(reverse("medicine:viewall"))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(len(response.json()["data"]["medicines"]), 1)

    def test_detail_valid_medicine(self):
        """Test retrieving a valid medicine's details"""
        response = self.client.get(reverse("medicine:detail", args=["MED-0001"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["name"], "Paracetamol")

    def test_detail_invalid_medicine(self):
        """Test retrieving a non-existing medicine"""
        response = self.client.get(reverse("medicine:detail", args=["MED-99999"]))
        self.assertEqual(response.status_code, 404)

    def test_create_valid_medicine(self):
        """Test creating a valid medicine"""
        data = {"name": "Aspirin", "stock": 50, "price": 7000}
        response = self.client.post(
            reverse("medicine:create"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        self.assertEqual(Medicine.objects.count(), 3)

    def test_create_missing_fields(self):
        """Test medicine creation with missing fields"""
        data = {"name": "Aspirin"}
        response = self.client.post(
            reverse("medicine:create"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Missing required fields")

    def test_create_invalid_stock_price(self):
        """Test medicine creation with negative stock or price"""
        data = {"name": "Aspirin", "stock": -10, "price": 7000}
        response = self.client.post(
            reverse("medicine:create"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_invalid_json(self):
        """Test medicine creation with invalid JSON format"""
        response = self.client.post(
            reverse("medicine:create"),
            "invalid_json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid JSON format")

    def test_restock_valid_medicine(self):
        """Test restocking a valid medicine"""
        data = {"id": "MED-0001", "stock": 10}
        response = self.client.post(
            reverse("medicine:restock"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.medicine1.refresh_from_db()
        self.assertEqual(self.medicine1.stock, 20)

    def test_restock_invalid_medicine(self):
        """Test restocking a non-existent medicine"""
        data = {"id": "MED-99999", "stock": 10}
        response = self.client.post(
            reverse("medicine:restock"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_create_duplicate_medicine(self):
        """Test creating a medicine with duplicate name"""
        data = {"name": "Paracetamol", "stock": 10, "price": 5000}
        response = self.client.post(
            reverse("medicine:create"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_valid_medicine(self):
        """Test soft-deleting a valid medicine"""
        response = self.client.post(reverse("medicine:delete", args=["MED-0001"]))
        self.assertEqual(response.status_code, 200)
        self.medicine1.refresh_from_db()
        self.assertIsNotNone(self.medicine1.deleted_at)

    def test_stock_cannot_be_negative(self):
        """Ensure stock cannot be negative due to constraint."""
        with self.assertRaises(IntegrityError):
            Medicine.objects.create(name="Test Medicine", stock=-1, price=10)

    def test_price_cannot_be_negative(self):
        """Ensure price cannot be negative due to constraint."""
        with self.assertRaises(IntegrityError):
            Medicine.objects.create(name="Test Medicine", stock=10, price=-1)
    
    def test_id_auto_generation(self):
        """Ensure ID is automatically generated in the correct format."""
        medicine = Medicine.objects.create(name="Test Medicine", stock=10, price=50)
        self.assertTrue(medicine.id.startswith("MED-"))
        self.assertEqual(len(medicine.id), 8)
    
    def test_id_auto_increment(self):
        """Ensure ID auto-increments correctly."""
        Medicine.objects.create(name="Medicine 3", stock=10, price=50)
        Medicine.objects.create(name="Medicine 4", stock=10, price=50)
        last_medicine = Medicine.objects.latest("id")
        self.assertEqual(last_medicine.id, "MED-0004")
    
    def test_last_id_number_initialization(self):
        """Ensure first medicine gets ID MED-0001 when DB is empty"""
        Medicine.objects.all().delete()
        response = self.client.post(
            reverse("medicine:create"),
            json.dumps({"name": "Aspirin", "stock": 10, "price": 5000}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        new_medicine = Medicine.objects.get(name="Aspirin")
        self.assertEqual(new_medicine.id, "MED-0001")

    def test_medicine_id_generation_when_empty(self):
        """Test that the first medicine gets ID 'MED-0001' when the table is empty"""
        medicine = Medicine(name="Paracetamol", stock=10, price=5000)
        medicine.save()
        self.assertEqual(medicine.id, "MED-0003")

    def test_medicine_id_generation_when_existing(self):
        """Test that the ID increments correctly when other medicines exist"""
        medicine = Medicine(name="Ibuprofen", stock=8, price=4000)
        medicine.save()
        self.assertEqual(medicine.id, "MED-0003")

    def test_str_representation(self):
        """Test the __str__ method"""
        medicine = Medicine.objects.create(id="MED-0005", name="Vitamin C", stock=15, price=2000)
        self.assertEqual(str(medicine), "MED-0005 - Vitamin C")
    
    def test_create_first_medicine(self):
        """Test creating new medicine when database is empty"""
        Medicine.objects.all().delete() 
        medicine = Medicine(name="Ibuprofen", stock=8, price=4000)
        medicine.save()
        self.assertEqual(medicine.id, "MED-0001")

    def test_invalid_medicine_id_missing_prefix(self):
        """Test with an ID missing the 'MED-' prefix"""
        response = self.client.get("/medicine/detail/0001/")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "status": 400, "success": False, "message": "Invalid medicine ID format"
        })

    def test_invalid_medicine_id_non_numeric(self):
        """Test with an ID that has non-numeric characters after 'MED-'"""
        response = self.client.get("/medicine/detail/MED-ABCD/")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "status": 400, "success": False, "message": "Invalid medicine ID format"
        })

    def test_invalid_medicine_id_none(self):
        """Test with an ID that is None"""
        response = self.client.get("/medicine/detail/None/")
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            "status": 400, "success": False, "message": "Invalid medicine ID format"
        })
    
    def test_invalid_medicine_id_wrong_type(self):
        """Test when `medicine_id` is an integer instead of a string"""
        request = HttpRequest()
        response = detail(request, 1234)
        self.assertEqual(response.status_code, 400)

    def test_get_create_medicine(self):
        """Test sending GET request to the medicine creation endpoint"""
        response = self.client.get(reverse("medicine:create"))

        self.assertEqual(response.status_code, 405)

    @patch("medicine.models.Medicine.objects.create")
    def test_internal_server_error(self, mock_create):
        """Test that a 500 error is returned when an unexpected exception occurs"""
        mock_create.side_effect = Exception("Database error")

        payload = {
            "name": "Test Medicine",
            "stock": 10,
            "price": 1000
        }

        response = self.client.post(reverse("medicine:create"), data=payload, content_type="application/json")

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Database error")
    
    def test_restock_missing_fields(self):
        """Test restocking with missing 'id' or 'stock' field"""
        payload = {
            "stock": 10
        }
        response = self.client.post(reverse("medicine:restock"), data=payload, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "ID and stock are required")

    def test_restock_negative_stock(self):
        """Test restocking with negative stock"""
        payload = {
            "id": "MED-0001",
            "stock": -5
        }
        response = self.client.post(reverse("medicine:restock"), data=payload, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Stock cannot be negative")
    
    def test_restock_invalid_json(self):
        """Test restocking with invalid JSON format"""
        invalid_payload = "{invalid_json: true}"
        response = self.client.post(reverse("medicine:restock"), data=invalid_payload, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Invalid JSON format")

    def test_restock_invalid_method(self):
        """Test sending GET request to restock endpoint"""
        response = self.client.get(reverse("medicine:restock"))

        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Method not allowed")

    def test_delete_non_existent_medicine(self):
        """Test deleting a medicine that does not exist"""
        response = self.client.post(reverse("medicine:delete", args=["MED-9999"]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Medicine not found")

    def test_delete_internal_server_error(self):
        """Test delete when an unexpected exception occurs"""
        with patch("medicine.models.Medicine.objects.get") as mock_get:
            mock_get.side_effect = Exception("Unexpected error")

            response = self.client.post(reverse("medicine:delete", args=["MED-0001"]))

            self.assertEqual(response.status_code, 500)
            self.assertFalse(response.json()["success"])
            self.assertEqual(response.json()["message"], "Unexpected error")

    def test_delete_invalid_method(self):
        """Test sending GET request to delete endpoint"""
        response = self.client.get(reverse("medicine:delete", args=["MED-0001"]))

        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Method not allowed")