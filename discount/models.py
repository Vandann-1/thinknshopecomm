from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Discount(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)  # e.g. SAVE20, DIWALI50
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)  # 10.00 or 20(%)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)  

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(default=0)  # 0 = unlimited
    used_count = models.PositiveIntegerField(default=0)

    applicable_users = models.ManyToManyField(User, blank=True)  # if blank, applies to all users
    is_active = models.BooleanField(default=True)

    def is_valid(self, user=None, order_total=Decimal('0.00')):
        """Check if discount is valid"""
        if not self.is_active:
            return False
        if not (self.start_date <= timezone.now() <= self.end_date):
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        if order_total < self.min_order_value:
            return False
        if self.applicable_users.exists() and user not in self.applicable_users.all():
            return False
        return True

    def calculate_discount(self, order_total):
        """Return the discount amount"""
        if self.discount_type == 'percentage':
            discount = (order_total * self.value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:  # fixed
            discount = self.value

        return min(discount, order_total)  # discount should not exceed order total

    def apply_discount(self, order_total, user=None):
        """Apply discount and return new total"""
        if self.is_valid(user, order_total):
            discount_amount = self.calculate_discount(order_total)
            return order_total - discount_amount, discount_amount
        return order_total, Decimal('0.00')

    def __str__(self):
        return f"{self.code} - {self.value}{'%' if self.discount_type == 'percentage' else ''}"



"""
🔎 How it works step by step

Admin creates a Discount

Example: code="SAVE20", type="percentage", value=20, min_order_value=500.

This means a 20% discount is applied when order total is ≥ ₹500.

User applies the code during checkout.

Suppose order total = ₹1000, user enters SAVE20.

Validation check (is_valid)

Is discount active?

Is it within start and end date?

Has it reached usage limit?

Is order total above minimum required?

Is user eligible (if restricted to specific users)?

Calculate discount (calculate_discount)

If percentage: 1000 * 20% = 200.

If fixed: directly subtract fixed value (e.g., ₹500 OFF).

Apply discount (apply_discount)

New total = ₹1000 - ₹200 = ₹800.

Save usage

When an order is placed, used_count is incremented.




"""