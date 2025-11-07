# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
import uuid


# Address Model
class Address(models.Model):
    """
    Robust address model for storing user addresses with comprehensive fields
    """
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'), 
        ('other', 'Other'),
    ]
    
    # Basic identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    
    # Address identification
    label = models.CharField(max_length=100, help_text="Address label like 'Home', 'Office', etc.")
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    is_default = models.BooleanField(default=False, help_text="Default address for this user")
    
    # Contact information
    full_name = models.CharField(max_length=100, help_text="Recipient's full name")
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', 
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    alternate_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)
    
    # Address components
    address_line_1 = models.CharField(max_length=255, help_text="House/Building number, Street name")
    address_line_2 = models.CharField(max_length=255, blank=True, null=True, help_text="Apartment, Suite, Floor")
    landmark = models.CharField(max_length=100, blank=True, null=True, help_text="Nearby landmark")
    
    # Location details
    pincode = models.CharField(max_length=10, help_text="Postal/ZIP code")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    
    # Geographic coordinates (optional, for delivery optimization)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    
    # Delivery preferences
    delivery_instructions = models.TextField(blank=True, null=True, help_text="Special delivery instructions")
    is_apartment = models.BooleanField(default=False, help_text="Is this an apartment/flat?")
    floor_number = models.CharField(max_length=10, blank=True, null=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['pincode']),
            models.Index(fields=['is_default']),
        ]
        constraints = [
            # Ensure only one default address per user
            models.UniqueConstraint(
                fields=['user'], 
                condition=models.Q(is_default=True),
                name='unique_default_address_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.label} - {self.full_name} ({self.city})"
    
    def save(self, *args, **kwargs):
        # If this is being set as default, unset all other defaults for this user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        
        # If this is the first address for the user, make it default
        elif not Address.objects.filter(user=self.user, is_default=True).exists():
            self.is_default = True
            
        super().save(*args, **kwargs)
    
    def get_full_address(self):
        """Return formatted full address"""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.landmark,
            self.city,
            self.state,
            self.pincode,
            self.country
        ]
        return ', '.join(filter(None, address_parts))
    
    def get_short_address(self):
        """Return shortened address for display"""
        return f"{self.address_line_1}, {self.city} - {self.pincode}"


class PincodeData(models.Model):
    """
    Model to cache pincode data for faster lookups
    """
    pincode = models.CharField(max_length=10, unique=True, primary_key=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    district = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    
    # Delivery information
    is_serviceable = models.BooleanField(default=True)
    delivery_days = models.IntegerField(default=7, help_text="Estimated delivery days")
    cod_available = models.BooleanField(default=True, help_text="Cash on Delivery available")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['pincode']
    
    def __str__(self):
        return f"{self.pincode} - {self.city}, {self.state}"