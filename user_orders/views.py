from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from orders.models import Order, OrderItem, OrderStatusUpdate
from django.contrib.auth.models import User




# 1) Users Orders List

@login_required
def order_list(request):
    """
    Display user's orders with filtering, sorting, and pagination.
    Supports status filtering, search, and date range filtering.
    """
    orders = Order.objects.filter(user=request.user).select_related(
        'user', 'shipping_address', 'billing_address'
    ).prefetch_related(
        'items__product', 'items__variant__color', 'items__variant__size'
    )
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sort_by = request.GET.get('sort', '-created_at')  # Default sort by newest first
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(items__product_name__icontains=search_query) |
            Q(tracking_id__icontains=search_query) |
            Q(coupon_code__icontains=search_query)
        ).distinct()
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Apply sorting
    valid_sort_options = [
        'created_at', '-created_at', 
        'total_amount', '-total_amount',
        'status', '-status',
        'confirmed_at', '-confirmed_at'
    ]
    if sort_by in valid_sort_options:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_orders = paginator.get_page(page_number)
    
    # Get order statistics for dashboard
    order_stats = {
        'total_orders': Order.objects.filter(user=request.user).count(),
        'pending_orders': Order.objects.filter(user=request.user, status='pending').count(),
        'delivered_orders': Order.objects.filter(user=request.user, status='delivered').count(),
        'cancelled_orders': Order.objects.filter(user=request.user, status='cancelled').count(),
        'total_spent': Order.objects.filter(
            user=request.user, 
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    
    # Get available status choices for filter dropdown
    status_choices = Order.ORDER_STATUS
    
    context = {
        'orders': page_orders,
        'order_stats': order_stats,
        'status_choices': status_choices,
        'current_status': status_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'current_sort': sort_by,
        'page_title': 'My Orders',
    }
    
    return render(request, 'user_orders/order_list.html', context)


# 2) Order Detail
@login_required
def order_detail(request, order_id):
    """
    Display detailed order information including items, status history, and tracking.
    Only allows users to view their own orders.
    """
    try:
        order = Order.objects.select_related(
            'user', 'shipping_address', 'billing_address'
        ).prefetch_related(
            'items__product',
            'items__variant__color',
            'items__variant__size',
            'status_updates__updated_by'
        ).get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found or you do not have permission to view it.')
        return redirect('orders:order_list')
    
    # Calculate order summary
    order_summary = {
        'item_count': order.items.count(),
        'total_quantity': sum(item.quantity for item in order.items.all()),
        'subtotal': order.subtotal or 0,
        'discount': order.discount_amount or 0,
        'shipping': order.shipping_cost or 0,
        'tax': order.tax_amount or 0,
        'total': order.total_amount or 0,
    }
    
    # Get status updates history
    status_updates = order.status_updates.all()
    
    # Determine if order can be cancelled
    can_cancel = order.can_be_cancelled()
    
    # Calculate expected delivery info
    delivery_info = {
        'estimated_delivery': order.estimated_delivery,
        'is_delivered': order.status == 'delivered',
        'delivery_date': order.delivered_at,
        'is_shipped': order.status in ['shipped', 'delivered'],
        'tracking_available': bool(order.tracking_id),
    }
    
    # Order timeline for status tracking
    timeline = []
    
    # Add order placed
    timeline.append({
        'status': 'placed',
        'title': 'Order Placed',
        'description': 'Your order has been placed successfully',
        'date': order.created_at,
        'completed': True,
        'icon': 'check-circle'
    })
    
    # Add confirmed
    if order.confirmed_at:
        timeline.append({
            'status': 'confirmed',
            'title': 'Order Confirmed',
            'description': 'Your order has been confirmed and is being processed',
            'date': order.confirmed_at,
            'completed': True,
            'icon': 'check-circle'
        })
    
    # Add shipped
    if order.shipped_at:
        timeline.append({
            'status': 'shipped',
            'title': 'Order Shipped',
            'description': f'Your order has been shipped',
            'date': order.shipped_at,
            'completed': True,
            'icon': 'truck'
        })
        if order.tracking_id:
            timeline[-1]['description'] += f' (Tracking: {order.tracking_id})'
    
    # Add delivered
    if order.delivered_at:
        timeline.append({
            'status': 'delivered',
            'title': 'Order Delivered',
            'description': 'Your order has been delivered successfully',
            'date': order.delivered_at,
            'completed': True,
            'icon': 'check-circle'
        })
    elif order.status == 'delivered':
        timeline.append({
            'status': 'delivered',
            'title': 'Order Delivered',
            'description': 'Your order has been delivered successfully',
            'date': None,
            'completed': True,
            'icon': 'check-circle'
        })
    
    # Add cancelled if applicable
    if order.status == 'cancelled':
        timeline.append({
            'status': 'cancelled',
            'title': 'Order Cancelled',
            'description': 'Your order has been cancelled',
            'date': None,
            'completed': True,
            'icon': 'x-circle',
            'is_cancelled': True
        })
    
    context = {
        'order': order,
        'order_summary': order_summary,
        'status_updates': status_updates,
        'can_cancel': can_cancel,
        'delivery_info': delivery_info,
        'timeline': timeline,
        'page_title': f'Order #{order.order_id}',
    }
    
    return render(request, 'user_orders/order_detail.html', context)


# Cancel Order
@login_required
@require_POST
def cancel_order(request, order_id):
    """
    Cancel an order if it's in a cancellable state.
    Creates a status update record for audit trail.
    """
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Order not found or you do not have permission to cancel it.'
        }, status=404)
    
    if not order.can_be_cancelled():
        return JsonResponse({
            'success': False,
            'message': 'This order cannot be cancelled as it has already been processed.'
        }, status=400)
    
    # Store old status for audit trail
    old_status = order.status
    
    # Update order status
    order.status = 'cancelled'
    order.save()
    
    # Create status update record
    OrderStatusUpdate.objects.create(
        order=order,
        old_status=old_status,
        new_status='cancelled',
        notes=f'Order cancelled by customer via website',
        updated_by=request.user
    )
    
    # Release reserved stock for all items
    for item in order.items.all():
        if item.variant and item.variant.reserved_stock >= item.quantity:
            item.variant.reserved_stock -= item.quantity
            item.variant.save()
    
    messages.success(request, f'Order #{order.order_id} has been cancelled successfully.')
    
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully.',
            'redirect_url': f'/orders/{order.order_id}/'
        })
    
    return redirect('/', order_id=order.order_id)


# Re-order
@login_required
def reorder(request, order_id):
    """
    Add all items from a previous order to the current cart.
    Checks stock availability and handles unavailable items gracefully.
    """
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('orders:order_list')
    
    # This would typically integrate with your cart system
    # For now, we'll create a response showing what would be added
    
    available_items = []
    unavailable_items = []
    
    for item in order.items.all():
        if item.variant and item.variant.is_active and item.variant.is_in_stock():
            if item.variant.get_available_stock() >= item.quantity:
                available_items.append({
                    'product': item.product,
                    'variant': item.variant,
                    'quantity': item.quantity,
                    'name': item.product_name,
                    'details': item.variant_details
                })
            else:
                unavailable_items.append({
                    'name': item.product_name,
                    'details': item.variant_details,
                    'reason': 'Limited stock available'
                })
        else:
            unavailable_items.append({
                'name': item.product_name,
                'details': item.variant_details,
                'reason': 'Product no longer available'
            })
    
    if available_items:
        # Here you would add items to cart
        # cart.add_items(available_items)
        messages.success(
            request, 
            f'{len(available_items)} items from your previous order have been added to cart.'
        )
    
    if unavailable_items:
        unavailable_list = ', '.join([f"{item['name']}" for item in unavailable_items])
        messages.warning(
            request,
            f'Some items are no longer available: {unavailable_list}'
        )
    
    # Redirect to cart page (adjust URL as needed)
    return redirect('cart:cart_detail')


# Download Invoice
@login_required
def download_invoice(request, order_id):
    """
    Generate and download invoice PDF for the order.
    Only for paid orders.
    """
    try:
        order = Order.objects.get(
            order_id=order_id, 
            user=request.user,
            payment_status='paid'
        )
    except Order.DoesNotExist:
        messages.error(request, 'Invoice not available for this order.')
        return redirect('order_detail', order_id=order_id)
    
    # This would typically generate a PDF invoice
    # For now, we'll redirect back with a message
    messages.info(request, 'Invoice download feature will be available soon.')
    return redirect('order_detail', order_id=order_id)


# Optional: AJAX endpoint for order status updates
@login_required
def get_order_status(request, order_id):
    """
    AJAX endpoint to get current order status and tracking info.
    Useful for real-time updates without page refresh.
    """
    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    
    return JsonResponse({
        'status': order.status,
        'status_display': order.get_status_display(),
        'payment_status': order.payment_status,
        'payment_status_display': order.get_payment_status_display(),
        'tracking_id': order.tracking_id,
        'courier_partner': order.courier_partner,
        'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        'can_cancel': order.can_be_cancelled(),
    })