from django.db import models
from product.models import *
from django.contrib.auth.models import User
# from django.core.validators import MinValueValidator

# Create your models here.

# Cart
class Cart(TimestampedModel):
    """
    Shopping cart for storing user's selected products.
    Supports both authenticated and guest users via session.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True, help_text="For guest users")
    
    # Cart metadata
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key', 'is_active']),
        ]
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Guest Cart - {self.session_key}"
    
    def get_total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    def get_total_amount(self):
        """Calculate total cart amount"""
        total = sum(item.get_total_price() for item in self.items.all())
        return round(total, 2)
    
    def get_items_count(self):
        """Get number of different products in cart"""
        return self.items.count()
    
    def clear_cart(self):
        """Remove all items from cart"""
        self.items.all().delete()


class CartItem(TimestampedModel):
    """
    Individual items in the shopping cart.
    Links cart with specific product variants and quantities.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    # Price snapshot (to track price changes)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        unique_together = ['cart', 'product', 'variant']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cart', 'product']),
        ]
    
    def __str__(self):
        variant_info = f" - {self.variant}" if self.variant else ""
        return f"{self.product.name}{variant_info} (x{self.quantity})"
    
    def save(self, *args, **kwargs):
        # Set unit price from product/variant if not already set
        if not self.unit_price:
            if self.variant:
                self.unit_price = self.variant.get_effective_price()
            else:
                self.unit_price = self.product.get_effective_price()
        super().save(*args, **kwargs)
    
    def get_total_price(self):
        """Calculate total price for this cart item"""
        return self.unit_price * self.quantity
    
    def get_current_price(self):
        """Get current price (may differ from unit_price if price changed)"""
        if self.variant:
            return self.variant.get_effective_price()
        return self.product.get_effective_price()
    
    def has_price_changed(self):
        """Check if price has changed since adding to cart"""
        return self.unit_price != self.get_current_price()
    
    def update_quantity(self, quantity):
        """Update quantity with stock validation"""
        if self.variant:
            available_stock = self.variant.get_available_stock()
        else:
            available_stock = self.product.get_total_stock()
        
        if quantity > available_stock:
            raise ValueError(f"Only {available_stock} items available in stock")
        
        self.quantity = quantity
        self.save()
        return True