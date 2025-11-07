
from django.urls import path
from . import views

# Future Purchase API URLs
urlpatterns = [

    
    # Future Purchase APIs
    path('api/products/<int:product_id>/details/', 
         views.get_product_details, 
         name='get_product_details'),
    
    path('api/future-purchases/create/', 
         views.create_future_purchase, 
         name='create_future_purchase'),
    
    path('api/future-purchases/user/', 
         views.get_user_future_purchases, 
         name='get_user_future_purchases'),
    
    path('api/future-purchases/<int:purchase_id>/status/', 
         views.update_future_purchase_status, 
         name='update_future_purchase_status'),

    # Future Purchase Dashboard APIs
    path('future_purchase_dashboard/', views.future_purchase_dashboard, name='future_purchase_dashboard'),
    
    # AJAX endpoints
    path('details/<int:purchase_id>/', views.get_purchase_details, name='get_purchase_details'),
    path('update-status/<int:purchase_id>/', views.update_purchase_status, name='update_purchase_status'),
    path('toggle-active/<int:purchase_id>/', views.toggle_purchase_active, name='toggle_purchase_active'),
    path('delete/<int:purchase_id>/', views.delete_purchase, name='delete_purchase'),
    path('stats/', views.get_dashboard_stats, name='get_dashboard_stats'),
    
    # Additional AJAX endpoints for future features
    # path('create/', views.create_purchase, name='create_purchase'),
    # path('edit/<int:purchase_id>/', views.edit_purchase, name='edit_purchase'),
    # path('execute/<int:purchase_id>/', views.execute_purchase, name='execute_purchase'),
    # path('send-reminder/<int:purchase_id>/', views.send_reminder, name='send_reminder'),
    # path('bulk-actions/', views.bulk_actions, name='bulk_actions'),  
]