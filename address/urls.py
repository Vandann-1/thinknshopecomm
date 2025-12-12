# urls.py (in your addresses app)
from django.urls import path
from .views import *

# app_name = 'addresses'

urlpatterns = [
    # Main address management page
    path('manage_address/', AddressManagement.as_view(), name='manage_address'),
    
    # AJAX endpoints
    path('save/', save_address, name='save_address'),
    path('set-default/', set_default_address, name='set_default_address'),
    path('delete/', delete_address, name='delete_address'),
    path('get-details/', get_address_details, name='get_address_details'),
    path('pincode-lookup/', get_pincode_data, name='get_pincode_data'),
]

