

# Register your models here.
from django.contrib import admin
from .models import Address, PincodeData


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'user',
        'label',
        'city',
        'state',
        'pincode',
        'address_type',
        'is_default',
        'is_active',
        'created_at',
    )
    
    list_filter = (
        'address_type',
        'is_default',
        'is_active',
        'city',
        'state',
        'country',
    )
    
    search_fields = (
        'full_name',
        'phone_number',
        'address_line_1',
        'address_line_2',
        'landmark',
        'city',
        'state',
        'pincode',
    )
    
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
    )

    ordering = ('-is_default', '-created_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'label', 'address_type', 'is_default', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('full_name', 'phone_number', 'alternate_phone')
        }),
        ('Address Details', {
            'fields': (
                'address_line_1', 'address_line_2', 'landmark',
                'city', 'state', 'pincode', 'country'
            )
        }),
        ('Delivery & Building Details', {
            'fields': ('delivery_instructions', 'is_apartment', 'floor_number')
        }),
        ('Location (Optional)', {
            'fields': ('latitude', 'longitude')
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PincodeData)
class PincodeAdmin(admin.ModelAdmin):
    list_display = (
        'pincode',
        'city',
        'state',
        'country',
        'district',
        'area',
        'is_serviceable',
        'delivery_days',
        'cod_available',
    )

    list_filter = (
        'state',
        'country',
        'is_serviceable',
        'cod_available',
    )

    search_fields = ('pincode', 'city', 'state', 'district', 'area')

    ordering = ('pincode',)

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Location Info', {
            'fields': ('pincode', 'city', 'state', 'country', 'district', 'area')
        }),
        ('Delivery Info', {
            'fields': ('is_serviceable', 'delivery_days', 'cod_available')
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at')
        }),
    )
