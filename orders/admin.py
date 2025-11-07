from django.contrib import admin
from .models import Order, OrderItem, OrderStatusUpdate


# --- Inline for Order Items ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_details", "unit_price", "quantity", "total_price")
    fields = ("product_name", "variant_details", "quantity", "unit_price", "total_price")


# --- Inline for Order Status Updates ---
class OrderStatusUpdateInline(admin.TabularInline):
    model = OrderStatusUpdate
    extra = 0
    readonly_fields = ("old_status", "new_status", "notes", "updated_by", "created_at")
    fields = ("old_status", "new_status", "notes", "updated_by", "created_at")
    ordering = ("-created_at",)


# --- Order Admin ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "user",
        "status",
        "payment_status",
        "payment_method",
        "subtotal",
        "discount_amount",
        "shipping_cost",
        "tax_amount",
        "total_amount",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "created_at",
    )
    search_fields = ("order_id", "user__username", "tracking_id", "coupon_code")
    ordering = ("-created_at",)
    readonly_fields = (
        "order_id",
        "confirmed_at",
        "shipped_at",
        "delivered_at",
    )
    inlines = [OrderItemInline, OrderStatusUpdateInline]

    fieldsets = (
        ("Order Info", {
            "fields": (
                "order_id",
                "user",
                "status",
                "payment_status",
                "payment_method",
                "payment_reference",
            )
        }),
        ("Pricing", {
            "fields": (
                "subtotal",
                "discount_amount",
                "shipping_cost",
                "tax_amount",
                "total_amount",
                "coupon_code",
            )
        }),
        ("Addresses", {
            "fields": (
                "shipping_address",
                "billing_address",
            )
        }),
        ("Tracking", {
            "fields": (
                "tracking_id",
                "courier_partner",
                "estimated_delivery",
            )
        }),
        ("Timestamps", {
            "fields": (
                "confirmed_at",
                "shipped_at",
                "delivered_at",
            )
        }),
        ("Notes", {
            "fields": ("order_notes",)
        }),
    )


# --- Order Item Admin ---
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "variant_details", "quantity", "unit_price", "total_price")
    list_filter = ("order__status", "product__category")
    search_fields = ("order__order_id", "product_name", "variant_details")
    ordering = ("-created_at",)


# --- Order Status Update Admin ---
@admin.register(OrderStatusUpdate)
class OrderStatusUpdateAdmin(admin.ModelAdmin):
    list_display = ("order", "old_status", "new_status", "updated_by", "created_at")
    list_filter = ("new_status", "created_at")
    search_fields = ("order__order_id", "notes", "updated_by__username")
    ordering = ("-created_at",)
