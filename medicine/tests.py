from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now
from medicine.models import Medicine
import json

class MedicineViewsTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create a test medicine
        self.medicine1 = Medicine.objects.create(
            id="MED-00001", name="Paracetamol", stock=10, price=5000
        )
        self.medicine2 = Medicine.objects.create(
            id="MED-00002", name="Ibuprofen", stock=20, price=8000, deleted_at=now()
        )

    def test_viewall_medicines(self):
        """Test retrieving all active medicines"""
        response = self.client.get(reverse("medicine:viewall"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(len(response.json()["data"]["medicines"]), 1)

    def test_detail_valid_medicine(self):
        """Test retrieving a valid medicine's details"""
        response = self.client.get(reverse("medicine:detail", args=["MED-00001"]))
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

    def test_restock_valid_medicine(self):
        """Test restocking a valid medicine"""
        data = {"id": "MED-00001", "stock": 10}
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

    def test_restock_negative_stock(self):
        """Test restocking with negative stock value"""
        data = {"id": "MED-00001", "stock": -10}
        response = self.client.post(
            reverse("medicine:restock"),
            json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_valid_medicine(self):
        """Test soft-deleting a valid medicine"""
        response = self.client.post(reverse("medicine:delete", args=["MED-00001"]))
        self.assertEqual(response.status_code, 200)
        self.medicine1.refresh_from_db()
        self.assertIsNotNone(self.medicine1.deleted_at)

    def test_delete_invalid_medicine(self):
        """Test deleting a non-existent medicine"""
        response = self.client.post(reverse("medicine:delete", args=["MED-99999"]))
        self.assertEqual(response.status_code, 404)

    def test_method_not_allowed(self):
        """Test sending an invalid HTTP method"""
        response = self.client.get(reverse("medicine:create"))  # Should be POST
        self.assertEqual(response.status_code, 405)

        response = self.client.get(reverse("medicine:restock"))  # Should be POST
        self.assertEqual(response.status_code, 405)

        response = self.client.get(reverse("medicine:delete", args=["MED-00001"]))  # Should be POST
        self.assertEqual(response.status_code, 405)
