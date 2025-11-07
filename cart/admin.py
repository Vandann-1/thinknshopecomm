
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (Cart, CartItem)





class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('created_at', 'updated_at', 'get_total_price')
    fields = ('product', 'variant', 'quantity', 'unit_price', 'get_total_price', 'created_at')
    
    def get_total_price(self, obj):
        if obj.pk:
            return f"₹{obj.get_total_price():.2f}"
        return "-"
    get_total_price.short_description = "Total Price"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_info', 'get_items_count', 'get_total_amount', 'is_active', 'last_activity', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_activity')
    search_fields = ('user__username', 'user__email', 'session_key')
    readonly_fields = ('created_at', 'updated_at', 'last_activity', 'get_total_items', 'get_total_amount')
    inlines = [CartItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'session_key', 'is_active')
        }),
        ('Cart Summary', {
            'fields': ('get_total_items', 'get_total_amount'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def get_user_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.username,
                obj.user.email
            )
        return format_html('<em>Guest</em><br><small>{}</small>', obj.session_key)
    get_user_info.short_description = "User"
    
    def get_items_count(self, obj):
        count = obj.get_items_count()
        return format_html('<span class="badge">{}</span>', count)
    get_items_count.short_description = "Items"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('items')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_cart_info', 'product', 'get_variant_info', 'quantity', 'unit_price', 'get_total_price', 'created_at')
    list_filter = ('created_at', 'product__category', 'product__brand')
    search_fields = ('product__name', 'cart__user__username', 'product__sku')
    readonly_fields = ('created_at', 'updated_at', 'get_total_price', 'get_current_price', 'has_price_changed')
    raw_id_fields = ('cart', 'product', 'variant')
    
    fieldsets = (
        (None, {
            'fields': ('cart', 'product', 'variant', 'quantity')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'get_total_price', 'get_current_price', 'has_price_changed'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_cart_info(self, obj):
        user_info = obj.cart.user.username if obj.cart.user else f"Guest ({obj.cart.session_key[:8]}...)"
        return format_html('<strong>Cart #{}</strong><br><small>{}</small>', obj.cart.id, user_info)
    get_cart_info.short_description = "Cart"
    
    def get_variant_info(self, obj):
        if obj.variant:
            return format_html(
                '<span class="color-swatch" style="background-color: {}; width: 12px; height: 12px; display: inline-block; border-radius: 50%; margin-right: 5px;"></span>{} - {}',
                obj.variant.color.hex_code,
                obj.variant.color.name,
                obj.variant.size.name
            )
        return "-"
    get_variant_info.short_description = "Variant"
    
    def get_total_price(self, obj):
        return f"₹{obj.get_total_price():.2f}"
    get_total_price.short_description = "Total"
    
    def get_current_price(self, obj):
        current = obj.get_current_price()
        if obj.has_price_changed():
            return format_html(
                '<span style="color: red;">₹{:.2f}</span>',
                current
            )
        return f"₹{current:.2f}"
    get_current_price.short_description = "Current Price"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'cart__user', 'product', 'variant__color', 'variant__size'
        )

# Optional: Custom admin actions
@admin.action(description='Clear selected carts')
def clear_carts(modeladmin, request, queryset):
    for cart in queryset:
        cart.clear_cart()
    modeladmin.message_user(
        request,
        f"Successfully cleared {queryset.count()} carts."
    )

@admin.action(description='Mark carts as inactive')
def mark_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request,
        f"Successfully marked {updated} carts as inactive."
    )

# Add actions to CartAdmin
CartAdmin.actions = [clear_carts, mark_inactive]