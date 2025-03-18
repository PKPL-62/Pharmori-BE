from django.db import models

class Medicine(models.Model):
    id = models.CharField(max_length=8, primary_key=True, unique=True, editable=False)
    name = models.CharField(max_length=255)
    stock = models.IntegerField(default=0)
    price = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # ✅ Default NULL, tidak auto-update

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(stock__gte=0), name="stock_gte_0"),
            models.CheckConstraint(check=models.Q(price__gte=0), name="price_gte_0"),
        ]

    def save(self, *args, **kwargs):
        if not self.id:  # Generate ID only if it's a new object
            latest_medicine = Medicine.objects.order_by("-id").first()
            if latest_medicine:
                last_number = int(latest_medicine.id.split("-")[1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.id = f"MED-{new_number:04d}"  # Format menjadi MED-XXXX
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.name}"
