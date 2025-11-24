from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required

@csrf_protect
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Basic validation
        if not all([username, email, password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return render(request, 'auth/register.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'auth/register.html')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/register.html')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/register.html')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None
            )
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, 'Error creating account. Please try again.')
            return render(request, 'auth/register.html')
    
    return render(request, 'accounts/authentication/register.html')

@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')  # Redirect if already logged in
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'auth/login.html')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect to next page if provided, otherwise to home
            next_page = request.POST.get('next') or request.GET.get('next') or '/'
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/authentication/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.first_name or request.user.username
        logout(request)
        messages.success(request, f' {username}! You have been logged out.')
    return redirect('/')



# Optional: Profile view to show user info
@login_required
def profile_view(request):
    return render(request, 'accounts/authentication/profile.html', {'user': request.user})



# ===================================MOBILE AUTHENTICATION =========================================================================================
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import PhoneOTP
from .utils import send_otp
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt 
def send_otp_view(request):     
    if request.method == "POST":         
        try:             
            data = json.loads(request.body)             
            phone = data.get("phone_number")         
        except Exception:             
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)          
        
        if not phone:             
            return JsonResponse({"success": False, "error": "Phone number required"}, status=400)          
        
        try:
            otp_obj, created = PhoneOTP.objects.get_or_create(phone=phone)         
            otp = otp_obj.generate_otp()         
            send_otp(phone, otp)          
            return JsonResponse({"success": True, "message": "OTP sent!"})
        except Exception as e:
            return JsonResponse({"success": False, "error" :"Failed to send OTP"}, status=500)
    
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)   


@csrf_exempt 
def verify_otp_view(request):     
    if request.method == "POST":         
        try:             
            data = json.loads(request.body)             
            phone = data.get("phone_number")             
            otp = data.get("otp")         
        except Exception:             
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)          
        
        if not phone or not otp:             
            return JsonResponse({"success": False, "error": "Phone and OTP required"}, status=400)          
        
        try:             
            otp_obj = PhoneOTP.objects.get(phone=phone, otp=otp)         
        except PhoneOTP.DoesNotExist:             
            return JsonResponse({"success": False, "error": "Invalid OTP"}, status=400)          
        
        # ✅ Login or create user         
        user, created = User.objects.get_or_create(username=phone)         
        login(request, user)          
        
        return JsonResponse({             
            "success": True,             
            "message": "Login success!",             
            "redirect_url": "/"         
        })      
    
    return JsonResponse({"success" : False, "error": "Invalid request"}, status=400)
