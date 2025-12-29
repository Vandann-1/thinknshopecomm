from django.urls import path
from . import views


urlpatterns = [
    # Product details and variant selection
    path('products/<int:product_id>/details/', 
         views.get_product_details, 
         name='product-details'),
    
    # Order calculation and review
    path('calculate-total/', 
         views.calculate_order_total, 
         name='calculate-total'),
    
    path('review/', 
         views.order_review, 
         name='order-review'),
    
    # Order creation and payment
    path('create/', 
         views.create_order, 
         name='create-order'),
    
    path('verify-payment/', 
         views.verify_payment, 
         name='verify-payment'),
    
    # Coupon management
    path('apply-coupon/', 
         views.apply_coupon, 
         name='apply-coupon'),
    
    # Address management
    path('address/manage/', 
         views.manage_address, 
         name='manage-address'),
    
    # Stock checking
    path('check-stock/', 
         views.check_stock_availability, 
         name='check-stock'),
    
    # Order management
    path('my-orders/', 
         views.user_orders, 
         name='user-orders'),
    
    path('<str:order_id>/', 
         views.order_detail, 
         name='order-detail'),
    
    path('<str:order_id>/cancel/', 
         views.cancel_order, 
         name='cancel-order'),

     path('complete-payment/<str:order_id>/',views.payment_page, name='complete_payment'),    
]