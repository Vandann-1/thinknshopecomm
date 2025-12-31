from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max, Count, Avg,When,Case
from django.http import JsonResponse
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from .models import (
    Product, Category, Brand, Color, Size, Material, 
    ProductVariant, Collection, ProductAttribute, ProductAttributeValue,ProductReview
)
from django.db.models import (
    Q, F, Case, When, Value, Count, Avg, Min, Max, 
    DecimalField, FloatField, IntegerField,Sum
)
from .models import *
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, F,When,Value
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import logging
from .utils import (get_additional_homepage_context)
logger = logging.getLogger(__name__)
from django.views.decorators.cache import cache_page
from django.db.models.functions import Coalesce
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
# Homepage View =======================================================================================================================================================================
"""
1 )  HomePage - Displays Initial Categories , Brands , New Arrivals ETC - No Login Required For Exploring
The Products
"""

class HomePageView(ListView):
    """
    Enhanced homepage displaying featured categories, brands, collections and products
    with additional features like trending products, price ranges, and reviews
    """
    template_name = 'products/list/home.html'
    context_object_name = 'featured_products'
    paginate_by = 8  # For featured products pagination
    
    def get_queryset(self):
        return Product.objects.filter(
            status='active', 
            is_featured=True
        ).select_related('brand', 'category').prefetch_related('gallery')[:8]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured categories with product counts
        context['featured_categories'] = Category.objects.filter(
            is_active=True,
            parent__isnull=True  # Only parent categories
        ).prefetch_related('subcategories').annotate(
            product_count=models.Count('products', filter=models.Q(products__status='active'))
        )[:8]
        
        # Featured brands with product counts
        context['featured_brands'] = Brand.objects.filter(
            is_active=True,
            is_featured=True
        ).annotate(
            product_count=models.Count('products', filter=models.Q(products__status='active'))
        )[:12]
        
        # Featured collections
        context['featured_collections'] = Collection.objects.filter(
            is_active=True,
            is_featured=True
        ).prefetch_related('products')[:6]
        
        # New arrivals (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['new_arrivals'] = Product.objects.filter(
            status='active',
            is_new_arrival=True,
            created_at__gte=thirty_days_ago
        ).select_related('brand', 'category').prefetch_related('gallery')[:8]
        
        # Bestsellers with purchase count
        context['bestsellers'] = Product.objects.filter(
            status='active',
            is_bestseller=True
        ).select_related('brand', 'category').prefetch_related('gallery').order_by('-purchase_count')[:8]
        
        # Trending products (most viewed in last 7 days)
        context['trending_products'] = Product.objects.filter(
            status='active',
            recentlyviewed__viewed_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('brand', 'category').prefetch_related('gallery').annotate(
            recent_views=models.Count('recentlyviewed')
        ).order_by('-recent_views')[:8]
        
        # Products on sale (with discounts)
        context['sale_products'] = Product.objects.filter(
            status='active',
            discounted_price__isnull=False,
            discounted_price__lt=models.F('base_price')
        ).select_related('brand', 'category').prefetch_related('gallery')[:8]
        
        # Top rated products (with reviews)
        context['top_rated_products'] = Product.objects.filter(
            status='active',
            reviews__isnull=False
        ).select_related('brand', 'category').prefetch_related('gallery').annotate(
            avg_rating=models.Avg('reviews__rating'),
            review_count=models.Count('reviews')
        ).filter(
            avg_rating__gte=4.0,
            review_count__gte=5
        ).order_by('-avg_rating', '-review_count')[:8]
        
        # Recently restocked products - Fixed query
        try:
            # Method 1: Using StockMovement model directly if it exists
            from .models import StockMovement 
            recent_stock_movements = StockMovement.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7),
                movement_type='in'
            ).values_list('variant_id', flat=True)
            
            context['restocked_products'] = Product.objects.filter(
                status='active',
                variants__id__in=recent_stock_movements,
                variants__stock__gt=0
            ).select_related('brand', 'category').prefetch_related('gallery').distinct()[:8]
        except ImportError:
            # Method 2: Fallback - get products with good stock levels
            context['restocked_products'] = Product.objects.filter(
                status='active',
                variants__stock__gt=10  # Products with decent stock
            ).select_related('brand', 'category').prefetch_related('gallery').distinct()[:8]
        
        # Limited stock products (urgency)
        context['limited_stock_products'] = Product.objects.filter(
            status='active',
            variants__stock__lte=models.F('variants__low_stock_threshold'),
            variants__stock__gt=0
        ).select_related('brand', 'category').prefetch_related('gallery').distinct()[:8]
        
        # Gender-specific sections
        context['mens_products'] = Product.objects.filter(
            status='active',
            gender='men'
        ).select_related('brand', 'category').prefetch_related('gallery')[:6]
        
        context['womens_products'] = Product.objects.filter(
            status='active',
            gender='women'
        ).select_related('brand', 'category').prefetch_related('gallery')[:6]
        
        context['kids_products'] = Product.objects.filter(
            status='active',
            gender='kids'
        ).select_related('brand', 'category').prefetch_related('gallery')[:6]
        
        # Seasonal products
        current_season = self.get_current_season()
        context['seasonal_products'] = Product.objects.filter(
            status='active',
            season__icontains=current_season
        ).select_related('brand', 'category').prefetch_related('gallery')[:8]
        
        # Price range categories
        context['budget_products'] = Product.objects.filter(
            status='active'
        ).annotate(
            effective_price=models.Case(
                models.When(discounted_price__isnull=False, then='discounted_price'),
                default='base_price'
            )
        ).filter(effective_price__lte=50).select_related('brand', 'category').prefetch_related('gallery')[:8]
        
        context['premium_products'] = Product.objects.filter(
            status='active'
        ).annotate(
            effective_price=models.Case(
                models.When(discounted_price__isnull=False, then='discounted_price'),
                default='base_price'
            )
        ).filter(effective_price__gte=200).select_related('brand', 'category').prefetch_related('gallery')[:8]
        
        # Recently reviewed products
        context['recently_reviewed_products'] = Product.objects.filter(
            status='active',
            reviews__created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('brand', 'category').prefetch_related('gallery', 'reviews').distinct()[:8]
        
        # Eco-friendly products
        context['eco_friendly_products'] = Product.objects.filter(
            status='active',
            materials__is_eco_friendly=True
        ).select_related('brand', 'category').prefetch_related('gallery').distinct()[:8]
        
        # Statistics for homepage
        context['stats'] = {
            'total_products': Product.objects.filter(status='active').count(),
            'total_brands': Brand.objects.filter(is_active=True).count(),
            'total_categories': Category.objects.filter(is_active=True).count(),
            # 'happy_customers': User.objects.filter(orders__isnull=False).distinct().count(),
            'happy_customers':200,
        }
        
        # Recent customer reviews (for testimonials)
        context['recent_reviews'] = ProductReview.objects.filter(
            is_approved=True,
            rating__gte=4
        ).select_related('user', 'product').order_by('-created_at')[:6]
        
        # Available colors and sizes for quick filters
        context['popular_colors'] = Color.objects.filter(
            is_active=True,
            productvariant__product__status='active'
        ).annotate(
            product_count=models.Count('productvariant__product', distinct=True)
        ).order_by('-product_count')[:10]
        
        context['popular_sizes'] = Size.objects.filter(
            is_active=True,
            productvariant__product__status='active'
        ).annotate(
            product_count=models.Count('productvariant__product', distinct=True)
        ).order_by('-product_count')[:10]

        # Additional Context
        try:
            context.update(self.get_additional_homepage_context())
        except (NameError, AttributeError):
            # Function doesn't exist, skip
            pass
        
        return context
    
    def get_current_season(self):
        """Determine current season based on month"""
        current_month = timezone.now().month
        if current_month in [12, 1, 2]:
            return 'Winter'
        elif current_month in [3, 4, 5]:
            return 'Spring'
        elif current_month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Fall'

    def get_additional_homepage_context(self):
        """Get additional context for homepage features"""
        
        # Price range analysis
        price_ranges = self.get_price_range_analysis()
        
        # Inventory alerts for admin (if user is staff)
        inventory_alerts = self.get_inventory_alerts() if self.request.user.is_staff else None
        
        # Recently viewed products for logged-in users
        user_recommendations = self.get_user_recommendations() if self.request.user.is_authenticated else None
        
        # Product categories with images
        categories_with_products = self.get_categories_with_featured_products()
        
        # Brand performance metrics
        brand_metrics = self.get_brand_performance_metrics()
        
        return {
            'price_ranges': price_ranges,
            'inventory_alerts': inventory_alerts,
            'user_recommendations': user_recommendations,
            'categories_with_products': categories_with_products,
            'brand_metrics': brand_metrics,
            'homepage_widgets': self.get_homepage_widgets(),
        }
    
    def get_price_range_analysis(self):
        """Analyze products by price ranges"""
        return {
            'under_25': Product.objects.filter(
                status='active'
            ).annotate(
                effective_price=Case(
                    When(discounted_price__isnull=False, then='discounted_price'),
                    default='base_price'
                )
            ).filter(effective_price__lt=25).count(),
            
            'range_25_50': Product.objects.filter(
                status='active'
            ).annotate(
                effective_price=Case(
                    When(discounted_price__isnull=False, then='discounted_price'),
                    default='base_price'
                )
            ).filter(effective_price__gte=25, effective_price__lt=50).count(),
            
            'range_50_100': Product.objects.filter(
                status='active'
            ).annotate(
                effective_price=Case(
                    When(discounted_price__isnull=False, then='discounted_price'),
                    default='base_price'
                )
            ).filter(effective_price__gte=50, effective_price__lt=100).count(),
            
            'over_100': Product.objects.filter(
                status='active'
            ).annotate(
                effective_price=Case(
                    When(discounted_price__isnull=False, then='discounted_price'),
                    default='base_price'
                )
            ).filter(effective_price__gte=100).count(),
        }
    
    def get_inventory_alerts(self):
        """Get inventory alerts for staff users"""
        return {
            'low_stock_variants': ProductVariant.objects.filter(
                is_active=True,
                stock__lte=F('low_stock_threshold'),
                stock__gt=0
            ).select_related('product', 'color', 'size')[:10],
            
            'out_of_stock_products': Product.objects.filter(
                status='active'
            ).annotate(
                total_stock=models.Sum('variants__stock')
            ).filter(total_stock=0)[:10],
            
            'products_needing_restock': ProductVariant.objects.filter(
                is_active=True,
                stock=0
            ).select_related('product')[:10],
        }
    
    def get_user_recommendations(self):
        """Get personalized recommendations for logged-in users"""
        user = self.request.user
        
        # Get user's recently viewed products
        recently_viewed = RecentlyViewed.objects.filter(
            user=user
        ).select_related('product')[:10]
        
        # Get user's wishlist
        wishlist_items = Wishlist.objects.filter(
            user=user
        ).select_related('product')[:10]
        
        # Get recommendations based on user's purchase history
        # (This would require Order models which aren't in your current models)
        
        # Get similar products based on recently viewed categories
        viewed_categories = recently_viewed.values_list('product__category', flat=True)
        similar_products = Product.objects.filter(
            status='active',
            category__in=viewed_categories
        ).exclude(
            id__in=recently_viewed.values_list('product_id', flat=True)
        ).select_related('brand', 'category')[:8]
        
        return {
            'recently_viewed': recently_viewed,
            'wishlist_items': wishlist_items,
            'similar_products': similar_products,
        }
    
    def get_categories_with_featured_products(self):
        """Get categories with their featured products"""
        categories = []
        for category in Category.objects.filter(is_active=True, parent__isnull=True)[:6]:
            featured_products = Product.objects.filter(
                status='active',
                category=category,
                is_featured=True
            ).select_related('brand').prefetch_related('gallery')[:3]
            
            if featured_products:
                categories.append({
                    'category': category,
                    'featured_products': featured_products,
                })
        return categories
    
    def get_brand_performance_metrics(self):
        """Get brand performance metrics"""
        return Brand.objects.filter(
            is_active=True,
            is_featured=True
        ).annotate(
            product_count=Count('products', filter=Q(products__status='active')),
            avg_price=Avg('products__base_price'),
            total_reviews=Count('products__reviews'),
            avg_rating=Avg('products__reviews__rating')
        ).filter(product_count__gt=0)[:8]
    
    def get_homepage_widgets(self):
        """Get additional widgets for homepage"""
        return {
            # Flash sale products
            'flash_sale_products': Product.objects.filter(
                status='active',
                discounted_price__isnull=False,
                discounted_price__lt=F('base_price') * 0.7  # 30% or more discount
            ).select_related('brand', 'category')[:6],
            
            # Products with free shipping (if you have shipping logic)
            'free_shipping_products': Product.objects.filter(
                status='active',
                weight__lte=500  # Assuming products under 500g get free shipping
            ).select_related('brand', 'category')[:6],
            
            # Gift-worthy products
            'gift_products': Product.objects.filter(
                status='active',
                occasion__icontains='gift'
            ).select_related('brand', 'category')[:6],
            
            # Products with high purchase counts
            'popular_products': Product.objects.filter(
                status='active',
                purchase_count__gte=10
            ).select_related('brand', 'category').order_by('-purchase_count')[:6],
        }


# Additional utility functions you can use

def get_product_recommendations(product, limit=4):
    """Get recommended products based on a specific product"""
    return Product.objects.filter(
        status='active',
        category=product.category,
        brand=product.brand
    ).exclude(id=product.id).select_related('brand', 'category')[:limit]

def get_frequently_bought_together(product, limit=3):
    """Get products frequently bought together (requires order data)"""
    # This would need Order and OrderItem models
    # For now, return products from same category
    return Product.objects.filter(
        status='active',
        category=product.category
    ).exclude(id=product.id)[:limit]

def get_trending_searches():
    """Get trending search terms (would need search tracking)"""
    # This would require a SearchQuery model to track user searches
    return []

def get_social_proof_data():
    """Get social proof data for homepage"""
    return {
        'recent_purchases': [], # Would need Order model
        'customer_count': User.objects.filter(orders__isnull=False).distinct().count(),
        'total_orders': 0, # Would need Order model
        'satisfaction_rate': 95, # Could be calculated from reviews
    }

# Additional homepage sections you could add:

def get_size_guide_popular_products():
    """Products that might need size guides"""
    return Product.objects.filter(
        status='active',
        category__name__icontains='clothing'
    ).select_related('brand', 'category')[:6]

def get_style_guide_products():
    """Products for style inspiration"""
    return Product.objects.filter(
        status='active',
        occasion__isnull=False
    ).select_related('brand', 'category')[:8]

def get_color_trend_products():
    """Products featuring trending colors"""
    trending_colors = Color.objects.filter(
        is_active=True,
        productvariant__product__status='active'
    ).annotate(
        product_count=Count('productvariant__product', distinct=True)
    ).order_by('-product_count')[:5]
    
    return {
        'trending_colors': trending_colors,
        'color_products': {
            color.name: Product.objects.filter(
                status='active',
                variants__color=color
            ).select_related('brand', 'category').distinct()[:4]
            for color in trending_colors
        }
    }    

   


# =========================================================================================================================================================================================

# 2 Product List View
"""
Retrieves and lists all available products from the Skatezo database.

This function is responsible for fetching all product entries currently
stored in the Skatezo product catalog. It is typically used in views 
or API endpoints to provide a complete overview of all products 
available for browsing or purchase.

Returns:
    QuerySet: A Django QuerySet containing all product instances 
              in the database that are not marked as deleted or archived.

Usage:
    This function can be used in views, serializers, or API responses 
    where a full product list is required for rendering or transmission.
"""

class ProductListView(ListView):
    """
    Enhanced product listing page with advanced filtering, sorting, search and pagination
    """
    model = Product
    template_name = 'products/list/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.filter(status='active').select_related(
            'brand', 'category'
        ).prefetch_related(
            'variants__color', 'variants__size', 'gallery', 'materials',
            'reviews', 'attribute_mappings__attribute_value__attribute'
        ).annotate(
            # Calculate average rating - specify output_field
            avg_rating=Coalesce(Avg('reviews__rating'), Value(0.0), output_field=FloatField()),
            review_count=Count('reviews'),
            # Calculate min price across variants - specify output_field
            min_variant_price=Min(
                Case(
                    When(variants__discounted_price__isnull=False, 
                         then='variants__discounted_price'),
                    default='variants__price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            # Calculate total stock - specify output_field
            total_stock=Coalesce(Sum('variants__stock'), Value(0), output_field=IntegerField()),
            # Calculate discount percentage - specify output_field
            discount_percent=Case(
                When(discounted_price__isnull=False,
                     then=(F('base_price') - F('discounted_price')) * Value(100.0) / F('base_price')),
                default=Value(0.0),
                output_field=FloatField()
            )
        )
        
        # Advanced search with PostgreSQL full-text search (fallback to icontains)
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            try:
                # Try PostgreSQL full-text search first
                search_vector = SearchVector('name', weight='A') + \
                               SearchVector('description', weight='B') + \
                               SearchVector('tags', weight='C') + \
                               SearchVector('brand__name', weight='B')
                search_query_obj = SearchQuery(search_query)
                queryset = queryset.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query_obj)
                ).filter(search=search_query_obj).order_by('-rank')
            except:
                # Fallback to regular search
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(tags__icontains=search_query) |
                    Q(brand__name__icontains=search_query) |
                    Q(short_description__icontains=search_query)
                )
        
        # Category filter with subcategories
        category_slug = self.request.GET.get('category', '')
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
                categories = [category] + category.get_all_children()
                queryset = queryset.filter(category__in=categories)
            except Category.DoesNotExist:
                pass
        
        # Multiple category filter
        categories = self.request.GET.getlist('categories')
        if categories:
            queryset = queryset.filter(category__slug__in=categories)
        
        # Brand filter (multiple brands)
        brands = self.request.GET.getlist('brands')
        if brands:
            queryset = queryset.filter(brand__slug__in=brands)
        
        # Gender filter
        gender = self.request.GET.get('gender', '')
        if gender and gender in dict(Product.GENDER_CHOICES):
            queryset = queryset.filter(gender=gender)
        
        # Color filter (multiple colors)
        colors = self.request.GET.getlist('colors')
        if colors:
            queryset = queryset.filter(variants__color__id__in=colors).distinct()
        
        # Size filter (multiple sizes)
        sizes = self.request.GET.getlist('sizes')
        if sizes:
            queryset = queryset.filter(variants__size__id__in=sizes).distinct()
        
        # Material filter (multiple materials)
        materials = self.request.GET.getlist('materials')
        if materials:
            queryset = queryset.filter(materials__id__in=materials).distinct()
        
        # Price range filter - cast to DecimalField for consistent comparison
        min_price = self.request.GET.get('min_price', '')
        max_price = self.request.GET.get('max_price', '')
        if min_price:
            try:
                min_price = float(min_price)
                queryset = queryset.filter(
                    Q(discounted_price__gte=min_price) |
                    Q(discounted_price__isnull=True, base_price__gte=min_price)
                )
            except ValueError:
                pass
        if max_price:
            try:
                max_price = float(max_price)
                queryset = queryset.filter(
                    Q(discounted_price__lte=max_price) |
                    Q(discounted_price__isnull=True, base_price__lte=max_price)
                )
            except ValueError:
                pass
        
        # Rating filter
        min_rating = self.request.GET.get('min_rating', '')
        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(avg_rating__gte=min_rating)
            except ValueError:
                pass
        
        # Availability filters
        availability = self.request.GET.get('availability', '')
        if availability == 'in_stock':
            queryset = queryset.filter(variants__stock__gt=0).distinct()
        elif availability == 'low_stock':
            queryset = queryset.filter(
                variants__stock__lte=F('variants__low_stock_threshold'),
                variants__stock__gt=0
            ).distinct()
        elif availability == 'out_of_stock':
            queryset = queryset.filter(variants__stock=0).distinct()
        
        # Discount filter
        has_discount = self.request.GET.get('has_discount', '')
        if has_discount == 'true':
            queryset = queryset.filter(discounted_price__isnull=False)
        
        # New arrivals filter
        is_new = self.request.GET.get('is_new', '')
        if is_new == 'true':
            queryset = queryset.filter(is_new_arrival=True)
        
        # Featured products filter
        is_featured = self.request.GET.get('is_featured', '')
        if is_featured == 'true':
            queryset = queryset.filter(is_featured=True)
        
        # Bestseller filter
        is_bestseller = self.request.GET.get('is_bestseller', '')
        if is_bestseller == 'true':
            queryset = queryset.filter(is_bestseller=True)
        
        # Collection filter
        collection_slug = self.request.GET.get('collection', '')
        if collection_slug:
            try:
                collection = Collection.objects.get(slug=collection_slug)
                queryset = queryset.filter(collections=collection)
            except Collection.DoesNotExist:
                pass
        
        # Custom attribute filters
        for key, value in self.request.GET.items():
            if key.startswith('attr_') and value:
                attr_name = key[5:]  # Remove 'attr_' prefix
                queryset = queryset.filter(
                    attribute_mappings__attribute_value__attribute__name=attr_name,
                    attribute_mappings__attribute_value__value=value
                ).distinct()
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = {
            'name': 'name',
            '-name': '-name',
            'price_low': 'min_variant_price',
            'price_high': '-min_variant_price',
            'newest': '-created_at',
            'oldest': 'created_at',
            'popular': '-purchase_count',
            'views': '-view_count',
            'rating': '-avg_rating',
            'discount': '-discount_percent',
            'alphabetical': 'name',
            'stock': '-total_stock'
        }
        
        if sort_by in valid_sorts:
            # Handle special sorting cases
            if sort_by in ['price_low', 'price_high']:
                queryset = queryset.order_by(valid_sorts[sort_by], 'name')
            elif sort_by == 'rating':
                queryset = queryset.order_by('-avg_rating', '-review_count', 'name')
            else:
                queryset = queryset.order_by(valid_sorts[sort_by])
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset.distinct()
    
    def get_paginate_by(self, queryset):
        """Allow dynamic pagination"""
        per_page = self.request.GET.get('per_page', self.paginate_by)
        try:
            per_page = int(per_page)
            if per_page in [12, 20, 40, 60, 100]:
                return per_page
        except ValueError:
            pass
        return self.paginate_by
    # repairing
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cache filter options for better performance
        cache_key = "product_list_filters"
        filter_data = cache.get(cache_key)
        
        if not filter_data:
            filter_data = {
                'categories': Category.objects.filter(
                    is_active=True,
                    parent__isnull=True
                ).prefetch_related('subcategories').annotate(
                    product_count=Count('products', filter=Q(products__status='active'))
                ),
                'brands': Brand.objects.filter(is_active=True).annotate(
                    product_count=Count('products', filter=Q(products__status='active'))
                ).order_by('name'),
                'colors': Color.objects.filter(is_active=True).annotate(
                    product_count=Count('productvariant__product', 
                                      filter=Q(productvariant__product__status='active'),
                                      distinct=True)
                ).order_by('sort_order', 'name'),
                'sizes': Size.objects.filter(is_active=True).annotate(
                    product_count=Count('productvariant__product',
                                      filter=Q(productvariant__product__status='active'),
                                      distinct=True)
                ).order_by('category', 'sort_order'),
                'materials': Material.objects.all().annotate(
                    product_count=Count('product', filter=Q(product__status='active'))
                ).order_by('name'),
                'collections': Collection.objects.filter(is_active=True).annotate(
                    product_count=Count('products', filter=Q(products__status='active'))
                ).order_by('sort_order', 'name'),
            }
            cache.set(cache_key, filter_data, 300)  # Cache for 5 minutes
        
        context.update(filter_data)
        
        # Custom attributes for filtering
        context['custom_attributes'] = ProductAttribute.objects.filter(
            is_filterable=True
        ).prefetch_related('values').order_by('sort_order')
        
        # Gender choices
        context['gender_choices'] = Product.GENDER_CHOICES
        
        # Price range - specify output_field for mixed types
        price_stats = Product.objects.filter(status='active').aggregate(
            min_price=Min(
                Case(
                    When(discounted_price__isnull=False, then='discounted_price'),
                    default='base_price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            max_price=Max(
                Case(
                    When(discounted_price__isnull=False, then='discounted_price'),
                    default='base_price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        context['price_range'] = price_stats
        
        # Current filters for display and form persistence
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'category': self.request.GET.get('category', ''),
            'categories': self.request.GET.getlist('categories'),
            'brands': self.request.GET.getlist('brands'),
            'gender': self.request.GET.get('gender', ''),
            'colors': self.request.GET.getlist('colors'),
            'sizes': self.request.GET.getlist('sizes'),
            'materials': self.request.GET.getlist('materials'),
            'min_price': self.request.GET.get('min_price', ''),
            'max_price': self.request.GET.get('max_price', ''),
            'min_rating': self.request.GET.get('min_rating', ''),
            'availability': self.request.GET.get('availability', ''),
            'has_discount': self.request.GET.get('has_discount', ''),
            'is_new': self.request.GET.get('is_new', ''),
            'is_featured': self.request.GET.get('is_featured', ''),
            'is_bestseller': self.request.GET.get('is_bestseller', ''),
            'collection': self.request.GET.get('collection', ''),
            'sort': self.request.GET.get('sort', 'newest'),
            'per_page': self.request.GET.get('per_page', str(self.paginate_by)),
        }
        
        # Add custom attribute filters
        for attr in context['custom_attributes']:
            attr_key = f'attr_{attr.name}'
            context['current_filters'][attr_key] = self.request.GET.get(attr_key, '')
        
        # Sort options
        context['sort_options'] = [
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
            ('name', 'Name A-Z'),
            ('-name', 'Name Z-A'),
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('popular', 'Most Popular'),
            ('views', 'Most Viewed'),
            ('rating', 'Highest Rated'),
            ('discount', 'Highest Discount'),
            ('stock', 'Stock Level'),
        ]
        
        # Pagination options
        context['per_page_options'] = [12, 20, 40, 60, 100]
        
        # Applied filters count
        applied_filters = 0
        for key, value in context['current_filters'].items():
            if key not in ['sort', 'per_page'] and value:
                if isinstance(value, list):
                    applied_filters += len(value)
                else:
                    applied_filters += 1
        context['applied_filters_count'] = applied_filters
        
        # Quick filter stats
        total_products = Product.objects.filter(status='active').count()
        context['total_products'] = total_products
        context['filtered_count'] = self.get_queryset().count()
        
        # Related collections (for cross-selling)
        if context['current_filters']['category']:
            try:
                category = Category.objects.get(slug=context['current_filters']['category'])
                context['related_collections'] = Collection.objects.filter(
                    is_active=True,
                    products__category=category
                ).distinct()[:3]
            except Category.DoesNotExist:
                context['related_collections'] = []
        
        return context


# AJAX views for dynamic filtering
def get_filter_options(request):
    """AJAX endpoint to get filter options based on current selection"""
    filters = {}
    
    # Get current filters
    category = request.GET.get('category', '')
    brands = request.GET.getlist('brands')
    
    # Get available colors for current selection
    queryset = Product.objects.filter(status='active')
    if category:
        try:
            cat_obj = Category.objects.get(slug=category)
            categories = [cat_obj] + cat_obj.get_all_children()
            queryset = queryset.filter(category__in=categories)
        except Category.DoesNotExist:
            pass
    
    if brands:
        queryset = queryset.filter(brand__slug__in=brands)
    
    # Get available options
    filters['colors'] = list(
        Color.objects.filter(
            productvariant__product__in=queryset,
            is_active=True
        ).distinct().values('id', 'name', 'hex_code')
    )
    
    filters['sizes'] = list(
        Size.objects.filter(
            productvariant__product__in=queryset,
            is_active=True
        ).distinct().values('id', 'name', 'category')
    )
    
    return JsonResponse(filters)

# Product Quick View----------------------------------------------------------------------------------
@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache for 5 minutes
class ProductQuickView(DetailView):
    """
    Quick view for individual product details without full page reload.
    Can be used via AJAX for modal/popup displays or as a partial template.
    """
    model = Product
    template_name = 'products/partials/product_quick_view.html'
    context_object_name = 'product'
    
    def get_object(self):
        """Get product by ID or slug"""
        try:
            logger.debug(f"Getting product with kwargs: {self.kwargs}")
            
            if 'product_id' in self.kwargs:
                logger.debug(f"Fetching product by ID: {self.kwargs['product_id']}")
                return get_object_or_404(
                    Product.objects.select_related('brand', 'category')
                                  .prefetch_related('variants__color', 'variants__size', 
                                                  'gallery', 'materials'),
                    id=self.kwargs['product_id'],
                    status='active'
                )
            elif 'slug' in self.kwargs:
                logger.debug(f"Fetching product by slug: {self.kwargs['slug']}")
                return get_object_or_404(
                    Product.objects.select_related('brand', 'category')
                                  .prefetch_related('variants__color', 'variants__size', 
                                                  'gallery', 'materials'),
                    slug=self.kwargs['slug'],
                    status='active'
                )
            else:
                logger.error("Neither product_id nor slug provided in kwargs")
                raise ValueError("Either product_id or slug must be provided")
        except Exception as e:
            logger.error(f"Error in get_object: {str(e)}", exc_info=True)
            raise
    
    def get_context_data(self, **kwargs):
        try:
            logger.debug(f"Building context for product: {self.object.id if self.object else 'None'}")
            context = super().get_context_data(**kwargs)
            product = self.object
            
            logger.debug(f"Product found: {product.name} (ID: {product.id})")
            
            # Get available variants - Fixed: using 'stock' instead of 'stock_quantity'
            logger.debug("Fetching active variants...")
            active_variants = product.variants.filter(is_active=True, stock__gt=0)
            logger.debug(f"Found {active_variants.count()} active variants with stock")
            
            # Get available colors and sizes from active variants only
            logger.debug("Fetching available colors...")
            try:
                if hasattr(product, 'get_available_colors'):
                    available_colors = product.get_available_colors().filter(
                        id__in=active_variants.values_list('color_id', flat=True)
                    ).filter(is_active=True)
                    logger.debug(f"Found {available_colors.count()} available colors")
                else:
                    logger.warning("Product model doesn't have get_available_colors method")
                    available_colors = []
            except Exception as e:
                logger.error(f"Error fetching available colors: {str(e)}")
                available_colors = []
            
            logger.debug("Fetching available sizes...")
            try:
                if hasattr(product, 'get_available_sizes'):
                    available_sizes = product.get_available_sizes().filter(
                        id__in=active_variants.values_list('size_id', flat=True)
                    ).filter(is_active=True)
                    logger.debug(f"Found {available_sizes.count()} available sizes")
                else:
                    logger.warning("Product model doesn't have get_available_sizes method")
                    available_sizes = []
            except Exception as e:
                logger.error(f"Error fetching available sizes: {str(e)}")
                available_sizes = []
            
            # Get primary image or first gallery image
            logger.debug("Fetching gallery images...")
            primary_image = product.gallery.filter(is_primary=True).first()
            if not primary_image:
                primary_image = product.gallery.first()
            logger.debug(f"Primary image found: {primary_image is not None}")
            
            # Get all gallery images
            gallery_images = product.gallery.all()[:6]  # Limit to 6 images for quick view
            logger.debug(f"Found {len(gallery_images)} gallery images")
            
            # Get price range for variants
            logger.debug("Calculating price range...")
            variant_prices = active_variants.values_list('price', 'discounted_price')
            if variant_prices:
                prices = []
                for price, discounted in variant_prices:
                    effective_price = discounted if discounted else price
                    prices.append(effective_price)
                
                min_price = min(prices) if prices else product.get_effective_price()
                max_price = max(prices) if prices else product.get_effective_price()
                logger.debug(f"Price range: {min_price} - {max_price}")
            else:
                min_price = max_price = product.get_effective_price()
                logger.debug(f"No variant prices, using product price: {min_price}")
            
            # Get reviews summary
            logger.debug("Fetching reviews...")
            reviews = product.reviews.filter(is_approved=True)
            avg_rating = reviews.aggregate(
                avg=models.Avg('rating')
            )['avg'] or 0
            logger.debug(f"Found {reviews.count()} reviews, avg rating: {avg_rating}")
            
            # Check if product has any stock across all variants
            logger.debug("Calculating total stock...")
            total_stock = active_variants.aggregate(
                total=models.Sum('stock')
            )['total'] or 0
            logger.debug(f"Total stock: {total_stock}")
            
            context.update({
                'active_variants': active_variants,
                'available_colors': available_colors,
                'available_sizes': available_sizes,
                'primary_image': primary_image,
                'gallery_images': gallery_images,
                'min_price': min_price,
                'max_price': max_price,
                'avg_rating': round(avg_rating, 1),
                'review_count': reviews.count(),
                'total_stock': total_stock,
                'is_in_stock': total_stock > 0,
                'is_quick_view': True,  # Flag to identify partial template usage
            })
            
            logger.debug("Context data built successfully")
            return context
            
        except Exception as e:
            logger.error(f"Error building context for product {self.object.id if self.object else 'None'}: {str(e)}", exc_info=True)
            raise
    
    def render_to_response(self, context, **response_kwargs):
        """Handle both AJAX and regular requests"""
        try:
            logger.debug(f"Rendering response for product {self.object.id}")
            
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                logger.debug("Handling AJAX request")
                # AJAX request - return JSON with HTML content
                html = render_to_string(self.template_name, context, request=self.request)
                
                response_data = {
                    'success': True,
                    'html': html,
                    'product_id': self.object.id,
                    'product_name': self.object.name,
                    'product_price': float(self.object.get_effective_price()),
                    'in_stock': context['is_in_stock'],
                }
                logger.debug("AJAX response prepared successfully")
                return JsonResponse(response_data)
            else:
                logger.debug("Handling regular HTTP request")
                # Regular request - return HTML response
                return super().render_to_response(context, **response_kwargs)
                
        except Exception as e:
            logger.error(f"Error rendering response for product {self.object.id if self.object else 'None'}: {str(e)}", exc_info=True)
            
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Internal server error occurred'
                }, status=500)
            else:
                raise


def product_quick_view_ajax(request, product_id):
    """
    AJAX-specific view for product quick view.
    Returns JSON response with HTML content.
    """
    logger.debug(f"AJAX view called for product_id: {product_id}")
    
    try:
        logger.debug(f"Fetching product with ID: {product_id}")
        product = get_object_or_404(
            Product.objects.select_related('brand', 'category')
                          .prefetch_related('variants__color', 'variants__size', 
                                          'gallery', 'materials'),
            id=product_id,
            status='active'
        )
        logger.debug(f"Product found: {product.name}")
        
        # Get context data - Fixed: using 'stock' instead of 'stock_quantity'
        logger.debug("Fetching active variants...")
        active_variants = product.variants.filter(is_active=True, stock__gt=0)
        logger.debug(f"Found {active_variants.count()} active variants")
        
        # Get available colors and sizes from active variants only
        logger.debug("Processing available colors...")
        try:
            if hasattr(product, 'get_available_colors'):
                available_colors = product.get_available_colors().filter(
                    id__in=active_variants.values_list('color_id', flat=True)
                ).filter(is_active=True)
                logger.debug(f"Found {available_colors.count()} available colors")
            else:
                logger.warning("Product model doesn't have get_available_colors method")
                available_colors = []
        except Exception as e:
            logger.error(f"Error fetching available colors: {str(e)}")
            available_colors = []
        
        logger.debug("Processing available sizes...")
        try:
            if hasattr(product, 'get_available_sizes'):
                available_sizes = product.get_available_sizes().filter(
                    id__in=active_variants.values_list('size_id', flat=True)
                ).filter(is_active=True)
                logger.debug(f"Found {available_sizes.count()} available sizes")
            else:
                logger.warning("Product model doesn't have get_available_sizes method")
                available_sizes = []
        except Exception as e:
            logger.error(f"Error fetching available sizes: {str(e)}")
            available_sizes = []
        
        logger.debug("Processing images...")
        primary_image = product.gallery.filter(is_primary=True).first()
        if not primary_image:
            primary_image = product.gallery.first()
        
        gallery_images = product.gallery.all()[:6]
        logger.debug(f"Found primary image: {primary_image is not None}, gallery images: {len(gallery_images)}")
        
        # Calculate price range
        logger.debug("Calculating price range...")
        variant_prices = active_variants.values_list('price', 'discounted_price')
        if variant_prices:
            prices = []
            for price, discounted in variant_prices:
                effective_price = discounted if discounted else price
                prices.append(effective_price)
            
            min_price = min(prices) if prices else product.get_effective_price()
            max_price = max(prices) if prices else product.get_effective_price()
        else:
            min_price = max_price = product.get_effective_price()
        logger.debug(f"Price range: {min_price} - {max_price}")
        
        # Reviews summary
        logger.debug("Processing reviews...")
        reviews = product.reviews.filter(is_approved=True)
        avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0
        logger.debug(f"Reviews: {reviews.count()}, avg rating: {avg_rating}")
        
        # Check total stock
        logger.debug("Calculating total stock...")
        total_stock = active_variants.aggregate(
            total=models.Sum('stock')
        )['total'] or 0
        logger.debug(f"Total stock: {total_stock}")
        
        context = {
            'product': product,
            'active_variants': active_variants,
            'available_colors': available_colors,
            'available_sizes': available_sizes,
            'primary_image': primary_image,
            'gallery_images': gallery_images,
            'min_price': min_price,
            'max_price': max_price,
            'avg_rating': round(avg_rating, 1),
            'review_count': reviews.count(),
            'total_stock': total_stock,
            'is_in_stock': total_stock > 0,
            'is_quick_view': True,
        }
        
        logger.debug("Rendering template...")
        html = render_to_string(
            'products/partials/product_quick_view.html', 
            context, 
            request=request
        )
        logger.debug("Template rendered successfully")
        
        # Prepare product data for JSON response
        product_data = {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'price': float(product.get_effective_price()),
            'in_stock': total_stock > 0,
            'total_stock': total_stock,
        }
        
        # Add optional fields with error handling
        try:
            if hasattr(product, 'get_discount_percent'):
                product_data['discount_percent'] = product.get_discount_percent()
            else:
                product_data['discount_percent'] = 0
        except Exception as e:
            logger.warning(f"Error getting discount percent: {str(e)}")
            product_data['discount_percent'] = 0
        
        try:
            product_data['brand'] = product.brand.name if product.brand else ''
        except Exception as e:
            logger.warning(f"Error getting brand name: {str(e)}")
            product_data['brand'] = ''
        
        try:
            product_data['category'] = product.category.name if product.category else ''
        except Exception as e:
            logger.warning(f"Error getting category name: {str(e)}")
            product_data['category'] = ''
        
        response_data = {
            'success': True,
            'html': html,
            'product': product_data
        }
        
        logger.debug("AJAX response prepared successfully")
        return JsonResponse(response_data)
        
    except Product.DoesNotExist:
        logger.error(f"Product with ID {product_id} not found")
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in product_quick_view_ajax for product {product_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error occurred'
        }, status=500)
# ----------------------------------------------------------------------------------------------------------------
# Additional Views 
def search_suggestions(request):
    """
    AJAX endpoint for search suggestions
    """
    query = request.GET.get('q', '').strip()
    suggestions = []
    
    if len(query) >= 2:
        # Product name suggestions
        products = Product.objects.filter(
            status='active',
            name__icontains=query
        ).values_list('name', flat=True)[:5]
        
        # Brand suggestions
        brands = Brand.objects.filter(
            is_active=True,
            name__icontains=query
        ).values_list('name', flat=True)[:3]
        
        # Category suggestions
        categories = Category.objects.filter(
            is_active=True,
            name__icontains=query
        ).values_list('name', flat=True)[:3]
        
        suggestions = {
            'products': list(products),
            'brands': list(brands),
            'categories': list(categories),
        }
    
    return JsonResponse({'suggestions': suggestions})


class CategoryProductListView(ProductListView):
    """
    Product list filtered by category
    """
    def get_queryset(self):
        self.category = get_object_or_404(
            Category, 
            slug=self.kwargs['category_slug'],
            is_active=True
        )
        
        # Get all child categories
        categories = [self.category] + self.category.get_all_children()
        
        queryset = super().get_queryset()
        return queryset.filter(category__in=categories)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['page_title'] = f"{self.category.name} - Products"
        context['breadcrumbs'] = self.get_breadcrumbs()
        return context
    
    def get_breadcrumbs(self):
        breadcrumbs = [{'name': 'Home', 'url': '/'}]
        
        # Add parent categories
        if self.category.parent:
            breadcrumbs.append({
                'name': self.category.parent.name,
                'url': reverse('products:category-products', 
                             kwargs={'category_slug': self.category.parent.slug})
            })
        
        breadcrumbs.append({
            'name': self.category.name,
            'url': reverse('products:category-products', 
                         kwargs={'category_slug': self.category.slug})
        })
        
        return breadcrumbs


class BrandProductListView(ProductListView):
    """
    Product list filtered by brand
    """
    def get_queryset(self):
        self.brand = get_object_or_404(
            Brand, 
            slug=self.kwargs['brand_slug'],
            is_active=True
        )
        
        queryset = super().get_queryset()
        return queryset.filter(brand=self.brand)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['brand'] = self.brand
        context['page_title'] = f"{self.brand.name} - Products"
        return context


class CollectionProductListView(ProductListView):
    """
    Product list filtered by collection
    """
    def get_queryset(self):
        self.collection = get_object_or_404(
            Collection, 
            slug=self.kwargs['collection_slug'],
            is_active=True
        )
        
        queryset = super().get_queryset()
        return queryset.filter(collections=self.collection)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.collection
        context['page_title'] = f"{self.collection.name} - Collection"
        return context

# Add To Wishlist
@login_required
@require_POST
@csrf_exempt
def add_to_wishlist(request, product_id):
    """
    AJAX endpoint to add product to wishlist
    """
    try:
        product = get_object_or_404(Product, id=product_id, status='active')
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'message': 'Added to wishlist!' if created else 'Already in wishlist'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error adding to wishlist'
        })


@login_required
@require_POST
def remove_from_wishlist(request, product_id):
    """
    AJAX endpoint to remove product from wishlist
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        Wishlist.objects.filter(
            user=request.user,
            product=product
        ).delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Removed from wishlist'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error removing from wishlist'
        })


@require_POST
def quick_add_to_cart(request, variant_id):
    """
    AJAX endpoint for quick add to cart
    """
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        
        if not variant.is_in_stock():
            return JsonResponse({
                'success': False,
                'message': 'Product is out of stock'
            })
        
        if quantity > variant.get_available_stock():
            return JsonResponse({
                'success': False,
                'message': f'Only {variant.get_available_stock()} items available'
            })
        
        # Add to cart logic here (depends on your cart implementation)
        # For example, using sessions:
        cart = request.session.get('cart', {})
        cart_key = str(variant.id)
        
        if cart_key in cart:
            cart[cart_key]['quantity'] += quantity
        else:
            cart[cart_key] = {
                'variant_id': variant.id,
                'quantity': quantity,
                'price': float(variant.get_effective_price())
            }
        
        request.session['cart'] = cart
        request.session.modified = True
        
        # Calculate cart totals
        cart_count = sum(item['quantity'] for item in cart.values())
        cart_total = sum(item['quantity'] * item['price'] for item in cart.values())
        
        return JsonResponse({
            'success': True,
            'message': 'Added to cart successfully!',
            'cart_count': cart_count,
            'cart_total': cart_total
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error adding to cart'
        })


class ProductCompareView(ListView):
    """
    Product comparison page
    """
    model = Product
    template_name = 'products/compare.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        product_ids = self.request.session.get('compare_products', [])
        return Product.objects.filter(
            id__in=product_ids,
            status='active'
        ).prefetch_related('variants', 'gallery', 'materials', 'reviews')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get comparison attributes
        if context['products']:
            # Common attributes to compare
            context['comparison_attributes'] = [
                'Brand', 'Category', 'Price', 'Rating', 'Materials',
                'Available Colors', 'Available Sizes', 'Stock Status'
            ]
        
        return context


def add_to_compare(request, product_id):
    """
    AJAX endpoint to add product to comparison
    """
    try:
        product = get_object_or_404(Product, id=product_id, status='active')
        compare_products = request.session.get('compare_products', [])
        
        if product_id not in compare_products:
            if len(compare_products) >= 4:  # Limit to 4 products
                return JsonResponse({
                    'success': False,
                    'message': 'Maximum 4 products can be compared'
                })
            
            compare_products.append(product_id)
            request.session['compare_products'] = compare_products
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': 'Added to comparison',
                'compare_count': len(compare_products)
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Product already in comparison'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error adding to comparison'
        })


def remove_from_compare(request, product_id):
    """
    AJAX endpoint to remove product from comparison
    """
    try:
        compare_products = request.session.get('compare_products', [])
        if product_id in compare_products:
            compare_products.remove(product_id)
            request.session['compare_products'] = compare_products
            request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': 'Removed from comparison',
            'compare_count': len(compare_products)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error removing from comparison'
        })

# Grab The Product to wishlist 
@login_required
@require_http_methods(["POST"])
@csrf_exempt
def grabWishList(request, product_id):
    """
    Add/Remove product from user's wishlist via AJAX
    Returns JSON response with status and product details
    """
    logger.info(f"Wishlist request for product_id: {product_id}, user: {request.user.id}")
    
    try:
        # Import models here to avoid circular imports
        from .models import Product, ProductVariant, Wishlist
        
        # Validate product_id
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid product_id: {product_id}")
            return JsonResponse({
                'success': False,
                'message': 'Invalid product ID.',
            }, status=400)
        
        # Get product
        try:
            product = get_object_or_404(Product, id=product_id, status='active')
            logger.info(f"Found product: {product.name}")
        except Product.DoesNotExist:
            logger.error(f"Product not found: {product_id}")
            return JsonResponse({
                'success': False,
                'message': 'Product not found or unavailable.',
            }, status=404)
        
        user = request.user
        logger.info(f"Processing wishlist for user: {user.username}")
        
        # Get variant if specified in request
        variant_id = request.POST.get('variant_id')
        variant = None
        if variant_id:
            try:
                variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
                logger.info(f"Found variant: {variant.id}")
            except ProductVariant.DoesNotExist:
                logger.error(f"Variant not found: {variant_id}")
                return JsonResponse({
                    'success': False,
                    'message': 'Product variant not found.',
                }, status=404)
        
        # Check if item already exists in wishlist
        try:
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=user,
                product=product,
                variant=variant,
                defaults={}
            )
            logger.info(f"Wishlist item created: {created}")
        except Exception as e:
            logger.error(f"Error creating/getting wishlist item: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error processing wishlist request.',
            }, status=500)
        
        if created:
            # Item added to wishlist
            message = "Product added to your wishlist!"
            action = "added"
            icon = "fas fa-heart"
            color = "text-red-500"
            logger.info(f"Product {product_id} added to wishlist for user {user.id}")
        else:
            # Item already exists, remove it
            try:
                wishlist_item.delete()
                message = "Product removed from your wishlist!"
                action = "removed"
                icon = "far fa-heart"
                color = "text-gray-600"
                logger.info(f"Product {product_id} removed from wishlist for user {user.id}")
            except Exception as e:
                logger.error(f"Error removing wishlist item: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': 'Error removing item from wishlist.',
                }, status=500)
        
        # Prepare product data for response
        try:
            # Get product image safely
            image_url = '/static/images/no-image.jpg'  # Default image
            if hasattr(product, 'gallery') and product.gallery.exists():
                # Try to get primary image first
                primary_image = product.gallery.filter(is_primary=True).first()
                if primary_image and hasattr(primary_image, 'image') and primary_image.image:
                    image_url = primary_image.image.url
                else:
                    # Fallback to first available image
                    first_image = product.gallery.first()
                    if first_image and hasattr(first_image, 'image') and first_image.image:
                        image_url = first_image.image.url
            
            product_data = {
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'base_price': str(product.base_price),
                'discounted_price': str(product.discounted_price) if product.discounted_price else None,
                'effective_price': str(product.get_effective_price()),
                'discount_percent': product.get_discount_percent(),
                'short_description': product.short_description or '',
                'brand': product.brand.name if product.brand else '',
                'category': product.category.name if product.category else '',
                'is_in_stock': product.is_in_stock(),
                'image_url': image_url,
            }
            
            if variant:
                product_data.update({
                    'variant_id': variant.id,
                    'color': variant.color.name if hasattr(variant, 'color') and variant.color else '',
                    'size': variant.size.name if hasattr(variant, 'size') and variant.size else '',
                    'variant_sku': getattr(variant, 'sku', ''),
                })
            
            logger.info(f"Product data prepared successfully")
            
        except Exception as e:
            logger.error(f"Error preparing product data: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error preparing product information.',
            }, status=500)
        
        # Get updated wishlist count
        try:
            wishlist_count = Wishlist.objects.filter(user=user).count()
            logger.info(f"Updated wishlist count: {wishlist_count}")
        except Exception as e:
            logger.error(f"Error getting wishlist count: {str(e)}")
            wishlist_count = 0
        
        response_data = {
            'success': True,
            'action': action,
            'message': message,
            'icon': icon,
            'color': color,
            'product': product_data,
            'wishlist_count': wishlist_count,
        }
        
        logger.info(f"Successful wishlist response for product {product_id}")
        return JsonResponse(response_data)
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid data provided.',
        }, status=400)
        
    except Exception as e:
        logger.error(f"Unexpected error in grabWishList: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'error': str(e) if getattr(settings, 'DEBUG', False) else None,
        }, status=500)

# Rest of the Product List Code Is In the - product_list.py file for modular structure


# =================================================================================================================================================================================================
# Working on category views 
from decimal import Decimal

class CategoryListView(ListView):
    """
    Enhanced category list view with statistics, filtering, and better organization
    """
    model = Category
    template_name = 'products/list/category_list.html'
    context_object_name = 'categories'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Category.objects.filter(
            is_active=True,
            parent__isnull=True
        ).prefetch_related(
            'subcategories', 
            'products',
            'products__brand',
            'products__variants'
        ).annotate(
            total_products=Count('products', filter=Q(products__status='active')),
            subcategory_count=Count('subcategories', filter=Q(subcategories__is_active=True))
        ).order_by('sort_order', 'name')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Category statistics
        context['total_categories'] = Category.objects.filter(is_active=True).count()
        context['featured_categories'] = Category.objects.filter(
            is_active=True, 
            products__is_featured=True
        ).distinct()[:6]
        
        # Popular categories (based on product count)
        context['popular_categories'] = Category.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count('products', filter=Q(products__status='active'))
        ).filter(product_count__gt=0).order_by('-product_count')[:8]
        
        # Search query for template
        context['search_query'] = self.request.GET.get('search', '')
        
        return context

# Category Detail View
class CategoryDetailView(ListView):
    """
    Enhanced category detail view with advanced filtering, sorting, and recommendations
    """
    template_name = 'products/list/category_detail.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        
        # Get products from this category and subcategories
        categories = [self.category] + self.category.get_all_children()
        queryset = Product.objects.filter(
            status='active',
            category__in=categories
        ).select_related('brand', 'category').prefetch_related(
            'variants', 'gallery', 'materials', 'reviews'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
            min_price=Min('variants__price'),
            max_price=Max('variants__price')
        )
        
        # Apply filters
        queryset = self.apply_filters(queryset)
        
        # Apply sorting
        queryset = self.apply_sorting(queryset)
        
        return queryset
    
    def apply_filters(self, queryset):
        """Apply various filters based on GET parameters"""
        
        # Brand filter
        brands = self.request.GET.getlist('brand')
        if brands:
            queryset = queryset.filter(brand__slug__in=brands)
        
        # Price range filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            try:
                min_price = Decimal(min_price)
                queryset = queryset.filter(
                    Q(discounted_price__gte=min_price) | 
                    Q(discounted_price__isnull=True, base_price__gte=min_price)
                )
            except (ValueError, TypeError):
                pass
        
        if max_price:
            try:
                max_price = Decimal(max_price)
                queryset = queryset.filter(
                    Q(discounted_price__lte=max_price) | 
                    Q(discounted_price__isnull=True, base_price__lte=max_price)
                )
            except (ValueError, TypeError):
                pass
        
        # Color filter
        colors = self.request.GET.getlist('color')
        if colors:
            queryset = queryset.filter(variants__color__slug__in=colors).distinct()
        
        # Size filter
        sizes = self.request.GET.getlist('size')
        if sizes:
            queryset = queryset.filter(variants__size__name__in=sizes).distinct()
        
        # Gender filter
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Material filter
        materials = self.request.GET.getlist('material')
        if materials:
            queryset = queryset.filter(materials__name__in=materials).distinct()
        
        # Rating filter
        min_rating = self.request.GET.get('min_rating')
        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(avg_rating__gte=min_rating)
            except (ValueError, TypeError):
                pass
        
        # Availability filter
        in_stock_only = self.request.GET.get('in_stock')
        if in_stock_only == '1':
            queryset = queryset.filter(variants__stock__gt=0).distinct()
        
        # Discount filter
        on_sale_only = self.request.GET.get('on_sale')
        if on_sale_only == '1':
            queryset = queryset.filter(discounted_price__isnull=False)
        
        # New arrivals filter
        new_arrivals = self.request.GET.get('new_arrivals')
        if new_arrivals == '1':
            queryset = queryset.filter(is_new_arrival=True)
        
        # Search within category
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__icontains=search_query) |
                Q(brand__name__icontains=search_query)
            )
        
        return queryset
    
    def apply_sorting(self, queryset):
        """Apply sorting based on GET parameter"""
        sort_by = self.request.GET.get('sort', 'default')
        
        sort_options = {
            'name': 'name',
            '-name': '-name',
            'price': 'base_price',
            '-price': '-base_price',
            'rating': '-avg_rating',
            'popularity': '-purchase_count',
            'newest': '-created_at',
            'oldest': 'created_at',
            'discount': '-discounted_price',
        }
        
        if sort_by in sort_options:
            queryset = queryset.order_by(sort_options[sort_by])
        else:
            # Default sorting
            queryset = queryset.order_by('-is_featured', '-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        
        # Subcategories
        context['subcategories'] = self.category.subcategories.filter(
            is_active=True
        ).annotate(
            product_count=Count('products', filter=Q(products__status='active'))
        )
        
        # Filter options for sidebar
        context.update(self.get_filter_options())
        
        # Category statistics
        context['category_stats'] = self.get_category_stats()
        
        # Breadcrumb
        context['breadcrumb'] = self.get_breadcrumb()
        
        # Related categories
        context['related_categories'] = self.get_related_categories()
        
        # Current filters (for display)
        context['current_filters'] = self.get_current_filters()
        
        # SEO data
        context['meta_title'] = self.category.meta_title or f"{self.category.name} - Fashion Store"
        context['meta_description'] = self.category.meta_description or self.category.description
        
        return context
    
    def get_filter_options(self):
        """Get available filter options for the current category"""
        categories = [self.category] + self.category.get_all_children()
        products = Product.objects.filter(
            status='active',
            category__in=categories
        )
        
        return {
            'available_brands': Brand.objects.filter(
                products__in=products
            ).annotate(
                product_count=Count('products')
            ).distinct().order_by('name'),
            
            'available_colors': Color.objects.filter(
                productvariant__product__in=products
            ).annotate(
                product_count=Count('productvariant__product', distinct=True)
            ).distinct().order_by('sort_order', 'name'),
            
            'available_sizes': Size.objects.filter(
                productvariant__product__in=products
            ).annotate(
                product_count=Count('productvariant__product', distinct=True)
            ).distinct().order_by('sort_order'),
            
            'available_materials': Material.objects.filter(
                product__in=products
            ).annotate(
                product_count=Count('product', distinct=True)
            ).distinct().order_by('name'),
            
            'price_range': products.aggregate(
                min_price=Min('base_price'),
                max_price=Max('base_price')
            ),
            
            'gender_choices': Product.GENDER_CHOICES,
        }
    
    def get_category_stats(self):
        """Get statistics for the current category"""
        categories = [self.category] + self.category.get_all_children()
        products = Product.objects.filter(
            status='active',
            category__in=categories
        )
        
        return {
            'total_products': products.count(),
            'in_stock_products': products.filter(variants__stock__gt=0).distinct().count(),
            'brands_count': products.values('brand').distinct().count(),
            'avg_price': products.aggregate(avg_price=Avg('base_price'))['avg_price'] or 0,
            'new_arrivals_count': products.filter(is_new_arrival=True).count(),
            'on_sale_count': products.filter(discounted_price__isnull=False).count(),
        }
    
    def get_breadcrumb(self):
        """Generate breadcrumb navigation"""
        breadcrumb = []
        current_category = self.category
        
        while current_category:
            breadcrumb.insert(0, {
                'name': current_category.name,
                'url': current_category.get_absolute_url(),
                'is_current': current_category == self.category
            })
            current_category = current_category.parent
        
        return breadcrumb
    
    def get_related_categories(self):
        """Get related categories for recommendations"""
        if self.category.parent:
            # Get sibling categories
            return self.category.parent.subcategories.filter(
                is_active=True
            ).exclude(id=self.category.id)[:4]
        else:
            # Get other top-level categories
            return Category.objects.filter(
                is_active=True,
                parent__isnull=True
            ).exclude(id=self.category.id)[:4]
    
    def get_current_filters(self):
        """Get currently applied filters for display"""
        filters = {}
        
        if self.request.GET.getlist('brand'):
            filters['Brands'] = Brand.objects.filter(
                slug__in=self.request.GET.getlist('brand')
            ).values_list('name', flat=True)
        
        if self.request.GET.getlist('color'):
            filters['Colors'] = Color.objects.filter(
                slug__in=self.request.GET.getlist('color')
            ).values_list('name', flat=True)
        
        if self.request.GET.getlist('size'):
            filters['Sizes'] = self.request.GET.getlist('size')
        
        if self.request.GET.get('gender'):
            gender_dict = dict(Product.GENDER_CHOICES)
            filters['Gender'] = [gender_dict.get(self.request.GET.get('gender'))]
        
        if self.request.GET.get('min_price') or self.request.GET.get('max_price'):
            price_range = []
            if self.request.GET.get('min_price'):
                price_range.append(f"Min: ${self.request.GET.get('min_price')}")
            if self.request.GET.get('max_price'):
                price_range.append(f"Max: ${self.request.GET.get('max_price')}")
            filters['Price'] = price_range
        
        return filters


# AJAX view for dynamic filtering
def category_filter_ajax(request, slug):
    """AJAX endpoint for dynamic filtering without page reload"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        category = get_object_or_404(Category, slug=slug)
        view = CategoryDetailView()
        view.request = request
        view.kwargs = {'slug': slug}
        
        products = view.get_queryset()
        
        # Render products to HTML
        from django.template.loader import render_to_string
        html = render_to_string('products/partials/product_grid.html', {
            'products': products[:view.paginate_by],
            'request': request
        })
        
        return JsonResponse({
            'html': html,
            'count': products.count(),
            'has_more': products.count() > view.paginate_by
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ===========================================================================================================================================
"""
Brands Section
This section contains views related to product brands, including listing all brands and displaying products from a specific
"""
# ====================================================================================================================================================
# Brand Views
class BrandListView(ListView):
    """
    Enhanced Brand List View with filtering, search, and sorting capabilities
    """
    model = Brand
    template_name = 'products/list/brand_list.html'
    context_object_name = 'brands'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Brand.objects.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__status='active')),
            avg_rating=Avg('products__reviews__rating'),
            min_price=Min('products__base_price'),
            max_price=Max('products__base_price')
        )
        
        # Search functionality
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(country__icontains=search_query)
            )
        
        # Filter by country
        country = self.request.GET.get('country')
        if country:
            queryset = queryset.filter(country__iexact=country)
        
        # Filter by featured status
        featured = self.request.GET.get('featured')
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        
        # Filter by product count range
        min_products = self.request.GET.get('min_products')
        if min_products:
            try:
                queryset = queryset.filter(product_count__gte=int(min_products))
            except ValueError:
                pass
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        valid_sorts = {
            'name': 'name',
            'name_desc': '-name',
            'products': '-product_count',
            'products_asc': 'product_count',
            'rating': '-avg_rating',
            'rating_asc': 'avg_rating',
            'established': '-established_year',
            'established_asc': 'established_year',
        }
        
        if sort_by in valid_sorts:
            queryset = queryset.order_by(valid_sorts[sort_by])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options to context
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'selected_country': self.request.GET.get('country', ''),
            'selected_featured': self.request.GET.get('featured', ''),
            'selected_sort': self.request.GET.get('sort', 'name'),
            'min_products': self.request.GET.get('min_products', ''),
            
            # Get unique countries for filter dropdown
            'countries': Brand.objects.filter(
                is_active=True, 
                country__isnull=False
            ).exclude(country='').values_list('country', flat=True).distinct().order_by('country'),
            
            # Featured brands for highlighting
            'featured_brands': Brand.objects.filter(
                is_active=True, 
                is_featured=True
            ).annotate(
                product_count=Count('products', filter=Q(products__status='active'))
            )[:6],
            
            # Statistics
            'total_brands': Brand.objects.filter(is_active=True).count(),
            'brands_with_products': Brand.objects.filter(
                is_active=True, 
                products__status='active'
            ).distinct().count(),
        })
        
        # Handle AJAX requests for infinite scroll or filtering
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string(
                'products/partials/brand_cards.html', 
                {'brands': context['brands']}, 
                request=self.request
            )
            return JsonResponse({'html': html, 'has_next': context['page_obj'].has_next()})
        
        return context

# Brand Detail View
class BrandDetailView(ListView):
    """
    Enhanced Brand Detail View with advanced filtering, sorting, and product management
    """
    template_name = 'products/list/brand_detail.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        self.brand = get_object_or_404(Brand, slug=self.kwargs['slug'])
        
        queryset = Product.objects.filter(
            status='active',
            brand=self.brand
        ).select_related('category', 'brand').prefetch_related(
            'gallery', 'variants', 'reviews', 'materials'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
            total_stock=Count('variants__stock')
        )
        
        # Category filtering
        category = self.request.GET.get('category')
        if category:
            try:
                category_obj = Category.objects.get(slug=category)
                # Include products from subcategories
                category_ids = [category_obj.id] + [child.id for child in category_obj.get_all_children()]
                queryset = queryset.filter(category_id__in=category_ids)
            except Category.DoesNotExist:
                pass
        
        # Price range filtering
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(base_price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(base_price__lte=float(max_price))
            except ValueError:
                pass
        
        # Rating filtering
        min_rating = self.request.GET.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(avg_rating__gte=float(min_rating))
            except ValueError:
                pass
        
        # Gender filtering
        gender = self.request.GET.get('gender')
        if gender and gender in ['men', 'women', 'unisex', 'kids']:
            queryset = queryset.filter(gender=gender)
        
        # Availability filtering
        availability = self.request.GET.get('availability')
        if availability == 'in_stock':
            queryset = queryset.filter(variants__stock__gt=0).distinct()
        elif availability == 'out_of_stock':
            queryset = queryset.exclude(variants__stock__gt=0)
        
        # Special status filtering
        status_filter = self.request.GET.get('status')
        if status_filter == 'featured':
            queryset = queryset.filter(is_featured=True)
        elif status_filter == 'new':
            queryset = queryset.filter(is_new_arrival=True)
        elif status_filter == 'bestseller':
            queryset = queryset.filter(is_bestseller=True)
        elif status_filter == 'on_sale':
            queryset = queryset.filter(discounted_price__isnull=False)
        
        # Search within brand products
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__icontains=search_query)
            )
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = {
            'name': 'name',
            'name_desc': '-name',
            'price_low': 'base_price',
            'price_high': '-base_price',
            'rating': '-avg_rating',
            'rating_asc': 'avg_rating',
            'newest': '-created_at',
            'oldest': 'created_at',
            'popular': '-purchase_count',
            'reviews': '-review_count',
        }
        
        if sort_by in valid_sorts:
            queryset = queryset.order_by(valid_sorts[sort_by])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['brand'] = self.brand
        
        # Get all products for statistics (not filtered)
        all_brand_products = Product.objects.filter(
            status='active',
            brand=self.brand
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        
        # Categories available for this brand
        brand_categories = Category.objects.filter(
            products__brand=self.brand,
            products__status='active'
        ).annotate(
            product_count=Count('products', filter=Q(products__status='active'))
        ).distinct().order_by('name')
        
        # Price range for filtering
        price_stats = all_brand_products.aggregate(
            min_price=Min('base_price'),
            max_price=Max('base_price')
        )
        
        # Filter parameters
        context.update({
            'brand_categories': brand_categories,
            'price_min': price_stats['min_price'] or 0,
            'price_max': price_stats['max_price'] or 1000,
            
            # Current filter values
            'selected_category': self.request.GET.get('category', ''),
            'selected_gender': self.request.GET.get('gender', ''),
            'selected_availability': self.request.GET.get('availability', ''),
            'selected_status': self.request.GET.get('status', ''),
            'selected_sort': self.request.GET.get('sort', '-created_at'),
            'search_query': self.request.GET.get('search', ''),
            'min_price_filter': self.request.GET.get('min_price', ''),
            'max_price_filter': self.request.GET.get('max_price', ''),
            'min_rating_filter': self.request.GET.get('min_rating', ''),
            
            # Statistics
            'total_products': all_brand_products.count(),
            'avg_brand_rating': all_brand_products.aggregate(
                avg=Avg('avg_rating')
            )['avg'],
            'total_reviews': all_brand_products.aggregate(
                total=Count('reviews')
            )['total'],
            
            # Related/suggested brands
            'related_brands': Brand.objects.filter(
                is_active=True,
                country=self.brand.country
            ).exclude(id=self.brand.id).annotate(
                product_count=Count('products', filter=Q(products__status='active'))
            ).filter(product_count__gt=0)[:4],
            
            # Recently viewed (if you have session tracking)
            'recently_viewed': self.request.session.get('recently_viewed_brands', []),
        })
        
        # Handle AJAX requests for dynamic filtering
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string(
                'products/partials/product_cards.html',
                {'products': context['products']},
                request=self.request
            )
            return JsonResponse({
                'html': html,
                'has_next': context['page_obj'].has_next(),
                'total_count': context['paginator'].count
            })
        
        # Track brand view in session
        recently_viewed = self.request.session.get('recently_viewed_brands', [])
        brand_data = {'id': self.brand.id, 'name': self.brand.name, 'slug': self.brand.slug}
        
        if brand_data in recently_viewed:
            recently_viewed.remove(brand_data)
        recently_viewed.insert(0, brand_data)
        
        # Keep only last 10 viewed brands
        self.request.session['recently_viewed_brands'] = recently_viewed[:10]
        
        return context


# Additional utility view for AJAX brand search
class BrandSearchView(ListView):
    """
    AJAX view for brand search autocomplete
    """
    model = Brand
    
    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if len(query) < 2:
            return Brand.objects.none()
        
        return Brand.objects.filter(
            is_active=True,
            name__icontains=query
        ).annotate(
            product_count=Count('products', filter=Q(products__status='active'))
        )[:10]
    
    def render_to_response(self, context, **response_kwargs):
        brands = [{
            'id': brand.id,
            'name': brand.name,
            'slug': brand.slug,
            'product_count': brand.product_count,
            'logo': brand.logo.url if brand.logo else None,
        } for brand in context['object_list']]
        
        return JsonResponse({'brands': brands})

# =====================================================================================================================================================================
# Product Detail View---------------------------------=================================================================================================================
# ===========================================================================================================================================================================

@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache for 15 minutes
class ProductDetailView(DetailView):
    """
    Enhanced product detail view with comprehensive features:
    - Similar products by category and brand
    - Frequently bought together
    - Size guide and fit information
    - Product questions and answers
    - Enhanced variant selection
    - Color-specific images
    - Stock alerts and availability
    """
    model = Product
    template_name = 'products/list/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """Optimize queryset with select_related and prefetch_related"""
        return Product.objects.select_related(
            'brand', 'category', 'category__parent'
        ).prefetch_related(
            'variants__color', 
            'variants__size', 
            'gallery', 
            'gallery__color',
            'reviews__user', 
            'materials',
            'collections',
            'attribute_mappings__attribute_value__attribute',
            'questions__user',
            'questions__answered_by'
        ).filter(status='active')
    
    def get_object(self, queryset=None):
        """Get the product object with error handling"""
        try:
            if queryset is None:
                queryset = self.get_queryset()
            
            slug = self.kwargs.get(self.slug_url_kwarg)
            if slug is None:
                raise AttributeError(
                    f"ProductDetailView must be called with a slug in the URLconf."
                )
            
            return get_object_or_404(queryset, slug=slug)
            
        except Product.DoesNotExist:
            logger.warning(f"Product not found with slug: {self.kwargs.get('slug')}")
            raise Http404("Product not found")
        except Exception as e:
            logger.error(f"Error retrieving product: {str(e)}")
            raise Http404("Product not available")
    
    def get(self, request, *args, **kwargs):
        """Handle GET request with view count increment and recently viewed tracking"""
        try:
            self.object = self.get_object()
            
            # Increment view count atomically
            Product.objects.filter(id=self.object.id).update(
                view_count=F('view_count') + 1
            )
            
            # Track recently viewed for authenticated users
            if request.user.is_authenticated:
                RecentlyViewed.objects.update_or_create(
                    user=request.user,
                    product=self.object,
                    defaults={'viewed_at': timezone.now()}
                )
            
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context)
            
        except Http404:
            raise
        except Exception as e:
            logger.error(f"Error in ProductDetailView GET: {str(e)}")
            raise Http404("Product not available")
    
    def get_context_data(self, **kwargs):
        """Add comprehensive context data"""
        context = super().get_context_data(**kwargs)
        product = self.object
        
        try:
            # Get active variants with optimized queries
            variants = product.variants.filter(is_active=True).select_related('color', 'size')
            context['variants'] = variants
            
            # Variant organization
            context['variants_by_color'] = self._organize_variants_by_color(variants)
            context['variants_by_size'] = self._organize_variants_by_size(variants)
            
            # Get available colors and sizes
            context['colors'] = self._get_available_colors(product)
            context['sizes'] = self._get_available_sizes(product)
            
            # Color-specific images
            context['color_images'] = self._get_color_specific_images(product)
            
            # Product attributes
            context['product_attributes'] = self._get_product_attributes(product)
            
            # Reviews with pagination and statistics
            reviews_data = self._get_reviews_data(product)
            context.update(reviews_data)
            
            # Product questions
            context['questions'] = self._get_product_questions(product)
            
            # Similar and related products
            context['similar_products'] = self._get_similar_products(product)
            context['brand_products'] = self._get_brand_products(product)
            context['frequently_bought_together'] = self._get_frequently_bought_together(product)
            
            # Recently viewed products (for authenticated users)
            if self.request.user.is_authenticated:
                context['recently_viewed'] = self._get_recently_viewed(product)
            
            # Product collections
            context['product_collections'] = product.collections.filter(is_active=True)
            
            # Inventory and availability
            inventory_data = self._get_inventory_data(variants)
            context.update(inventory_data)
            
            # Price analytics
            price_data = self._get_price_data(variants, product)
            context.update(price_data)
            
            # User-specific data (wishlist, purchased status)
            if self.request.user.is_authenticated:
                context.update(self._get_user_specific_data(product))
            
            # SEO and meta data
            context['breadcrumbs'] = self._get_breadcrumbs(product)
            context['meta_data'] = self._get_meta_data(product)
            
        except Exception as e:
            logger.error(f"Error building context for product {product.id}: {str(e)}")
            # Provide minimal context in case of error
            context.update(self._get_fallback_context(product))
        
        return context
    
    def _organize_variants_by_color(self, variants):
        """Organize variants by color for better frontend handling"""
        variants_by_color = {}
        for variant in variants:
            color_name = variant.color.name
            if color_name not in variants_by_color:
                variants_by_color[color_name] = {
                    'color': variant.color,
                    'variants': [],
                    'sizes': []
                }
            variants_by_color[color_name]['variants'].append(variant)
            variants_by_color[color_name]['sizes'].append(variant.size)
        return variants_by_color
    
    def _organize_variants_by_size(self, variants):
        """Organize variants by size"""
        variants_by_size = {}
        for variant in variants:
            size_name = variant.size.name
            if size_name not in variants_by_size:
                variants_by_size[size_name] = {
                    'size': variant.size,
                    'variants': [],
                    'colors': []
                }
            variants_by_size[size_name]['variants'].append(variant)
            variants_by_size[size_name]['colors'].append(variant.color)
        return variants_by_size
    
    def _get_available_colors(self, product):
        """Get available colors for the product"""
        try:
            return product.get_available_colors() if hasattr(product, 'get_available_colors') else \
                   Color.objects.filter(productvariant__product=product, productvariant__is_active=True).distinct()
        except Exception as e:
            logger.error(f"Error getting colors for product {product.id}: {str(e)}")
            return Color.objects.none()
    
    def _get_available_sizes(self, product):
        """Get available sizes for the product"""
        try:
            return product.get_available_sizes() if hasattr(product, 'get_available_sizes') else \
                   Size.objects.filter(productvariant__product=product, productvariant__is_active=True).distinct()
        except Exception as e:
            logger.error(f"Error getting sizes for product {product.id}: {str(e)}")
            return Size.objects.none()
    
    def _get_color_specific_images(self, product):
        """Get color-specific images from gallery"""
        try:
            color_images = {}
            for image in product.gallery.filter(color__isnull=False):
                if image.color.name not in color_images:
                    color_images[image.color.name] = []
                color_images[image.color.name].append(image)
            return color_images
        except Exception as e:
            logger.error(f"Error getting color images for product {product.id}: {str(e)}")
            return {}
    
    def _get_product_attributes(self, product):
        """Get product attributes and values"""
        try:
            attributes = {}
            for mapping in product.attribute_mappings.select_related('attribute_value__attribute'):
                attr_name = mapping.attribute_value.attribute.display_name or mapping.attribute_value.attribute.name
                if attr_name not in attributes:
                    attributes[attr_name] = []
                attributes[attr_name].append(mapping.attribute_value.value)
            return attributes
        except Exception as e:
            logger.error(f"Error getting attributes for product {product.id}: {str(e)}")
            return {}
    
    def _get_reviews_data(self, product):
        """Get review data with pagination and statistics"""
        try:
            approved_reviews = product.reviews.filter(is_approved=True).select_related('user')
            
            # Paginate reviews
            paginator = Paginator(approved_reviews, 5)
            page_number = self.request.GET.get('reviews_page', 1)
            reviews_page = paginator.get_page(page_number)
            
            # Review statistics
            review_stats = approved_reviews.aggregate(
                avg_rating=Avg('rating'),
                total_reviews=Count('id'),
                rating_5=Count('id', filter=Q(rating=5)),
                rating_4=Count('id', filter=Q(rating=4)),
                rating_3=Count('id', filter=Q(rating=3)),
                rating_2=Count('id', filter=Q(rating=2)),
                rating_1=Count('id', filter=Q(rating=1)),
            )
            
            # Calculate rating distribution
            total = review_stats['total_reviews'] or 1
            rating_distribution = {
                5: (review_stats['rating_5'] / total) * 100,
                4: (review_stats['rating_4'] / total) * 100,
                3: (review_stats['rating_3'] / total) * 100,
                2: (review_stats['rating_2'] / total) * 100,
                1: (review_stats['rating_1'] / total) * 100,
            }
            
            return {
                'reviews': reviews_page,
                'review_stats': {
                    'avg_rating': review_stats['avg_rating'] or 0,
                    'total_reviews': review_stats['total_reviews'] or 0,
                    'distribution': rating_distribution
                }
            }
        except Exception as e:
            logger.error(f"Error getting reviews for product {product.id}: {str(e)}")
            return {
                'reviews': [],
                'review_stats': {'avg_rating': 0, 'total_reviews': 0, 'distribution': {}}
            }
    
    def _get_product_questions(self, product):
        """Get product questions and answers"""
        try:
            return product.questions.filter(is_public=True).select_related(
                'user', 'answered_by'
            ).order_by('-created_at')[:10]
        except Exception as e:
            logger.error(f"Error getting questions for product {product.id}: {str(e)}")
            return []
    
    def _get_similar_products(self, product):
        """Get similar products based on category, attributes, and price range"""
        try:
            # Base similar products query
            similar_products = Product.objects.filter(
                status='active'
            ).exclude(id=product.id).select_related('brand', 'category')
            
            # Filter by same category or parent category
            category_filter = Q(category=product.category)
            if product.category.parent:
                category_filter |= Q(category__parent=product.category.parent)
            
            similar_products = similar_products.filter(category_filter)
            
            # Price range filtering (±30% of current product price)
            price = product.get_effective_price()
            price_min = price * 0.7
            price_max = price * 1.3
            
            similar_products = similar_products.filter(
                Q(base_price__range=[price_min, price_max]) |
                Q(discounted_price__range=[price_min, price_max])
            )
            
            # Order by relevance (same brand first, then by popularity)
            return similar_products.annotate(
                same_brand=Case(
                    When(brand=product.brand, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-same_brand', '-purchase_count', '-view_count')[:12]
            
        except Exception as e:
            logger.error(f"Error getting similar products for {product.id}: {str(e)}")
            return Product.objects.none()
    
    def _get_brand_products(self, product):
        """Get other products from the same brand"""
        try:
            return Product.objects.filter(
                brand=product.brand,
                status='active'
            ).exclude(id=product.id).select_related(
                'brand', 'category'
            ).order_by('-purchase_count', '-view_count')[:8]
        except Exception as e:
            logger.error(f"Error getting brand products for {product.id}: {str(e)}")
            return Product.objects.none()
    
    def _get_frequently_bought_together(self, product):
        """Get products frequently bought together (based on order history)"""
        try:
            # This would require order/cart models to implement properly
            # For now, return similar products from same category
            return Product.objects.filter(
                category=product.category,
                status='active'
            ).exclude(id=product.id).order_by('-purchase_count')[:4]
        except Exception as e:
            logger.error(f"Error getting frequently bought together for {product.id}: {str(e)}")
            return Product.objects.none()
    
    def _get_recently_viewed(self, product):
        """Get user's recently viewed products"""
        try:
            return Product.objects.filter(
                recently_viewed__user=self.request.user,
                status='active'
            ).exclude(id=product.id).select_related(
                'brand', 'category'
            ).order_by('-recently_viewed__viewed_at')[:6]
        except Exception as e:
            logger.error(f"Error getting recently viewed for user: {str(e)}")
            return Product.objects.none()
    
    def _get_inventory_data(self, variants):
        """Get comprehensive inventory information"""
        try:
            total_stock = sum(variant.get_available_stock() for variant in variants)
            low_stock_variants = [v for v in variants if v.is_low_stock()]
            out_of_stock_variants = [v for v in variants if not v.is_in_stock()]
            
            return {
                'has_variants': variants.exists(),
                'in_stock': total_stock > 0,
                'total_stock': total_stock,
                'low_stock_variants': low_stock_variants,
                'out_of_stock_variants': out_of_stock_variants,
                'stock_status': 'in_stock' if total_stock > 0 else 'out_of_stock'
            }
        except Exception as e:
            logger.error(f"Error getting inventory data: {str(e)}")
            return {
                'has_variants': False,
                'in_stock': False,
                'total_stock': 0,
                'low_stock_variants': [],
                'out_of_stock_variants': [],
                'stock_status': 'out_of_stock'
            }
    
    def _get_price_data(self, variants, product):
        """Get comprehensive price information"""
        try:
            if variants.exists():
                variant_prices = variants.aggregate(
                    min_price=Min('price'),
                    max_price=Max('price'),
                    min_discounted=Min('discounted_price'),
                    max_discounted=Max('discounted_price')
                )
                
                # Determine effective price range
                min_effective = variant_prices['min_discounted'] or variant_prices['min_price']
                max_effective = variant_prices['max_discounted'] or variant_prices['max_price']
                
                return {
                    'min_price': min_effective,
                    'max_price': max_effective,
                    'price_range': min_effective != max_effective,
                    'variant_prices': variant_prices
                }
            else:
                return {
                    'min_price': product.get_effective_price(),
                    'max_price': product.get_effective_price(),
                    'price_range': False,
                    'variant_prices': {}
                }
        except Exception as e:
            logger.error(f"Error getting price data: {str(e)}")
            return {
                'min_price': 0,
                'max_price': 0,
                'price_range': False,
                'variant_prices': {}
            }
    
    def _get_user_specific_data(self, product):
        """Get user-specific data like wishlist status"""
        try:
            is_in_wishlist = Wishlist.objects.filter(
                user=self.request.user,
                product=product
            ).exists()
            
            # Check if user has purchased this product (would require order models)
            has_purchased = False  # Implement based on your order models
            
            return {
                'is_in_wishlist': is_in_wishlist,
                'has_purchased': has_purchased
            }
        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            return {
                'is_in_wishlist': False,
                'has_purchased': False
            }
    
    def _get_breadcrumbs(self, product):
        """Generate breadcrumb navigation"""
        breadcrumbs = [{'name': 'Home', 'url': '/'}]
        
        # Add category hierarchy
        categories = []
        current_category = product.category
        while current_category:
            categories.append(current_category)
            current_category = current_category.parent
        
        # Reverse to show parent to child
        for category in reversed(categories):
            breadcrumbs.append({
                'name': category.name,
                'url': f'/category/{category.slug}/'
            })
        
        # Add current product (no URL for current page)
        breadcrumbs.append({'name': product.name, 'url': None})
        
        return breadcrumbs
    
    def _get_meta_data(self, product):
        """Get SEO meta data"""
        return {
            'title': product.meta_title or f"{product.name} | {product.brand.name}",
            'description': product.meta_description or product.short_description[:160],
            'keywords': product.tags or f"{product.name}, {product.brand.name}, {product.category.name}",
            'og_image': product.get_primary_image()
        }
    
    def _get_fallback_context(self, product):
        """Provide minimal context in case of errors"""
        return {
            'variants': product.variants.none(),
            'colors': [],
            'sizes': [],
            'reviews': [],
            'review_stats': {'avg_rating': 0, 'total_reviews': 0},
            'similar_products': Product.objects.none(),
            'brand_products': Product.objects.none(),
            'has_variants': False,
            'in_stock': False,
            'min_price': getattr(product, 'base_price', 0),
            'breadcrumbs': [{'name': 'Home', 'url': '/'}, {'name': product.name, 'url': None}]
        }

# ======================================================================================================================================================================================
# Collection Views
class CollectionDetailView(ListView):
    """
    Display products in a collection
    """
    template_name = 'products/list/collection_detail.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        self.collection = get_object_or_404(Collection, slug=self.kwargs['slug'])
        return self.collection.products.filter(status='active').select_related('brand', 'category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.collection
        return context

# Product Variants and AJAX Views
def ajax_product_variants(request, product_id):
    """
    AJAX view to get product variants based on selected color/size
    """
    if request.is_ajax():
        product = get_object_or_404(Product, id=product_id)
        color_id = request.GET.get('color_id')
        size_id = request.GET.get('size_id')
        
        variants = product.variants.filter(is_active=True)
        
        if color_id:
            variants = variants.filter(color_id=color_id)
        if size_id:
            variants = variants.filter(size_id=size_id)
        
        variant_data = []
        for variant in variants:
            variant_data.append({
                'id': variant.id,
                'sku': variant.sku,
                'price': float(variant.get_effective_price()),
                'stock': variant.get_available_stock(),
                'color': variant.color.name,
                'size': variant.size.name,
                'image_url': variant.image.url if variant.image else None,
            })
        
        return JsonResponse({'variants': variant_data})
    
    return JsonResponse({'error': 'Invalid request'})


# Search Suggestions
def search_suggestions(request):
    """
    AJAX view for search autocomplete
    """
    if request.is_ajax():
        query = request.GET.get('q', '')
        if len(query) >= 2:
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(tags__icontains=query),
                status='active'
            )[:10]
            
            suggestions = []
            for product in products:
                suggestions.append({
                    'name': product.name,
                    'url': product.get_absolute_url(),
                    'image': product.gallery.first().image.url if product.gallery.first() else None,
                    'price': float(product.get_effective_price()),
                })
            
            return JsonResponse({'suggestions': suggestions})
    
    return JsonResponse({'suggestions': []})