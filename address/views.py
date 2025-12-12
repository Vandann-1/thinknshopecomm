# views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db import transaction
import json
import requests
from .models import Address, PincodeData
from django.views import View


# Address Management View
@login_required
def address_management(request):
    """
    Main address management view
    """
    addresses = Address.objects.filter(user=request.user, is_active=True)
    
    context = {
        'addresses': addresses,
        'page_title': 'Manage Addresses'
    }
    return render(request, 'address/manage/address_management.html', context)


# Address Management View
@login_required
def address_management(request):
    """
    Main address management view
    """
 
    
    data = {
        'success': 'ok'
    }
    # return render(request, 'address/manage/address_management.html', context)
    return JsonResponse(data=data)  # Placeholder for actual rendering

@method_decorator(login_required,name='dispatch')
class AddressManagement(View):
    
    def get(self, request):
        addresses = Address.objects.filter(user=request.user, is_active=True)
        context = {
            'addresses': addresses,
            'page_title': 'Manage Addresses'
        }
        return render(request, 'address/manage/address_management.html', context)   
    def post(self, request):
        data = {
            'success': 'ok'
        }
        return JsonResponse(data=data)  # Placeholder for actual rendering


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def save_address(request):
    """
    Save new address or update existing one
    """
    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        
        # Validate required fields
        required_fields = ['full_name', 'phone_number', 'address_line_1', 'pincode', 'city', 'state']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False, 
                    'error': f'{field.replace("_", " ").title()} is required'
                })
        
        with transaction.atomic():
            if address_id:
                # Update existing address
                address = get_object_or_404(Address, id=address_id, user=request.user)
            else:
                # Create new address
                address = Address(user=request.user)
            
            # Update fields
            address.label = data.get('label', 'Home')
            address.address_type = data.get('address_type', 'home')
            address.full_name = data['full_name']
            address.phone_number = data['phone_number']
            address.alternate_phone = data.get('alternate_phone', '')
            address.address_line_1 = data['address_line_1']
            address.address_line_2 = data.get('address_line_2', '')
            address.landmark = data.get('landmark', '')
            address.pincode = data['pincode']
            address.city = data['city']
            address.state = data['state']
            address.country = data.get('country', 'India')
            address.delivery_instructions = data.get('delivery_instructions', '')
            address.is_apartment = data.get('is_apartment', False)
            address.floor_number = data.get('floor_number', '')
            address.is_default = data.get('is_default', False)
            
            address.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Address saved successfully',
                'address': {
                    'id': str(address.id),
                    'label': address.label,
                    'full_name': address.full_name,
                    'phone_number': address.phone_number,
                    'short_address': address.get_short_address(),
                    'full_address': address.get_full_address(),
                    'is_default': address.is_default
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def set_default_address(request):
    """
    Set an address as default
    """
    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        
        if not address_id:
            return JsonResponse({'success': False, 'error': 'Address ID is required'})
        
        with transaction.atomic():
            # Get the address
            address = get_object_or_404(Address, id=address_id, user=request.user)
            
            # Set as default (model's save method handles unsetting others)
            address.is_default = True
            address.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Default address updated successfully'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_address(request):
    """
    Soft delete an address
    """
    try:
        data = json.loads(request.body)
        address_id = data.get('address_id')
        
        if not address_id:
            return JsonResponse({'success': False, 'error': 'Address ID is required'})
        
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Don't allow deletion of default address if it's the only one
        if address.is_default:
            other_addresses = Address.objects.filter(
                user=request.user, 
                is_active=True
            ).exclude(id=address_id)
            
            if other_addresses.exists():
                # Make another address default
                other_addresses.first().is_default = True
                other_addresses.first().save()
        
        # Soft delete
        address.is_active = False
        address.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Address deleted successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def get_pincode_data(request):
    """
    Get pincode data from cache or API
    """
    pincode = request.GET.get('pincode')
    
    if not pincode:
        return JsonResponse({'success': False, 'error': 'Pincode is required'})
    
    # Check cache first
    try:
        pincode_data = PincodeData.objects.get(pincode=pincode)
        return JsonResponse({
            'success': True,
            'data': {
                'city': pincode_data.city,
                'state': pincode_data.state,
                'district': pincode_data.district,
                'area': pincode_data.area,
                'is_serviceable': pincode_data.is_serviceable,
                'delivery_days': pincode_data.delivery_days,
                'cod_available': pincode_data.cod_available
            }
        })
    except PincodeData.DoesNotExist:
        pass
    
    # Fetch from API (using India Post API as example)
    try:
        api_url = f"https://api.postalpincode.in/pincode/{pincode}"
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            api_data = response.json()
            
            if api_data and api_data[0]['Status'] == 'Success':
                post_office = api_data[0]['PostOffice'][0]
                
                # Cache the data
                pincode_obj, created = PincodeData.objects.get_or_create(
                    pincode=pincode,
                    defaults={
                        'city': post_office['District'],
                        'state': post_office['State'],
                        'district': post_office['District'],
                        'area': post_office['Name'],
                        'country': 'India'
                    }
                )
                
                return JsonResponse({
                    'success': True,
                    'data': {
                        'city': pincode_obj.city,
                        'state': pincode_obj.state,
                        'district': pincode_obj.district,
                        'area': pincode_obj.area,
                        'is_serviceable': pincode_obj.is_serviceable,
                        'delivery_days': pincode_obj.delivery_days,
                        'cod_available': pincode_obj.cod_available
                    }
                })
            else:
                return JsonResponse({'success': False, 'error': 'Invalid pincode'})
        else:
            return JsonResponse({'success': False, 'error': 'API request failed'})
            
    except requests.RequestException:
        return JsonResponse({'success': False, 'error': 'Unable to fetch pincode data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
@login_required
def get_address_details(request):
    """
    Get detailed address information for editing
    """
    address_id = request.GET.get('address_id')
    
    if not address_id:
        return JsonResponse({'success': False, 'error': 'Address ID is required'})
    
    try:
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'address': {
                'id': str(address.id),
                'label': address.label,
                'address_type': address.address_type,
                'full_name': address.full_name,
                'phone_number': address.phone_number,
                'alternate_phone': address.alternate_phone or '',
                'address_line_1': address.address_line_1,
                'address_line_2': address.address_line_2 or '',
                'landmark': address.landmark or '',
                'pincode': address.pincode,
                'city': address.city,
                'state': address.state,
                'country': address.country,
                'delivery_instructions': address.delivery_instructions or '',
                'is_apartment': address.is_apartment,
                'floor_number': address.floor_number or '',
                'is_default': address.is_default
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})