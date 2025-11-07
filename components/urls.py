from django.urls import path
from .views import header, footer

urlpatterns=[
    path('header/', header, name='header'),
    path('footer/', footer, name='footer'),
]