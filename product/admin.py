from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Avg, Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Brand, Color, Size, Material, Product, ProductVariant,
    ProductGallery, ProductReview, ProductQuestion, StockMovement,
    Wishlist, RecentlyViewed, Collection, ProductAttribute,
    ProductAttributeValue, ProductAttributeMapping
)


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class ProductVariantInline(admin.TabularInline):
    """
    Inline admin for managing product variants within the product admin page.
    Allows quick creation and editing of color/size combinations.
    """
    model = ProductVariant
    extra = 1
    fields = ('color', 'size', 'price', 'discounted_price', 'stock', 'is_active', 'image')
    readonly_fields = ('sku',)
    show_change_link = True


class ProductGalleryInline(admin.TabularInline):
    """
    Inline admin for managing product images within the product admin page.
    """
    model = ProductGallery
    extra = 2
    fields = ('image', 'alt_text', 'color', 'is_primary', 'sort_order')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px;"/>', obj.image.url)
        return "No image"
    image_preview.short_description = "Preview"


class ProductAttributeMappingInline(admin.TabularInline):
    """
    Inline admin for managing product attributes within the product admin page.
    """
    model = ProductAttributeMapping
    extra = 1
    fields = ('attribute_value',)
    verbose_name = "Product Attribute"
    verbose_name_plural = "Product Attributes"


class ProductAttributeValueInline(admin.TabularInline):
    """
    Inline admin for managing attribute values within the attribute admin page.
    """
    model = ProductAttributeValue
    extra = 2
    fields = ('value', 'sort_order')


class SubCategoryInline(admin.TabularInline):
    """
    Inline admin for managing subcategories within the category admin page.
    """
    model = Category
    extra = 1
    fields = ('name', 'slug', 'is_active', 'sort_order')
    show_change_link = True


class StockMovementInline(admin.TabularInline):
    """
    Inline admin for viewing stock movements within the product variant admin page.
    """
    model = StockMovement
    extra = 0
    fields = ('movement_type', 'reason', 'quantity', 'reference_id', 'notes', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False


# ============================================================================
# CORE MODEL ADMIN CLASSES
# ============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for managing product categories.
    Supports hierarchical display and bulk operations.
    """
    list_display = ('name', 'parent', 'product_count', 'is_active', 'sort_order', 'created_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'sort_order')
    list_per_page = 50
    inlines = [SubCategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'parent')
        }),
        ('Display Settings', {
            'fields': ('image', 'is_active', 'sort_order')
        }),
        ('SEO Settings', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def product_count(self, obj):
        """Display number of products in this category"""
        count = obj.products.count()
    #     if count > 0:
    #         url = reverse('admin:your_app_product_changelist') + f'?category__id__exact={obj.id}'
    #         return format_html('<a href="{}">{} products</a>', url, count)
    #     return count
    # product_count.short_description = 'Products'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """
    Admin interface for managing brands.
    """
    list_display = ('name', 'logo_preview', 'product_count', 'is_featured', 'is_active', 'country', 'created_at')
    list_filter = ('is_featured', 'is_active', 'country', 'created_at')
    search_fields = ('name', 'description', 'country')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_featured', 'is_active')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'logo')
        }),
        ('Brand Details', {
            'fields': ('website_url', 'country', 'established_year')
        }),
        ('Display Settings', {
            'fields': ('is_featured', 'is_active')
        })
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height: 40px;"/>', obj.logo.url)
        return "No logo"
    logo_preview.short_description = 'Logo'
    
    def product_count(self, obj):
        count = obj.products.count()
        # if count > 0:
            # url = reverse('admin:your_app_product_changelist') + f'?brand__id__exact={obj.id}'
            # return format_html('<a href="{}">{} products</a>', url, count)
        # return count
    # product_count.short_description = 'Products'


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    """
    Admin interface for managing colors.
    """
    list_display = ('name', 'color_preview', 'hex_code', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('name', 'hex_code')
    list_editable = ('is_active', 'sort_order')
    ordering = ('sort_order', 'name')
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.hex_code
        )
    color_preview.short_description = 'Color'


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    """
    Admin interface for managing sizes.
    """
    list_display = ('name', 'category', 'chest', 'waist', 'hip', 'is_active', 'sort_order')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active', 'sort_order')
    ordering = ('category', 'sort_order')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'sort_order', 'is_active')
        }),
        ('Size Chart (cm)', {
            'fields': ('chest', 'waist', 'hip', 'length'),
            'classes': ('collapse',)
        })
    )




@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Main admin interface for managing products.
    Comprehensive interface with inlines for variants, images, and attributes.
    """
    list_display = (
        'name', 'sku', 'brand', 'category', 'gender', 'status', 
        'base_price', 'discount_percent', 'total_stock', 'is_featured', 'created_at'
    )
    list_filter = (
        'status', 'gender', 'category', 'brand', 'is_featured', 
        'is_new_arrival', 'is_bestseller', 'created_at'
    )
    search_fields = ('name', 'sku', 'description', 'tags')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('status', 'is_featured')
    date_hierarchy = 'created_at'
    list_per_page = 25
    
    inlines = [ProductVariantInline, ProductGalleryInline, ProductAttributeMappingInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category', 'brand')
        }),
        ('Product Details', {
            'fields': ('description', 'short_description', 'features', 'care_instructions')
        }),
        ('Pricing', {
            'fields': ('base_price', 'discounted_price', 'cost_price')
        }),
        ('Product Attributes', {
            'fields': ('gender', 'materials', 'season', 'occasion')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'is_featured', 'is_new_arrival', 'is_bestseller')
        }),
        ('Physical Properties', {
            'fields': ('weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'purchase_count'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('view_count', 'purchase_count', 'created_at', 'updated_at')
    
    # Custom admin actions
    actions = ['make_active', 'make_inactive', 'mark_as_featured', 'unmark_as_featured']
    
    def discount_percent(self, obj):
        discount = obj.get_discount_percent()
        if discount > 0:
            return format_html('<span style="color: green;">{}%</span>', discount)
        return '-'
    discount_percent.short_description = 'Discount'
    
    def total_stock(self, obj):
        stock = obj.get_total_stock()
        if stock == 0:
            return format_html('<span style="color: red;">{}</span>', stock)
        elif stock <= 10:
            return format_html('<span style="color: orange;">{}</span>', stock)
        return stock
    total_stock.short_description = 'Stock'
    
    # Admin Actions
    def make_active(self, request, queryset):
        queryset.update(status='active')
    make_active.short_description = "Mark selected products as active"
    
    def make_inactive(self, request, queryset):
        queryset.update(status='discontinued')
    make_inactive.short_description = "Mark selected products as inactive"
    
    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = "Mark selected products as featured"
    
    def unmark_as_featured(self, request, queryset):
        queryset.update(is_featured=False)
    unmark_as_featured.short_description = "Remove featured status"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Admin interface for managing individual product variants.
    """
    list_display = (
        'product', 'color', 'size', 'sku', 'price', 'discounted_price',
        'stock', 'available_stock', 'low_stock_warning', 'is_active'
    )
    list_filter = ('product__category', 'product__brand', 'color', 'size', 'is_active')
    search_fields = ('product__name', 'sku', 'product__sku')
    list_editable = ('price', 'discounted_price', 'stock', 'is_active')
    readonly_fields = ('sku', 'created_at', 'updated_at')
    
    inlines = [StockMovementInline]
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product', 'color', 'size', 'sku')
        }),
        ('Pricing', {
            'fields': ('price', 'discounted_price')
        }),
        ('Inventory', {
            'fields': ('stock', 'reserved_stock', 'low_stock_threshold')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def available_stock(self, obj):
        stock = obj.get_available_stock()
        if stock == 0:
            return format_html('<span style="color: red;">{}</span>', stock)
        elif obj.is_low_stock():
            return format_html('<span style="color: orange;">{}</span>', stock)
        return stock
    available_stock.short_description = 'Available Stock'
    
    def low_stock_warning(self, obj):
        if obj.is_low_stock() and obj.is_in_stock():
            return format_html('<span style="color: orange;">⚠️ Low Stock</span>')
        elif not obj.is_in_stock():
            return format_html('<span style="color: red;">❌ Out of Stock</span>')
        return format_html('<span style="color: green;">✅ In Stock</span>')
    low_stock_warning.short_description = 'Stock Status'


@admin.register(ProductGallery)
class ProductGalleryAdmin(admin.ModelAdmin):
    """
    Admin interface for managing product images.
    """
    list_display = ('product', 'image_preview', 'color', 'is_primary', 'sort_order')
    list_filter = ('product__category', 'color', 'is_primary')
    search_fields = ('product__name', 'alt_text')
    list_editable = ('is_primary', 'sort_order')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px;"/>', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


# ============================================================================
# REVIEW & CUSTOMER INTERACTION ADMIN CLASSES
# ============================================================================

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for managing product reviews.
    """
    list_display = (
        'product', 'user', 'rating', 'title', 'is_verified_purchase',
        'is_approved', 'helpful_count', 'created_at'
    )
    list_filter = ('rating', 'is_verified_purchase', 'is_approved', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'review_text')
    list_editable = ('is_approved',)
    readonly_fields = ('helpful_count', 'not_helpful_count', 'created_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'user', 'variant', 'rating')
        }),
        ('Review Content', {
            'fields': ('title', 'review_text')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved')
        }),
        ('Statistics', {
            'fields': ('helpful_count', 'not_helpful_count'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing product Q&A.
    """
    list_display = (
        'product', 'user', 'question_preview', 'is_answered',
        'answered_by', 'is_public', 'created_at'
    )
    list_filter = ('is_public', 'answered_at', 'created_at')
    search_fields = ('product__name', 'user__username', 'question', 'answer')
    readonly_fields = ('created_at', 'updated_at')
    
    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'
    
    def is_answered(self, obj):
        if obj.is_answered:
            return format_html('<span style="color: green;">✅ Answered</span>')
        return format_html('<span style="color: red;">❌ Pending</span>')
    is_answered.short_description = 'Status'


# ============================================================================
# INVENTORY & ANALYTICS ADMIN CLASSES
# ============================================================================

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """
    Admin interface for tracking inventory movements.
    """
    list_display = (
        'variant', 'movement_type', 'reason', 'quantity',
        'reference_id', 'created_by', 'created_at'
    )
    list_filter = ('movement_type', 'reason', 'created_at')
    search_fields = ('variant__product__name', 'variant__sku', 'reference_id', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of stock movements for audit trail
        return False


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing customer wishlists.
    """
    list_display = ('user', 'product', 'variant', 'created_at')
    list_filter = ('created_at', 'product__category', 'product__brand')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RecentlyViewed)
class RecentlyViewedAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing customer browsing history.
    """
    list_display = ('user', 'product', 'viewed_at')
    list_filter = ('viewed_at', 'product__category')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('viewed_at',)


# ============================================================================
# MARKETING & COLLECTIONS ADMIN CLASSES
# ============================================================================

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing product collections.
    """
    list_display = ('name', 'product_count', 'is_active', 'is_featured', 'sort_order', 'created_at')
    list_filter = ('is_active', 'is_featured', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'is_featured', 'sort_order')
    filter_horizontal = ('products',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Products', {
            'fields': ('products',)
        }),
        ('Display Settings', {
            'fields': ('is_active', 'is_featured', 'sort_order')
        }),
        ('SEO Settings', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        })
    )
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


# ============================================================================
# ATTRIBUTE SYSTEM ADMIN CLASSES
# ============================================================================

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    """
    Admin interface for managing product attributes.
    """
    list_display = ('name', 'display_name', 'is_required', 'is_filterable', 'sort_order')
    list_editable = ('is_required', 'is_filterable', 'sort_order')
    search_fields = ('name', 'display_name')
    inlines = [ProductAttributeValueInline]


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    """
    Admin interface for managing attribute values.
    """
    list_display = ('attribute', 'value', 'sort_order')
    list_filter = ('attribute',)
    search_fields = ('attribute__name', 'value')
    list_editable = ('sort_order',)


# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

# Customize the admin site header and title
admin.site.site_header = "Skatezo Admin Panel"
admin.site.site_title = "Skatezo-Commerce Admin"
admin.site.index_title = "Welcome to Skatezo Administration"

