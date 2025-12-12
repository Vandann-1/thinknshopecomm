from django.urls import path
from . import views


urlpatterns = [
    # Order list and detail
    path('my_orders/', views.order_list, name='my_orders'),
    path('<str:order_id>/', views.order_detail, name='order_detail'),
    
    # Order actions
    path('<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
path('<str:order_id>/reorder/', views.reorder, name='reorder'),
    path('<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    
    # AJAX endpoints
    path('<str:order_id>/status/', views.get_order_status, name='get_order_status'),
]