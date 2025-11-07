from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max, Count, Avg
from django.http import JsonResponse
from django.views.generic import ListView
from django.db import models
from .models import (
    Product, Category, Brand, Color, Size, Material, 
    ProductVariant, Collection, ProductAttribute, ProductAttributeValue,ProductReview
)
from .models import *
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, F,When,Case
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


"""
HomePage View - Additional Context - Provides Better And More Features 
 For Customer

"""
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