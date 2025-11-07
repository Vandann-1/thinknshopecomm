from django.contrib import admin
from .models import Discount


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "value",
        "max_discount",
        "min_order_value",
        "start_date",
        "end_date",
        "usage_limit",
        "used_count",
        "is_active",
    )
    list_filter = (
        "discount_type",
        "is_active",
        "start_date",
        "end_date",
    )
    search_fields = ("code",)
    ordering = ("-start_date",)
    readonly_fields = ("used_count",)

    fieldsets = (
        ("Discount Info", {
            "fields": (
                "code",
                "discount_type",
                "value",
                "max_discount",
                "min_order_value",
            )
        }),
        ("Validity", {
            "fields": (
                "start_date",
                "end_date",
                "is_active",
            )
        }),
        ("Usage", {
            "fields": (
                "usage_limit",
                "used_count",
                "applicable_users",
            )
        }),
    )

    def get_queryset(self, request):
        """Optimize query with select_related & prefetch_related"""
        qs = super().get_queryset(request)
        return qs.prefetch_related("applicable_users")

