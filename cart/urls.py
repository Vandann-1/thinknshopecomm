# Add these URLs to your urlpatterns in urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ... your existing URLs ...
    
    # Cart URLs
    path('cart/fill-product/<int:product_id>/', views.fill_product_into_cart, name='fill_product_into_cart'),
    path('cart/add-variant/', views.add_variant_to_cart, name='add_variant_to_cart'),
    path('cart/summary/', views.get_cart_summary, name='get_cart_summary'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update-quantity/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    
    # 
    path('cart/', views.cart_view, name='cart_view'),
    
    # Cart actions
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    
    # AJAX endpoints
    path('count/', views.get_cart_count, name='get_cart_count'),

]