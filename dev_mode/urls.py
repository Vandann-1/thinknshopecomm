from django.urls import path
from .views import dev_notice

urlpatterns =[
    path('sketezo_development/',dev_notice, name='sketezo_development'),
]