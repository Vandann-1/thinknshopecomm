# urls.py (in your addresses app)
from django.urls import path
from . import views

# app_name = 'addresses'

urlpatterns = [
    # Main address management page
    path('manage_address/', views.address_management, name='manage_address'),
    
    # AJAX endpoints
    path('save/', views.save_address, name='save_address'),
    path('set-default/', views.set_default_address, name='set_default_address'),
    path('delete/', views.delete_address, name='delete_address'),
    path('get-details/', views.get_address_details, name='get_address_details'),
    path('pincode-lookup/', views.get_pincode_data, name='get_pincode_data'),
]

