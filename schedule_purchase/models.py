from django.db import models
from product.models import *
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
# Create your models here.


class FuturePurchase(TimestampedModel):
    """
    Model to store user's future purchase plans with scheduling and automation options.
    Supports email reminders and automatic purchase execution.
    """
    FREQUENCY_CHOICES = [
        ('once', 'One Time'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    ACTION_CHOICES = [
        ('reminder', 'Email Reminder Only'),
        ('auto_purchase', 'Automatic Purchase'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # User and Product Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='future_purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='future_purchases')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, 
                               help_text="Specific variant to purchase")
    
    # Purchase Details
    title = models.CharField(max_length=255, help_text="Custom title for this future purchase")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                   help_text="Maximum price willing to pay")
    notes = models.TextField(blank=True, help_text="Personal notes or special instructions")
    
    # Scheduling Configuration
    scheduled_date = models.DateTimeField(help_text="When to execute this purchase")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='once')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, default='reminder')
    
    # Reminder Settings
    reminder_days_before = models.PositiveIntegerField(default=1, 
                                                      help_text="Days before scheduled date to send reminder")
    send_reminder_email = models.BooleanField(default=True)
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Auto Purchase Settings
    auto_purchase_enabled = models.BooleanField(default=False)
    check_stock_availability = models.BooleanField(default=True, 
                                                  help_text="Check if product is in stock before purchase")
    use_default_address = models.BooleanField(default=True)
    shipping_address = models.TextField(blank=True, help_text="Custom shipping address if not using default")
    
    # Status and Control
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)
    
    # Execution Tracking
    last_executed_at = models.DateTimeField(null=True, blank=True)
    next_execution_date = models.DateTimeField(null=True, blank=True)
    execution_count = models.PositiveIntegerField(default=0)
    max_executions = models.PositiveIntegerField(null=True, blank=True, 
                                               help_text="Maximum times to execute (for recurring)")
    
    # Failure Handling
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    last_error_message = models.TextField(blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    
    # Budget and Limits
    budget_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     help_text="Monthly/Total budget limit for this item")
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ['scheduled_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['scheduled_date', 'is_active']),
            models.Index(fields=['next_execution_date']),
            models.Index(fields=['status', 'action_type']),
        ]
        verbose_name = "Future Purchase"
        verbose_name_plural = "Future Purchases"
    
    def __str__(self):
        return f"{self.user.username} - {self.title or self.product.name} - {self.scheduled_date.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        # Set title if not provided
        if not self.title:
            variant_info = f" ({self.variant.color.name} - {self.variant.size.name})" if self.variant else ""
            self.title = f"{self.product.name}{variant_info}"
        
        # Set next execution date for recurring purchases
        if self.frequency != 'once' and not self.next_execution_date:
            self.next_execution_date = self.scheduled_date
            
        super().save(*args, **kwargs)
    
    def get_estimated_total(self):
        """Calculate estimated total cost including quantity"""
        if self.variant:
            price = self.variant.get_effective_price()
        else:
            price = self.product.get_effective_price()
        return price * self.quantity
    
    def is_within_budget(self):
        """Check if purchase is within budget limits"""
        if not self.budget_limit:
            return True
        estimated_total = self.get_estimated_total()
        return (self.spent_amount + estimated_total) <= self.budget_limit
    
    def can_execute(self):
        """Check if purchase can be executed"""
        if not self.is_active or self.status != 'active':
            return False, "Purchase is not active"
        
        if not self.is_within_budget():
            return False, "Budget limit exceeded"
        
        if self.max_executions and self.execution_count >= self.max_executions:
            return False, "Maximum executions reached"
        
        if self.max_price and self.get_estimated_total() > self.max_price:
            return False, "Price exceeds maximum limit"
        
        if self.check_stock_availability:
            if self.variant and not self.variant.is_in_stock():
                return False, "Variant out of stock"
            elif not self.variant and not self.product.is_in_stock():
                return False, "Product out of stock"
        
        return True, "Ready to execute"
    
    def get_next_execution_date(self):
        """Calculate next execution date based on frequency"""
        if self.frequency == 'once':
            return None
        
        base_date = self.last_executed_at or self.scheduled_date
        
        if self.frequency == 'weekly':
            return base_date + timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            return base_date + timedelta(weeks=2)
        elif self.frequency == 'monthly':
            return base_date + timedelta(days=30)
        elif self.frequency == 'quarterly':
            return base_date + timedelta(days=90)
        elif self.frequency == 'yearly':
            return base_date + timedelta(days=365)
        
        return None
    
    def should_send_reminder(self):
        """Check if reminder should be sent"""
        if not self.send_reminder_email or self.reminder_sent:
            return False
        
        reminder_date = self.scheduled_date - timedelta(days=self.reminder_days_before)
        return timezone.now() >= reminder_date
    
    def mark_reminder_sent(self):
        """Mark reminder as sent"""
        self.reminder_sent = True
        self.reminder_sent_at = timezone.now()
        self.save(update_fields=['reminder_sent', 'reminder_sent_at'])
    
    def mark_executed(self, success=True, error_message=None):
        """Mark purchase as executed"""
        self.last_executed_at = timezone.now()
        self.execution_count += 1
        
        if success:
            self.retry_count = 0
            self.last_error_message = ""
            
            # Update next execution for recurring purchases
            if self.frequency != 'once':
                self.next_execution_date = self.get_next_execution_date()
                
                # Mark as completed if max executions reached
                if self.max_executions and self.execution_count >= self.max_executions:
                    self.status = 'completed'
            else:
                self.status = 'completed'
        else:
            self.retry_count += 1
            self.last_error_message = error_message or "Unknown error"
            self.last_error_at = timezone.now()
            
            if self.retry_count >= self.max_retries:
                self.status = 'failed'
        
        self.save()


class FuturePurchaseLog(TimestampedModel):
    """
    Log model to track all activities related to future purchases.
    Includes execution attempts, reminders sent, status changes, etc.
    """
    ACTION_TYPES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('reminder_sent', 'Reminder Sent'),
        ('execution_attempted', 'Execution Attempted'),
        ('execution_successful', 'Execution Successful'),
        ('execution_failed', 'Execution Failed'),
        ('paused', 'Paused'),
        ('resumed', 'Resumed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    future_purchase = models.ForeignKey(FuturePurchase, on_delete=models.CASCADE, related_name='logs')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    message = models.TextField(help_text="Detailed message about the action")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional data in JSON format")
    
    # Reference to related objects
    order_id = models.CharField(max_length=100, blank=True, help_text="Order ID if purchase was successful")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['future_purchase', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.future_purchase.title} - {self.get_action_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class FuturePurchaseReminder(TimestampedModel):
    """
    Model to track reminder configurations and history.
    Supports multiple reminder types and channels.
    """
    REMINDER_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    future_purchase = models.ForeignKey(FuturePurchase, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES, default='email')
    scheduled_for = models.DateTimeField(help_text="When to send this reminder")
    
    # Content
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    template_name = models.CharField(max_length=100, blank=True, help_text="Email template to use")
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Configuration
    is_recurring = models.BooleanField(default=False)
    recurring_interval_days = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['scheduled_for', 'status']),
            models.Index(fields=['future_purchase', 'reminder_type']),
        ]
    
    def __str__(self):
        return f"Reminder for {self.future_purchase.title} - {self.scheduled_for.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_sent(self):
        """Mark reminder as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_failed(self, error_message):
        """Mark reminder as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])