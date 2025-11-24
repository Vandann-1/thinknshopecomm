"""
URL configuration for sketezo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from .views import *
from customize.views import *


urlpatterns = [
    path('admin/', admin.site.urls),
    path('main_page/',home,name='main_page'),
    path('',include('product.urls')),
    path('dev_mode/',include('dev_mode.urls')),
    path('accounts/',include('accounts.urls')),
    path('product/',include('product.urls')),
    path('components/',include('components.urls')),
    path('cart/',include('cart.urls')),
    path('schedule_purchase/',include('schedule_purchase.urls')),
    path('address/',include('address.urls')),
    path('orders/',include('orders.urls')),
    path('user_orders/',include('user_orders.urls')),
    path('customize/', customize_bottle_view, name='customize-bottle'),
    
    
    path('aboutus',abhout,name='about-us'),
    path('shipping',shipping,name="shipping"),
    path('contact',contact,name="contact")
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
