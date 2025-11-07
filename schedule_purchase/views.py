from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.validators import ValidationError
from django.db import transaction
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import json
import logging
from .models import FuturePurchase, FuturePurchaseLog,FuturePurchaseReminder
from product.models import *
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta
import json
from decimal import Decimal
logger = logging.getLogger(__name__)



@login_required
@require_http_methods(["GET"])
def get_product_details(request, product_id):
    """
    Get product details including variants for the future purchase modal
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Get product variants with stock info
        variants_data = []
        for variant in product.variants.filter(is_active=True):
            variants_data.append({
                'id': variant.id,
                'color': variant.color.name,
                'size': variant.size.name,
                'price': str(variant.get_effective_price()),
                'stock_quantity': variant.stock,  # Corrected field name
                'is_in_stock': variant.is_in_stock(),
                'sku': variant.sku,
            })
        
        # Product base information
        product_data = {
            'id': product.id,
            'name': product.name,
            'description': product.description[:200] + '...' if len(product.description) > 200 else product.description,
            'base_price': str(product.get_effective_price()),
            'currency': 'INR',  # Adjust based on your currency setup
            'image_url': product.get_primary_image(),  # Use the model method
            'is_in_stock': product.is_in_stock(),
            'variants': variants_data,
            'has_variants': len(variants_data) > 0,
        }
        
        return JsonResponse({
            'success': True,
            'product': product_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching product details: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch product details'
        }, status=500)


# Main Views 
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_future_purchase(request):
    """
    Create a new future purchase entry
    """
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['product_id', 'scheduled_date', 'quantity']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)
        
        # Get product
        try:
            product = Product.objects.get(id=data['product_id'])
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Product not found'
            }, status=404)
        
        # Get variant if specified
        variant = None
        if data.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(id=data['variant_id'], product=product)
            except ProductVariant.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Product variant not found'
                }, status=404)
        
        # Validate and parse data
        try:
            quantity = int(data['quantity'])
            if quantity < 1:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid quantity'
            }, status=400)
        
        # Parse scheduled date - FIXED VERSION
        try:
            scheduled_date_str = data['scheduled_date']
            
            # Handle different date formats from JavaScript
            if isinstance(scheduled_date_str, str):
                # Remove any milliseconds and handle Z timezone
                if 'T' in scheduled_date_str:
                    # ISO format like "2023-12-25T10:30:00.000Z" or "2023-12-25T10:30:00Z"
                    scheduled_date_str = scheduled_date_str.split('.')[0]  # Remove milliseconds
                    if scheduled_date_str.endswith('Z'):
                        scheduled_date_str = scheduled_date_str[:-1] + '+00:00'
                    scheduled_date = datetime.fromisoformat(scheduled_date_str)
                else:
                    # Try parsing date-only format like "2023-12-25"
                    try:
                        # Parse as date and convert to datetime at start of day
                        from datetime import date
                        date_obj = date.fromisoformat(scheduled_date_str)
                        scheduled_date = datetime.combine(date_obj, datetime.min.time())
                        scheduled_date = timezone.make_aware(scheduled_date)
                    except ValueError:
                        raise ValueError("Invalid date format")
            else:
                raise ValueError("Scheduled date must be a string")
            
            # Ensure timezone awareness
            if scheduled_date.tzinfo is None:
                scheduled_date = timezone.make_aware(scheduled_date)
            
            # Check if date is in the past
            if scheduled_date < timezone.now():
                return JsonResponse({
                    'success': False,
                    'error': 'Scheduled date cannot be in the past'
                }, status=400)
                
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid scheduled date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS) or date format (YYYY-MM-DD). Error: {str(e)}'
            }, status=400)
        
        # Parse optional decimal fields
        max_price = None
        budget_limit = None
        
        if data.get('max_price'):
            try:
                max_price = Decimal(str(data['max_price']))
                if max_price <= 0:
                    raise ValueError("Max price must be positive")
            except (InvalidOperation, ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid max price'
                }, status=400)
        
        if data.get('budget_limit'):
            try:
                budget_limit = Decimal(str(data['budget_limit']))
                if budget_limit <= 0:
                    raise ValueError("Budget limit must be positive")
            except (InvalidOperation, ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid budget limit'
                }, status=400)
        
        # Parse reminder days
        try:
            reminder_days_before = int(data.get('reminder_days_before', 1))
            if reminder_days_before < 0:
                raise ValueError("Reminder days must be non-negative")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid reminder days'
            }, status=400)
        
        # Validate choices
        valid_frequencies = [choice[0] for choice in FuturePurchase.FREQUENCY_CHOICES]
        frequency = data.get('frequency', 'once')
        if frequency not in valid_frequencies:
            return JsonResponse({
                'success': False,
                'error': 'Invalid frequency'
            }, status=400)
        
        valid_actions = [choice[0] for choice in FuturePurchase.ACTION_CHOICES]
        action_type = data.get('action_type', 'reminder')
        if action_type not in valid_actions:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action type'
            }, status=400)
        
        valid_priorities = [choice[0] for choice in FuturePurchase.PRIORITY_CHOICES]
        priority = data.get('priority', 'medium')
        if priority not in valid_priorities:
            return JsonResponse({
                'success': False,
                'error': 'Invalid priority'
            }, status=400)
        
        # Create future purchase with transaction
        with transaction.atomic():
            future_purchase = FuturePurchase.objects.create(
                user=request.user,
                product=product,
                variant=variant,
                title=data.get('title', '').strip() or None,  # Let model generate if empty
                quantity=quantity,
                max_price=max_price,
                notes=data.get('notes', '').strip(),
                scheduled_date=scheduled_date,
                frequency=frequency,
                action_type=action_type,
                reminder_days_before=reminder_days_before,
                send_reminder_email=data.get('send_reminder_email', True),
                auto_purchase_enabled=data.get('auto_purchase_enabled', False),
                check_stock_availability=data.get('check_stock_availability', True),
                use_default_address=data.get('use_default_address', True),
                shipping_address=data.get('shipping_address', '').strip(),
                priority=priority,
                budget_limit=budget_limit,
                max_executions=data.get('max_executions') if data.get('max_executions') else None,
            )
            
            # Create log entry
            FuturePurchaseLog.objects.create(
                future_purchase=future_purchase,
                action_type='created',
                message=f'Future purchase created for {product.name}',
                metadata={
                    'quantity': quantity,
                    'scheduled_date': scheduled_date.isoformat(),
                    'frequency': frequency,
                    'action_type': action_type,
                }
            )
        
        # Prepare response data
        response_data = {
            'success': True,
            'message': 'Future purchase scheduled successfully!',
            'future_purchase': {
                'id': future_purchase.id,
                'title': future_purchase.title,
                'scheduled_date': future_purchase.scheduled_date.isoformat(),
                'quantity': future_purchase.quantity,
                'estimated_total': str(future_purchase.get_estimated_total()),
                'status': future_purchase.status,
                'priority': future_purchase.priority,
            }
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error creating future purchase: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_user_future_purchases(request):
    """
    Get user's future purchases for management
    """
    try:
        future_purchases = FuturePurchase.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('product', 'variant').prefetch_related('logs')
        
        purchases_data = []
        for fp in future_purchases:
            purchases_data.append({
                'id': fp.id,
                'title': fp.title,
                'product_name': fp.product.name,
                'variant_info': f"{fp.variant.color.name} - {fp.variant.size.name}" if fp.variant else None,
                'quantity': fp.quantity,
                'scheduled_date': fp.scheduled_date.isoformat(),
                'frequency': fp.get_frequency_display(),
                'action_type': fp.get_action_type_display(),
                'status': fp.get_status_display(),
                'priority': fp.get_priority_display(),
                'estimated_total': str(fp.get_estimated_total()),
                'can_execute': fp.can_execute()[0],
                'execution_count': fp.execution_count,
                'created_at': fp.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'future_purchases': purchases_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching user future purchases: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch future purchases'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_future_purchase_status(request, purchase_id):
    """
    Update future purchase status (pause, resume, cancel)
    """
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action not in ['pause', 'resume', 'cancel']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action'
            }, status=400)
        
        future_purchase = get_object_or_404(
            FuturePurchase, 
            id=purchase_id, 
            user=request.user
        )
        
        with transaction.atomic():
            if action == 'pause':
                future_purchase.status = 'paused'
                log_message = 'Future purchase paused by user'
            elif action == 'resume':
                future_purchase.status = 'active'
                log_message = 'Future purchase resumed by user'
            elif action == 'cancel':
                future_purchase.status = 'cancelled'
                future_purchase.is_active = False
                log_message = 'Future purchase cancelled by user'
            
            future_purchase.save()
            
            # Create log entry
            FuturePurchaseLog.objects.create(
                future_purchase=future_purchase,
                action_type=action if action != 'resume' else 'resumed',
                message=log_message,
                metadata={'action': action}
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Future purchase {action}d successfully',
            'new_status': future_purchase.get_status_display()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error updating future purchase status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to update future purchase'
        }, status=500)

#============================================================================================================================================================================================================================

"""
Future Purchase Dashboard -
   In the dashboard the user can see all the future purchases they have made

""" 




@login_required
def future_purchase_dashboard(request):
    """
    Main dashboard view for managing future purchases
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    action_filter = request.GET.get('action', 'all')
    priority_filter = request.GET.get('priority', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    purchases = FuturePurchase.objects.filter(user=request.user).select_related(
        'product', 'variant', 'variant__color', 'variant__size'
    )
    
    # Apply filters
    if status_filter != 'all':
        purchases = purchases.filter(status=status_filter)
    
    if action_filter != 'all':
        purchases = purchases.filter(action_type=action_filter)
    
    if priority_filter != 'all':
        purchases = purchases.filter(priority=priority_filter)
    
    if search_query:
        purchases = purchases.filter(
            Q(title__icontains=search_query) |
            Q(product__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Get dashboard statistics
    stats = {
        'total_purchases': purchases.count(),
        'active_purchases': purchases.filter(status='active').count(),
        'completed_purchases': purchases.filter(status='completed').count(),
        'failed_purchases': purchases.filter(status='failed').count(),
        'auto_purchases': purchases.filter(action_type='auto_purchase').count(),
        'total_estimated_value': sum(p.get_estimated_total() for p in purchases),
        'upcoming_this_week': purchases.filter(
            scheduled_date__gte=timezone.now(),
            scheduled_date__lte=timezone.now() + timedelta(days=7),
            status='active'
        ).count(),
    }
    
    # Pagination
    paginator = Paginator(purchases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'purchases': page_obj,
        'stats': stats,
        'status_choices': FuturePurchase.STATUS_CHOICES,
        'action_choices': FuturePurchase.ACTION_CHOICES,
        'priority_choices': FuturePurchase.PRIORITY_CHOICES,
        'frequency_choices': FuturePurchase.FREQUENCY_CHOICES,
        'current_filters': {
            'status': status_filter,
            'action': action_filter,
            'priority': priority_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'future_purchases/dashboard/dashboard.html', context)


@login_required
def get_purchase_details(request, purchase_id):
    """
    AJAX view to get detailed information about a future purchase
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        purchase = get_object_or_404(
            FuturePurchase.objects.select_related('product', 'variant'),
            id=purchase_id,
            user=request.user
        )
        
        # Get recent logs
        recent_logs = purchase.logs.all()[:5]
        
        # Get upcoming reminders
        upcoming_reminders = purchase.reminders.filter(
            status='pending',
            scheduled_for__gte=timezone.now()
        )[:3]
        
        data = {
            'id': purchase.id,
            'title': purchase.title,
            'product_name': purchase.product.name,
            'variant_info': f"{purchase.variant.color.name} - {purchase.variant.size.name}" if purchase.variant else None,
            'quantity': purchase.quantity,
            'scheduled_date': purchase.scheduled_date.strftime('%Y-%m-%d %H:%M'),
            'frequency': purchase.get_frequency_display(),
            'action_type': purchase.get_action_type_display(),
            'status': purchase.get_status_display(),
            'priority': purchase.get_priority_display(),
            'estimated_total': float(purchase.get_estimated_total()),
            'max_price': float(purchase.max_price) if purchase.max_price else None,
            'notes': purchase.notes,
            'execution_count': purchase.execution_count,
            'next_execution_date': purchase.next_execution_date.strftime('%Y-%m-%d %H:%M') if purchase.next_execution_date else None,
            'budget_limit': float(purchase.budget_limit) if purchase.budget_limit else None,
            'spent_amount': float(purchase.spent_amount),
            'can_execute': purchase.can_execute(),
            'recent_logs': [
                {
                    'action_type': log.get_action_type_display(),
                    'message': log.message,
                    'created_at': log.created_at.strftime('%Y-%m-%d %H:%M'),
                }
                for log in recent_logs
            ],
            'upcoming_reminders': [
                {
                    'type': reminder.get_reminder_type_display(),
                    'scheduled_for': reminder.scheduled_for.strftime('%Y-%m-%d %H:%M'),
                    'subject': reminder.subject,
                }
                for reminder in upcoming_reminders
            ]
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def update_purchase_status(request, purchase_id):
    """
    AJAX view to update purchase status
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        purchase = get_object_or_404(FuturePurchase, id=purchase_id, user=request.user)
        new_status = request.POST.get('status')
        
        if new_status not in dict(FuturePurchase.STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        old_status = purchase.status
        purchase.status = new_status
        purchase.save()
        
        # Create log entry
        FuturePurchaseLog.objects.create(
            future_purchase=purchase,
            action_type='updated',
            message=f'Status changed from {old_status} to {new_status}',
            metadata={'old_status': old_status, 'new_status': new_status}
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {purchase.get_status_display()}',
            'new_status': purchase.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def toggle_purchase_active(request, purchase_id):
    """
    AJAX view to toggle purchase active status
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        purchase = get_object_or_404(FuturePurchase, id=purchase_id, user=request.user)
        purchase.is_active = not purchase.is_active
        purchase.save()
        
        action = 'resumed' if purchase.is_active else 'paused'
        FuturePurchaseLog.objects.create(
            future_purchase=purchase,
            action_type=action,
            message=f'Purchase {action} by user',
        )
        
        return JsonResponse({
            'success': True,
            'is_active': purchase.is_active,
            'message': f'Purchase {"activated" if purchase.is_active else "paused"}'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def delete_purchase(request, purchase_id):
    """
    AJAX view to delete a future purchase
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        purchase = get_object_or_404(FuturePurchase, id=purchase_id, user=request.user)
        purchase_title = purchase.title
        purchase.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'"{purchase_title}" has been deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_dashboard_stats(request):
    """
    AJAX view to get updated dashboard statistics
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        purchases = FuturePurchase.objects.filter(user=request.user)
        
        stats = {
            'total_purchases': purchases.count(),
            'active_purchases': purchases.filter(status='active').count(),
            'completed_purchases': purchases.filter(status='completed').count(),
            'failed_purchases': purchases.filter(status='failed').count(),
            'auto_purchases': purchases.filter(action_type='auto_purchase').count(),
            'total_estimated_value': float(sum(p.get_estimated_total() for p in purchases)),
            'upcoming_this_week': purchases.filter(
                scheduled_date__gte=timezone.now(),
                scheduled_date__lte=timezone.now() + timedelta(days=7),
                status='active'
            ).count(),
        }
        
        return JsonResponse({'success': True, 'stats': stats})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)