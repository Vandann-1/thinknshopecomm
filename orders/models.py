from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from decimal import Decimal
from product.models import * 
from address.models import Address

# Order Management System
class Order(TimestampedModel):
    """
    Main order model to track customer orders.
    Simple and effective order tracking system.
    """
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('cod', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('wallet', 'Digital Wallet'),
        ('netbanking', 'Net Banking'),
    ]
    
    # Order Identification
    order_id = models.CharField(max_length=50, unique=True, help_text="Unique order identifier", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    
    # Order Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending', null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending', null=True, blank=True)
    
    # Pricing Information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)], null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)], null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cod', null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Payment gateway reference ID", null=True)
    
    # Address - Use your existing Address model
    shipping_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='shipping_orders', null=True, blank=True)
    billing_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='billing_orders', null=True, blank=True)
    
    # Tracking Information
    tracking_id = models.CharField(max_length=100, blank=True, help_text="Courier tracking ID", null=True)
    courier_partner = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    
    # Important Dates
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Additional Information
    order_notes = models.TextField(blank=True, help_text="Special instructions from customer", null=True)
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_id']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Order {self.order_id} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Set billing address same as shipping if not provided
        if not self.billing_address:
            self.billing_address = self.shipping_address
        
        super().save(*args, **kwargs)
    
    def get_total_items(self):
        """Get total number of items in the order"""
        return sum(item.quantity for item in self.items.all())
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']
    
    def update_status(self, new_status):
        """Update order status with timestamp tracking"""
        self.status = new_status
        
        # Set appropriate timestamps
        now = timezone.now()
        if new_status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = now
        elif new_status == 'shipped' and not self.shipped_at:
            self.shipped_at = now
        elif new_status == 'delivered' and not self.delivered_at:
            self.delivered_at = now
        
        self.save()


# OrderItem
class OrderItem(TimestampedModel):
    """
    Individual items within an order.
    Links to specific product variants with quantities and pricing.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    
    # Store product details at time of order (for historical accuracy)
    product_name = models.CharField(max_length=255, null=True, blank=True)
    variant_details = models.CharField(max_length=100, help_text="Color and Size info", null=True, blank=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.product_name} ({self.variant_details}) x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Store product details for historical accuracy
        if self.product:
            self.product_name = self.product.name
        if self.variant:
            self.variant_details = f"{self.variant.color.name}, {self.variant.size.name}"
        
        # Calculate total price
        if self.unit_price and self.quantity:
            self.total_price = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)


# OrderStatusUpdate
class OrderStatusUpdate(TimestampedModel):
    """
    Simple tracking of order status changes for audit trail.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_updates', null=True, blank=True)
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_id} - {self.old_status} → {self.new_status}"
    
    def save(self, *args, **kwargs):
        # Automatically capture old status from order before saving
        if self.order and not self.old_status:
            self.old_status = self.order.status
        
        super().save(*args, **kwargs)
        
        # Update the order status after saving the status update
        if self.order and self.new_status:
            self.order.status = self.new_status
            self.order.save(update_fields=['status'])