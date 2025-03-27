from django.utils import timezone
import uuid
from django.db import models
from medicine.models import Medicine

class Prescription(models.Model):
    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("ON PROCESS", "On Process"),
        ("FINISHED", "Finished"),
        ("CANCELLED", "Cancelled"),
        ("PAID", "Paid")
    ]

    id = models.CharField(max_length=10, primary_key=True, unique=True, editable=False)
    total_price = models.IntegerField(default=0, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    patient_id = models.UUIDField(null=False, blank=False)
    medicines = models.ManyToManyField(Medicine, through="MedicineQuantity")

    def save(self, *args, **kwargs):
        if not self.id:
            latest_prescription = Prescription.objects.order_by("-id").first()
            if latest_prescription:
                last_number = int(latest_prescription.id.split("-")[1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.id = f"PRES-{new_number:05d}"

        self.total_price = sum(
            mq.needed_qty * mq.medicine.price for mq in self.medicinequantity_set.all()
        ) 

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Prescription {self.id} (Deleted: {self.deleted_at is not None})"

    class Meta:
        indexes = [
            models.Index(fields=["deleted_at"]),
        ]


class MedicineQuantity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    needed_qty = models.IntegerField()
    fulfilled_qty = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(needed_qty__gte=1),
                name="needed_qty_gte_1"
            ),
            models.CheckConstraint(
                check=models.Q(fulfilled_qty__gte=0),
                name="fulfilled_qty_gte_0"
            ),
            models.CheckConstraint(
                check=models.Q(fulfilled_qty__lte=models.F("needed_qty")),
                name="fulfilled_qty_lte_needed_qty"
            )
        ]

    def __str__(self):
        return f"{self.needed_qty} of {self.medicine.name} for Prescription {self.prescription.id} (Fulfilled: {self.fulfilled_qty})"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    total_price = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    user_id = models.UUIDField(null=False, blank=False)

    def __str__(self):
        return f"Payment {self.id} - Prescription {self.prescription.id} - Amount: {self.total_price}"
