from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.urls import reverse
import uuid


class TimestampedModel(models.Model):
    """
    Abstract base model that provides created_at and updated_at timestamps
    for all models that inherit from it.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Category(TimestampedModel):
    """
    Hierarchical category model for organizing products.
    Supports nested categories (parent-child relationships) for better organization.
    Used for navigation, filtering, and SEO purposes.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, help_text="URL-friendly name")
    description = models.TextField(blank=True, help_text="Category description for SEO")
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='subcategories',
        help_text="Parent category for hierarchical structure"
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order")
    meta_title = models.CharField(max_length=60, blank=True, help_text="SEO meta title")
    meta_description = models.CharField(max_length=160, blank=True, help_text="SEO meta description")
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('products:category-detail', kwargs={'slug': self.slug})
    
    def get_all_children(self):
        """Get all descendant categories recursively"""
        children = list(self.subcategories.all())
        for child in self.subcategories.all():
            children.extend(child.get_all_children())
        return children


class Brand(TimestampedModel):
    """
    Brand model for product manufacturers/designers.
    Includes brand information, logos, and metadata for SEO.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True, help_text="Brand's official website")
    is_featured = models.BooleanField(default=False, help_text="Feature on homepage")
    is_active = models.BooleanField(default=True)
    country = models.CharField(max_length=100, blank=True)
    established_year = models.PositiveIntegerField(blank=True, null=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Color(models.Model):
    """
    Color options for product variants.
    Includes both display name and hex code for consistent UI representation.
    """
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, help_text="Color hex code (e.g., #FF5733)")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class Size(models.Model):
    """
    Size options for bottle products.
    Stores simple, customizable volume sizes (default 950ml).
    """

    BOTTLE_CATEGORIES = [
        ('bottle', 'Bottle'),
    ]

    name = models.CharField(max_length=20, default="950ml")  # e.g., 950ml, 750ml, 500ml
    category = models.CharField(max_length=20, choices=BOTTLE_CATEGORIES, default='bottle')
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Bottle volume field (in ml)
    volume_ml = models.PositiveIntegerField(default=950)

    class Meta:
        ordering = ['category', 'sort_order']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.name} ({self.volume_ml}ml)"



class Material(models.Model):
    """
    Fabric/material information for clothing products.
    Important for customer decisions and care instructions.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    care_instructions = models.TextField(blank=True)
    is_eco_friendly = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class Product(TimestampedModel):
    """
    Main product model containing core product information.
    Serves as the parent for all product variants and related data.
    """
    PRODUCT_STATUS = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    ]
    
    GENDER_CHOICES = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('unisex', 'Unisex'),
        ('kids', 'Kids'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    
    # Product Details
    description = models.TextField(help_text="Main product description")
    short_description = models.TextField(max_length=500, blank=True, help_text="Brief description for listings")
    features = models.TextField(blank=True, help_text="Key features and benefits")
    care_instructions = models.TextField(blank=True)
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Cost for profit calculation")
    
    # Product Attributes
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    materials = models.ManyToManyField(Material, blank=True)
    season = models.CharField(max_length=20, blank=True, help_text="Summer, Winter, All Season, etc.")
    occasion = models.CharField(max_length=100, blank=True, help_text="Casual, Formal, Party, etc.")
    
    # Status and Visibility
    status = models.CharField(max_length=20, choices=PRODUCT_STATUS, default='active')
    is_featured = models.BooleanField(default=False, help_text="Feature on homepage")
    is_new_arrival = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    
    # Inventory and Logistics
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Weight in grams")
    dimensions = models.CharField(max_length=100, blank=True, help_text="L x W x H in cm")
    
    # SEO and Marketing---
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags for search")
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    purchase_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            self.sku = f"PRD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        # return reverse('/', kwargs={'slug': self.slug})
        pass
        
    
    def get_discount_percent(self):
        """Calculate discount percentage"""
        if self.discounted_price and self.discounted_price < self.base_price:
            return round((1 - self.discounted_price / self.base_price) * 100, 2)
        return 0
    
    def get_effective_price(self):
        """Get the current selling price"""
        return self.discounted_price if self.discounted_price else self.base_price
    
    def get_total_stock(self):
        """Get total stock across all variants"""
        return sum(variant.stock for variant in self.variants.all())
    
    def is_in_stock(self):
        """Check if product has any stock available"""
        return self.get_total_stock() > 0
    
    def get_available_colors(self):
        """Get all colors available for this product"""
        return Color.objects.filter(productvariant__product=self).distinct()
    
    def get_available_sizes(self):
        """Get all sizes available for this product"""
        return Size.objects.filter(productvariant__product=self).distinct()
    
    def get_primary_image(self):
        """Get the primary image URL with fallback strategy"""
        # Primary gallery image
        primary_gallery = self.gallery.filter(is_primary=True).first()
        if primary_gallery and primary_gallery.image:
            return primary_gallery.image.url
        
        # First gallery image
        first_gallery = self.gallery.first()
        if first_gallery and first_gallery.image:
            return first_gallery.image.url
        
        # First variant image
        first_variant = self.variants.filter(is_active=True, image__isnull=False).first()
        if first_variant and first_variant.image:
            return first_variant.image.url
        
        return None


class ProductVariant(TimestampedModel):
    """
    Product variants represent different combinations of color, size for a product.
    Each variant has its own pricing, stock, and images.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    
    # Variant-specific details
    sku = models.CharField(max_length=50, unique=True, help_text="Variant-specific SKU")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    
    # Inventory
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0, help_text="Stock reserved in pending orders")
    low_stock_threshold = models.PositiveIntegerField(default=5)
    
    # Variant image
    image = models.ImageField(upload_to='products/variants/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['product', 'color', 'size']
        ordering = ['color__sort_order', 'size__sort_order']
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.color.name} - {self.size.name}"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{self.product.sku}-{self.color.name[:3].upper()}-{self.size.name}"
        super().save(*args, **kwargs)
    
    def get_effective_price(self):
        """Get the current selling price for this variant"""
        return self.discounted_price if self.discounted_price else self.price
    
    def get_available_stock(self):
        """Get available stock (total - reserved)"""
        return max(0, self.stock - self.reserved_stock)
    
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.get_available_stock() <= self.low_stock_threshold
    
    def is_in_stock(self):
        """Check if variant is in stock"""
        return self.get_available_stock() > 0


class ProductGallery(models.Model):
    """
    Product image gallery supporting multiple images per product.
    Can be associated with specific colors for color-specific images.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Alt text for SEO and accessibility")
    color = models.ForeignKey(Color, null=True, blank=True, on_delete=models.SET_NULL, help_text="Color-specific image")
    is_primary = models.BooleanField(default=False, help_text="Primary product image")
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
    
    def __str__(self):
        return f"{self.product.name} - Image {self.id}"


class ProductReview(TimestampedModel):
    """
    Customer reviews and ratings for products.
    Includes verification status and helpfulness voting.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, help_text="Specific variant reviewed")
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    review_text = models.TextField()
    
    # Review attributes
    is_verified_purchase = models.BooleanField(default=False, help_text="Customer bought this product")
    is_approved = models.BooleanField(default=True)
    
    # Helpfulness voting
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"
    
    def get_helpfulness_ratio(self):
        """Calculate helpfulness ratio"""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100


class ProductQuestion(TimestampedModel):
    """
    Customer questions about products with answers from sellers/moderators.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField(blank=True)
    answered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='answered_questions')
    answered_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Question by {self.user.username} for {self.product.name}"
    
    @property
    def is_answered(self):
        return bool(self.answer)


class StockMovement(TimestampedModel):
    """
    Track stock movements for inventory management and auditing.
    Records all stock changes with reasons and references.
    """
    MOVEMENT_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('reserved', 'Reserved'),
        ('released', 'Released'),
    ]
    
    MOVEMENT_REASONS = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('damage', 'Damage'),
        ('lost', 'Lost'),
        ('adjustment', 'Stock Adjustment'),
        ('reservation', 'Order Reservation'),
        ('cancellation', 'Order Cancellation'),
    ]
    
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    reason = models.CharField(max_length=20, choices=MOVEMENT_REASONS)
    quantity = models.IntegerField()  # Can be negative for outgoing stock
    reference_id = models.CharField(max_length=100, blank=True, help_text="Order ID, Invoice ID, etc.")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.variant} - {self.movement_type} - {self.quantity}"


class Wishlist(TimestampedModel):
    """
    User wishlist for saving favorite products.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, help_text="Specific variant wishlisted")
    
    class Meta:
        unique_together = ['user', 'product', 'variant']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s wishlist - {self.product.name}"


class RecentlyViewed(models.Model):
    """
    Track recently viewed products by users for personalized recommendations.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recently_viewed')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"


class Collection(TimestampedModel):
    """
    Curated product collections for marketing and promotions.
    Examples: "Summer Collection", "Wedding Special", "Trending Now"
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='collections/', blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='collections', blank=True)
    
    # Display settings
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    class Meta:
        ordering = ['sort_order', '-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductAttribute(models.Model):
    """
    Additional flexible attributes for products.
    Examples: "Sleeve Length", "Neckline", "Pattern", "Fit Type"
    """
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    is_required = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.display_name or self.name


class ProductAttributeValue(models.Model):
    """
    Values for product attributes.
    Examples: "Full Sleeve", "V-Neck", "Striped", "Slim Fit"
    """
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['attribute', 'value']
        ordering = ['sort_order', 'value']
    
    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductAttributeMapping(models.Model):
    """
    Maps products to their attribute values.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attribute_mappings')
    attribute_value = models.ForeignKey(ProductAttributeValue, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['product', 'attribute_value']
    
    def __str__(self):
        return f"{self.product.name} - {self.attribute_value}"
    



