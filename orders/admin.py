from django.contrib import admin
from .models import Order, OrderItem, OrderStatusUpdate, ZippypostOrder
from django.utils.html import format_html



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
from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem, OrderStatusUpdate


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "user",
        "status",
        "payment_status",
        "payment_method",
        "total_amount",
        "created_at",
        "short_shipping_address",
    )

    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "created_at",
    )

    search_fields = (
        "order_id",
        "user__username",
        "tracking_id",
        "coupon_code",
        "shipping_address__city",
        "shipping_address__pincode",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "order_id",
        "confirmed_at",
        "shipped_at",
        "delivered_at",
        "delivery_shipping_address",
        "delivery_billing_address",
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
                "delivery_shipping_address",
                "billing_address",
                "delivery_billing_address",
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

    # ----------------------------------------------------------
    #  DELIVERY-OPTIMIZED FULL SHIPPING ADDRESS (BLACK TEXT FIX)
    # ----------------------------------------------------------
    def delivery_shipping_address(self, obj):
        addr = obj.shipping_address
        if not addr:
            return "—"

        return format_html(
            f"""
            <div style='line-height:1.7; font-size:14px; padding:10px;
                        border:1px solid #ccc; border-radius:6px;
                        background:#fafafa; color:#000;'>
                <b style='font-size:15px;'>🎯 Shipping Address</b><br>
                <b>Name:</b> {addr.full_name}<br>
                <b>Phone:</b> {addr.phone_number}<br><br>

                <b>Address:</b><br>
                {addr.address_line_1}<br>
                {(addr.address_line_2 or "") + "<br>" if addr.address_line_2 else ""}
                {(addr.landmark or "") + "<br>" if addr.landmark else ""}
                {addr.city}, {addr.state} - {addr.pincode}<br>
                {addr.country}
            </div>
            """
        )

    delivery_shipping_address.short_description = "Full Shipping Address"

    # ----------------------------------------------------------
    #  DELIVERY-OPTIMIZED FULL BILLING ADDRESS (BLACK TEXT FIX)
    # ----------------------------------------------------------
    def delivery_billing_address(self, obj):
        addr = obj.billing_address
        if not addr:
            return "—"

        return format_html(
            f"""
            <div style='line-height:1.7; font-size:14px; padding:10px;
                        border:1px solid #ccc; border-radius:6px;
                        background:#fafafa; color:#000;'>
                <b style='font-size:15px;'>📦 Billing Address</b><br>
                <b>Name:</b> {addr.full_name}<br>
                <b>Phone:</b> {addr.phone_number}<br><br>

                <b>Address:</b><br>
                {addr.address_line_1}<br>
                {(addr.address_line_2 or "") + "<br>" if addr.address_line_2 else ""}
                {(addr.landmark or "") + "<br>" if addr.landmark else ""}
                {addr.city}, {addr.state} - {addr.pincode}<br>
                {addr.country}
            </div>
            """
        )

    delivery_billing_address.short_description = "Full Billing Address"

    # ----------------------------------------------------------
    # SHORT ADDRESS FOR LIST VIEW
    # ----------------------------------------------------------
    def short_shipping_address(self, obj):
        if not obj.shipping_address:
            return "—"
        return obj.shipping_address.get_short_address()

    short_shipping_address.short_description = "Ship To"

    # ----------------------------------------------------------
    # APPLY STATUS FROM INLINE UPDATES
    # ----------------------------------------------------------
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        order = form.instance
        latest_update = order.status_updates.first()

        if latest_update and latest_update.new_status and order.status != latest_update.new_status:
            order.status = latest_update.new_status
            order.save(update_fields=["status"])
            

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
    list_display = ('order', 'old_status', 'new_status', 'created_at', 'updated_by')
    list_filter = ('new_status', 'created_at')
    search_fields = ('order__order_id', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'old_status')

    fields = ('order', 'old_status', 'new_status', 'notes', 'updated_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        # Set updated_by automatically
        if not obj.updated_by:
            obj.updated_by = request.user

        # Save the status update entry FIRST
        super().save_model(request, obj, form, change)

        # Apply status change to Order
        if (
            obj.order
            and obj.new_status
            and obj.order.status != obj.new_status
        ):
            obj.order.status = obj.new_status
            obj.order.save(update_fields=['status'])



admin.site.register(ZippypostOrder)