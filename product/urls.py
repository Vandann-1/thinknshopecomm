from django.urls import path
from . import views


app_name='products'

urlpatterns=[
    # New Product list Urls 
    path('', views.HomePageView.as_view(), name='home'),
    
    # Product listings
    # Parent - Product List
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Brands
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    path('brand/<slug:slug>/', views.BrandDetailView.as_view(), name='brand-detail'),
    
    # Collections
    path('collection/<slug:slug>/', views.CollectionDetailView.as_view(), name='collection-detail'),
    
    # AJAX endpoints
    path('ajax/variants/<int:product_id>/', views.ajax_product_variants, name='ajax-variants'),
    path('ajax/search-suggestions/', views.search_suggestions, name='search-suggestions'),


    # AJAX endpoints for dynamic filtering - Child - Product List
    path('filter-options/', views.get_filter_options, name='filter-options'),
    # Class-based view
    path('products/quick/<int:product_id>/', 
         views.ProductQuickView.as_view(), 
         name='product-quick-view'),
    
    # Alternative by slug
    path('products/quick/<slug:slug>/', 
         views.ProductQuickView.as_view(), 
         name='product-quick-view-slug'),
    
    # Function-based AJAX view
    path('api/products/<int:product_id>/quick/', 
         views.product_quick_view_ajax, 
         name='product-quick-view-ajax'),
    path('search-suggestions/', views.search_suggestions, name='search-suggestions'),
    
    # Product detail
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Category-specific listings
    path('category/<slug:category_slug>/', views.CategoryProductListView.as_view(), name='category-products'),
    path('brand/<slug:brand_slug>/', views.BrandProductListView.as_view(), name='brand-products'),
    path('collection/<slug:collection_slug>/', views.CollectionProductListView.as_view(), name='collection-products'),
    
    # Wishlist operations
    path('wishlist/grab/<int:product_id>/',views.grabWishList, name='grab_wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add-to-wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove-from-wishlist'),
    
    # Quick add to cart
    path('cart/quick-add/<int:variant_id>/', views.quick_add_to_cart, name='quick-add-to-cart'),
    
    # Product comparison
    path('compare/', views.ProductCompareView.as_view(), name='product-compare'),
    path('compare/add/<int:product_id>/', views.add_to_compare, name='add-to-compare'),
    path('compare/remove/<int:product_id>/', views.remove_from_compare, name='remove-from-compare'),
]