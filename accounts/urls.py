from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # mobile otp authentication
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),

    # FORGET PASSWORD
    path(
        'forgot-password/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/authentication/forgot_password.html',
            email_template_name='accounts/authentication/password_reset_email.html',
            subject_template_name='accounts/authentication/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done')
        ),
        name='forgot_password'
    ),

    path(
        'forgot-password-sent/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/authentication/password_reset_sent.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/authentication/reset_password.html'
        ),
        name='password_reset_confirm'
    ),

    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/authentication/password_reset_done.html'
        ),
        name='password_reset_complete'
    ),
]
