from django.urls import path
from . import views
from django.urls import path, include


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    # mobile otp authentication
    path('send-otp/',views.send_otp_view, name='send_otp'),
    path('verify-otp/',views.verify_otp_view, name='verify_otp')
]
