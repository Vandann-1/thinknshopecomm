from django.shortcuts import render
from .models import *
from product.models import *
from address.models import Address
from discount.models import Discount
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from decimal import Decimal
import json
from datetime import datetime
import razorpay
from django.conf import settings
from django.views.decorators.http import require_http_methods,require_POST
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
import logging
from django.urls import reverse_lazy

# Set up logger
logger = logging.getLogger(__name__)
# Views
# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# GET PRODUCT DETAILS FOR ORDERING=============================================================================================



"""
1) GET PRODUCT DETAILS - SO THAT USER WILL SELECT THE VARIANT ETC
"""
@login_required
@require_http_methods(["GET", "POST"])
def get_product_details(request, product_id):
    """
    AJAX endpoint to get product variants, pricing, and availability
    """
    try:
        product = get_object_or_404(Product, id=product_id, status='active')
        
        # Get all active variants
        variants = ProductVariant.objects.filter(
            product=product, 
            is_active=True
        ).select_related('color', 'size')
        
        # Build response data
        colors = []
        sizes = []
        variant_data = {}
        
        for variant in variants:
            # Collect unique colors
            color_info = {
                'id': variant.color.id,
                'name': variant.color.name,
                'hex_code': variant.color.hex_code
            }
            if color_info not in colors:
                colors.append(color_info)
            
            # Collect unique sizes
            size_info = {
                'id': variant.size.id,
                'name': variant.size.name,
                'category': variant.size.category
            }
            if size_info not in sizes:
                sizes.append(size_info)
            
            # Store variant details
            variant_key = f"{variant.color.id}_{variant.size.id}"
            variant_data[variant_key] = {
                'id': variant.id,
                'sku': variant.sku,
                'price': str(variant.price),
                'discounted_price': str(variant.discounted_price) if variant.discounted_price else None,
                'effective_price': str(variant.get_effective_price()),
                'stock': variant.get_available_stock(),
                'is_in_stock': variant.is_in_stock(),
                'is_low_stock': variant.is_low_stock(),
                'image_url': variant.image.url if variant.image else None
            }
        
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'base_price': str(product.base_price),
                'discounted_price': str(product.discounted_price) if product.discounted_price else None,
                'discount_percent': product.get_discount_percent(),
                'total_stock': product.get_total_stock()
            },
            'colors': colors,
            'sizes': sizes,
            'variants': variant_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# Calculate the price
@login_required
@require_POST
@csrf_exempt
def calculate_order_total(request):
    """
    AJAX endpoint to calculate order total based on selections
    """
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        quantity = int(data.get('quantity', 1))
        coupon_code = data.get('coupon_code', '').strip()
        address_id = data.get('address_id')
        
        # Validate variant
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        
        if quantity <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Invalid quantity'
            }, status=400)
        
        if quantity > variant.get_available_stock():
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.get_available_stock()} items available'
            }, status=400)
        
        # Calculate base amounts
        unit_price = variant.get_effective_price()
        subtotal = unit_price * quantity
        
        # Calculate shipping (basic logic - you can enhance this)
        shipping_cost = Decimal('0.00')
        if subtotal < Decimal('500.00'):  # Free shipping above ₹500
            shipping_cost = Decimal('50.00')
        
        # Apply discount if coupon provided
        discount_amount = Decimal('0.00')
        discount_info = None
        
        if coupon_code:
            try:
                discount = Discount.objects.get(code=coupon_code)
                if discount.is_valid(user=request.user, order_total=subtotal):
                    new_total, discount_amount = discount.apply_discount(subtotal, request.user)
                    discount_info = {
                        'code': discount.code,
                        'type': discount.discount_type,
                        'value': str(discount.value),
                        'discount_amount': str(discount_amount)
                    }
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid or expired coupon code'
                    }, status=400)
            except Discount.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Coupon code not found'
                }, status=400)
        
        # Calculate tax (18% GST example)
        taxable_amount = subtotal - discount_amount + shipping_cost
        tax_amount = taxable_amount * Decimal('0.05')
        
        # Final total
        total_amount = subtotal - discount_amount + shipping_cost + tax_amount
        
        return JsonResponse({
            'success': True,
            'pricing': {
                'unit_price': str(unit_price),
                'quantity': quantity,
                'subtotal': str(subtotal),
                'discount_amount': str(discount_amount),
                'shipping_cost': str(shipping_cost),
                'tax_amount': str(tax_amount),
                'total_amount': str(total_amount)
            },
            'discount': discount_info,
            'variant': {
                'id': variant.id,
                'name': f"{variant.product.name} - {variant.color.name}, {variant.size.name}",
                'sku': variant.sku,
                'available_stock': variant.get_available_stock()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# 2) ORDER REVIEW PAGE 
@login_required
@csrf_exempt
def order_review(request):
    """
    Order review page - GET: show review, POST: create order
    """
    logger.info(f"Order review accessed by user {request.user.id} with method {request.method}")
    
    if request.method == 'GET':
        try:
            # Get order details from session or parameters
            variant_id = request.GET.get('variant_id')
            quantity = int(request.GET.get('quantity', 1))
            coupon_code = request.GET.get('coupon_code', '')
            address_id = request.GET.get('address_id')
            
            logger.info(f"Order review GET parameters - User: {request.user.id}, "
                       f"variant_id: {variant_id}, quantity: {quantity}, "
                       f"coupon_code: {coupon_code}, address_id: {address_id}")
            
            # Validate required parameters
            if not variant_id:
                logger.warning(f"Missing variant_id for user {request.user.id}")
                messages.error(request, 'Invalid product selection')
                return redirect('products:product-list')
            
            # Validate quantity
            if quantity <= 0:
                logger.warning(f"Invalid quantity {quantity} for user {request.user.id}")
                messages.error(request, 'Invalid quantity specified')
                return redirect('products:product-list')
            
            try:
                variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
                logger.info(f"Found variant {variant.id} - {variant.product.name}")
            except Exception as e:
                logger.error(f"Error fetching variant {variant_id}: {str(e)}")
                messages.error(request, 'Product variant not found or not available')
                return redirect('products:product-list')
            
            # Check stock availability
            if hasattr(variant, 'stock') and variant.stock < quantity:
                logger.warning(f"Insufficient stock for variant {variant_id}. Requested: {quantity}, Available: {variant.stock}")
                messages.error(request, f'Only {variant.stock} items available in stock')
                return redirect('products:product-detail', variant.product.slug)
            
            # Calculate pricing
            try:
                unit_price = variant.get_effective_price()
                subtotal = unit_price * quantity
                shipping_cost = Decimal('50.00') if subtotal < Decimal('500.00') else Decimal('0.00')
                discount_amount = Decimal('0.00')
                discount = None
                
                logger.info(f"Pricing calculated - unit_price: {unit_price}, subtotal: {subtotal}, shipping: {shipping_cost}")
                
            except Exception as e:
                logger.error(f"Error calculating pricing for variant {variant_id}: {str(e)}")
                messages.error(request, 'Error calculating product pricing')
                return redirect('products:product-list')
            
            # Apply coupon if provided
            if coupon_code:
                try:
                    discount = Discount.objects.get(code=coupon_code, is_active=True)
                    logger.info(f"Attempting to apply coupon: {coupon_code}")
                    
                    if discount.is_valid(user=request.user, order_total=subtotal):
                        original_total = subtotal
                        new_total, discount_amount = discount.apply_discount(subtotal, request.user)
                        logger.info(f"Coupon {coupon_code} applied successfully. "
                                   f"Original: {original_total}, Discount: {discount_amount}, New total: {new_total}")
                    else:
                        logger.warning(f"Coupon {coupon_code} is not valid for user {request.user.id}")
                        messages.warning(request, 'Coupon is not valid or has expired')
                        
                except Discount.DoesNotExist:
                    logger.warning(f"Invalid coupon code attempted: {coupon_code} by user {request.user.id}")
                    messages.warning(request, 'Invalid coupon code')
                except Exception as e:
                    logger.error(f"Error applying coupon {coupon_code}: {str(e)}")
                    messages.warning(request, 'Error applying coupon code')
            
            # Calculate tax and total
            try:
                taxable_amount = subtotal - discount_amount + shipping_cost
                tax_amount = taxable_amount * Decimal('0.05')  # 18% tax
                total_amount = subtotal - discount_amount + shipping_cost + tax_amount
                
                logger.info(f"Final calculations - taxable_amount: {taxable_amount}, "
                           f"tax_amount: {tax_amount}, total_amount: {total_amount}")
                
            except Exception as e:
                logger.error(f"Error calculating tax and total: {str(e)}")
                messages.error(request, 'Error calculating order total')
                return redirect('products:product-list')
            
            # Get user addresses
            try:
                addresses = Address.objects.filter(user=request.user, is_active=True)
                selected_address = None
                
                if address_id:
                    selected_address = addresses.filter(id=address_id).first()
                    if selected_address:
                        logger.info(f"Selected address {address_id} for user {request.user.id}")
                    else:
                        logger.warning(f"Address {address_id} not found for user {request.user.id}")
                
                if not selected_address:
                    selected_address = addresses.filter(is_default=True).first()
                    if selected_address:
                        logger.info(f"Using default address {selected_address.id} for user {request.user.id}")
                
                if not addresses.exists():
                    logger.warning(f"No addresses found for user {request.user.id}")
                    messages.warning(request, 'Please add a delivery address before proceeding')
                    
            except Exception as e:
                logger.error(f"Error fetching addresses for user {request.user.id}: {str(e)}")
                messages.error(request, 'Error loading delivery addresses')
                return redirect('accounts:address-list')
            
            # Prepare context
            context = {
                'variant': variant,
                'quantity': quantity,
                'unit_price': unit_price,
                'subtotal': subtotal,
                'discount_amount': discount_amount,
                'shipping_cost': shipping_cost,
                'tax_amount': tax_amount,
                'total_amount': total_amount,
                'discount': discount,
                'addresses': addresses,
                'selected_address': selected_address,
                'coupon_code': coupon_code,
            }
            
            logger.info(f"Order review page rendered successfully for user {request.user.id}")
            return render(request, 'orders/order_review.html', context)
            
        except ValueError as e:
            logger.error(f"ValueError in order review GET: {str(e)} for user {request.user.id}")
            messages.error(request, 'Invalid order parameters provided')
            return redirect('products:product-list')
            
        except Exception as e:
            logger.error(f"Unexpected error in order review GET: {str(e)} for user {request.user.id}", exc_info=True)
            messages.error(request, 'An unexpected error occurred while loading order details')
            return redirect('products:product-list')
    
    elif request.method == 'POST':
        logger.info(f"Order creation POST request from user {request.user.id}")
        try:
            return create_order(request)
        except Exception as e:
            logger.error(f"Error in order creation: {str(e)} for user {request.user.id}", exc_info=True)
            messages.error(request, 'An error occurred while creating your order')
            return redirect('order-review')
    
    else:
        logger.warning(f"Invalid HTTP method {request.method} for order review by user {request.user.id}")
        messages.error(request, 'Invalid request method')
        return JsonResponse({'error:':'error'},status=400)


# PURCHASE THE ORDER=========================================================================================================
# Updated create_order function
@login_required
@require_POST
@csrf_exempt
@transaction.atomic
def create_order(request):
    """
    Create order from review page
    """
    try:
        # Get form data
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method')
        coupon_code = request.POST.get('coupon_code', '').strip()
        order_notes = request.POST.get('order_notes', '').strip()

        print("PAYMENT METHOD : ",payment_method)
        
        # Validate inputs
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        if quantity > variant.get_available_stock():
            messages.error(request, 'Insufficient stock available')
            return redirect('order-review')
        
        # Calculate pricing
        unit_price = variant.get_effective_price()
        subtotal = unit_price * quantity
        shipping_cost = Decimal('50.00') if subtotal < Decimal('500.00') else Decimal('0.00')
        discount_amount = Decimal('0.00')
        discount = None
        
        # Apply discount
        if coupon_code:
            try:
                discount = Discount.objects.get(code=coupon_code)
                if discount.is_valid(user=request.user, order_total=subtotal):
                    new_total, discount_amount = discount.apply_discount(subtotal, request.user)
                else:
                    messages.error(request, 'Invalid or expired coupon code')
                    return redirect('order-review')
            except Discount.DoesNotExist:
                messages.error(request, 'Coupon code not found')
                return redirect('order-review')
        
        # Calculate final amounts
        taxable_amount = subtotal - discount_amount + shipping_cost
        tax_amount = taxable_amount * Decimal('0.05')
        total_amount = subtotal - discount_amount + shipping_cost + tax_amount
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            status='pending',
            payment_status='pending',
            payment_method=payment_method,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            total_amount=total_amount,
            shipping_address=address,
            billing_address=address,
            order_notes=order_notes,
            coupon_code=coupon_code if discount else ''
        )
        
        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            product=variant.product,
            variant=variant,
            quantity=quantity,
            unit_price=unit_price
        )
        
        # Reserve stock
        variant.reserved_stock += quantity
        variant.save()
        
        # Record stock movement
        StockMovement.objects.create(
            variant=variant,
            movement_type='reserved',
            reason='reservation',
            quantity=-quantity,
            reference_id=order.order_id,
            notes=f'Stock reserved for order {order.order_id}',
            created_by=request.user
        )
        
        # Update discount usage if applied
        if discount:
            discount.used_count += 1
            discount.save()
        
        # Handle payment method
        if payment_method == 'cod':
            try:
                # 1. Update Order and Stock Atomically
                with transaction.atomic():
                    order.status = 'confirmed'
                    order.payment_status = 'pending' # COD is pending payment
                    order.save()
                    
                    # Convert reserved stock to sold (Same logic as Razorpay)
                    for item in order.items.all():
                        variant = item.variant
                        if variant:
                            variant.reserved_stock -= item.quantity
                            variant.stock -= item.quantity
                            variant.save()
                            
                            # Record stock movement
                            StockMovement.objects.create(
                                variant=variant,
                                movement_type='out',
                                reason='sale',
                                quantity=-item.quantity,
                                reference_id=order.order_id,
                                notes=f'Sold via order {order.order_id} (COD)',
                                created_by=request.user
                            )
                
                # 2. Create Zippypost Shipment (Outside atomic block)
                try:
                    from .zippypost_utils import process_zippypost_shipment
                    process_zippypost_shipment(order)
                except Exception as zip_error:
                    # Log error but don't fail the order
                    logger.error(f"COD Zippypost Error for {order.order_id}: {zip_error}")
                
                messages.success(request, f'Order {order.order_id} placed successfully!')
                return redirect('order_detail',order_id=order.order_id)
                
            except Exception as e:
                logger.error(f"Error validating COD order {order.order_id}: {str(e)}")
                messages.error(request, "Error placing order. Please try again.")
                return redirect('order-review')
        
        elif payment_method == 'razorpay':
            # Create Razorpay order
            razorpay_order = razorpay_client.order.create({
                'amount': int(total_amount * 100),  # Amount in paise
                'currency': 'INR',
                'receipt': order.order_id,
                'payment_capture': 1
            })
            
            order.payment_reference = razorpay_order['id']
            order.save()
            
            # Store payment data in session instead of rendering directly
            request.session['payment_data'] = {
                'order_id': order.order_id,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': int(total_amount * 100),
                'currency': 'INR',
                'user_name': request.user.get_full_name() or request.user.username,
                'user_email': request.user.email,
                'user_phone': address.phone_number
            }
            # construct redirect url
            redirect_url = reverse_lazy('complete_payment', kwargs={'order_id': order.order_id})
            return JsonResponse({'redirect_url': redirect_url})
            # Redirect to payment page instead of rendering
            # return redirect(reverse_lazy('complete_payment', kwargs={'order_id': order.order_id}))
        
        else:
            messages.error(request, 'Invalid payment method')
            return redirect('complete_payment',order_id=order.order_id)
            
    except Exception as e:
        messages.error(request, f'Error creating order: {str(e)}')
        return redirect('order-review')


# NEW: Add this payment page view
@login_required
def payment_page(request, order_id):
    """
    Dedicated payment page that loads via GET request
    """
    try:
        # Get order
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        
        # Check if payment data exists in session
        payment_data = request.session.get('payment_data')
        if not payment_data or payment_data.get('order_id') != order_id:
            messages.error(request, 'Payment session expired. Please try again.')
            return redirect('orders:order-detail', order_id=order_id)
        
        # Clear payment data from session after retrieving
        del request.session['payment_data']
        
        # Prepare context
        context = {
            'order': order,
            'razorpay_order_id': payment_data['razorpay_order_id'],
            'razorpay_key_id': payment_data['razorpay_key_id'],
            'amount': payment_data['amount'],
            'currency': payment_data['currency'],
            'user_name': payment_data['user_name'],
            'user_email': payment_data['user_email'],
            'user_phone': payment_data['user_phone']
        }
        
        return render(request, 'orders/payment.html', context)
        
    except Exception as e:
        logger.error(f"Error in payment page for order {order_id}: {str(e)}")
        messages.error(request, 'Error loading payment page')
        return redirect('orders:order-detail', order_id=order_id)



# VERIFY THE PAYMENT================================================================================================
@login_required
@require_POST
@csrf_exempt
def verify_payment(request):
    """
    Verify Razorpay payment and update order status
    """
    try:
        data = json.loads(request.body)
        
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        # Get order
        order = get_object_or_404(Order, payment_reference=razorpay_order_id, user=request.user)
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Payment successful
            with transaction.atomic():
                order.payment_status = 'paid'
                order.status = 'confirmed'
                order.payment_method='upi'
                order.save()
                
                # Convert reserved stock to sold
                for item in order.items.all():
                    variant = item.variant
                    variant.reserved_stock -= item.quantity
                    variant.stock -= item.quantity
                    variant.save()
                    
                    # Record stock movement
                    StockMovement.objects.create(
                        variant=variant,
                        movement_type='out',
                        reason='sale',
                        quantity=-item.quantity,
                        reference_id=order.order_id,
                        notes=f'Sold via order {order.order_id}',
                        created_by=request.user
                    )
            
            # ========== ZIPPYPOST INTEGRATION ==========
            # Create shipment on Zippypost after successful payment
            try:
                from .zippypost_utils import process_zippypost_shipment
                
                # Process shipment in background (or inline for now)
                process_zippypost_shipment(order)
                
            except Exception as zippypost_error:
                # Log error but don't fail the order - manual processing can be done later
                logger.exception(f"Zippypost integration error for order {order.order_id}: {str(zippypost_error)}")
                logger.error("Order payment successful but shipment creation failed - needs manual processing")
            # ========== END ZIPPYPOST INTEGRATION ==========
            
            return JsonResponse({
                'success': True,
                'message': 'Payment successful',
                'order_id': order.order_id,
                'redirect_url': f'/user_orders/{order.order_id}/'
            })
            
        except razorpay.errors.SignatureVerificationError:
            order.payment_status = 'failed'
            order.save()
            
            return JsonResponse({
                'success': False,
                'error': 'Payment verification failed'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ==================================================================================================================================================================
# APPLY COUPON
@login_required
@require_POST
@csrf_exempt
def apply_coupon(request):
    """
    AJAX endpoint to validate and apply coupon codes
    """
    try:
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').strip().upper()
        order_total = Decimal(data.get('order_total', '0'))
        
        if not coupon_code:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a coupon code'
            }, status=400)
        
        try:
            discount = Discount.objects.get(code=coupon_code)
            
            if discount.is_valid(user=request.user, order_total=order_total):
                new_total, discount_amount = discount.apply_discount(order_total, request.user)
                
                return JsonResponse({
                    'success': True,
                    'discount': {
                        'code': discount.code,
                        'type': discount.discount_type,
                        'value': str(discount.value),
                        'discount_amount': str(discount_amount),
                        'description': f"₹{discount_amount} off" if discount.discount_type == 'fixed' 
                                     else f"{discount.value}% off"
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Coupon is not valid for this order'
                }, status=400)
                
        except Discount.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid coupon code'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# SELECT / MANAGE ADDRESS
@login_required
@require_http_methods(["GET", "POST"])
def manage_address(request):
    """
    AJAX endpoint to get addresses or create new address
    """
    if request.method == 'GET':
        addresses = Address.objects.filter(user=request.user, is_active=True)
        
        address_list = []
        for addr in addresses:
            address_list.append({
                'id': str(addr.id),
                'label': addr.label,
                'full_name': addr.full_name,
                'phone_number': addr.phone_number,
                'full_address': addr.get_full_address(),
                'short_address': addr.get_short_address(),
                'is_default': addr.is_default
            })
        
        return JsonResponse({
            'success': True,
            'addresses': address_list
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['full_name', 'phone_number', 'address_line_1', 'city', 'state', 'pincode']
            for field in required_fields:
                if not data.get(field, '').strip():
                    return JsonResponse({
                        'success': False,
                        'error': f'{field.replace("_", " ").title()} is required'
                    }, status=400)
            
            # Create new address
            address = Address.objects.create(
                user=request.user,
                label=data.get('label', 'Home'),
                address_type=data.get('address_type', 'home'),
                full_name=data.get('full_name').strip(),
                phone_number=data.get('phone_number').strip(),
                alternate_phone=data.get('alternate_phone', '').strip() or None,
                address_line_1=data.get('address_line_1').strip(),
                address_line_2=data.get('address_line_2', '').strip() or None,
                landmark=data.get('landmark', '').strip() or None,
                pincode=data.get('pincode').strip(),
                city=data.get('city').strip(),
                state=data.get('state').strip(),
                country=data.get('country', 'India').strip(),
                delivery_instructions=data.get('delivery_instructions', '').strip() or None,
                is_apartment=data.get('is_apartment', False),
                floor_number=data.get('floor_number', '').strip() or None
            )
            
            return JsonResponse({
                'success': True,
                'address': {
                    'id': str(address.id),
                    'label': address.label,
                    'full_name': address.full_name,
                    'phone_number': address.phone_number,
                    'full_address': address.get_full_address(),
                    'short_address': address.get_short_address(),
                    'is_default': address.is_default
                },
                'message': 'Address added successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


# CHECK STOCK AVAILABILITY 

@login_required
@require_POST
@csrf_exempt
def check_stock_availability(request):
    """
    AJAX endpoint to check real-time stock availability
    """
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        quantity = int(data.get('quantity', 1))
        
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        available_stock = variant.get_available_stock()
        
        return JsonResponse({
            'success': True,
            'available_stock': available_stock,
            'is_available': quantity <= available_stock,
            'is_low_stock': variant.is_low_stock(),
            'max_quantity': available_stock
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)




# =================================================================================================================================================================



@login_required
def order_detail(request, order_id):
    """
    Order detail page
    """
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Tracking Data
    timeline = []
    tracking_data = None
    
    print(f"DEBUG: Order {order.order_id} - Checking Zippypost")
    
    # 1. Try to get Zippypost Tracking
    if hasattr(order, 'zippypost') and order.zippypost.tracking_number:
        tracking_no = order.zippypost.tracking_number
        print(f"DEBUG: Found valid tracking number: {tracking_no}")
        try:
            from .zippypost_utils import track_shipment
            print(f"DEBUG: Calling track_shipment for {tracking_no}")
            
            success, api_data, error = track_shipment(tracking_no)
            print(f"DEBUG: API Response Success: {success}")
            print(f"DEBUG: API Data: {api_data}")
            
            if success and api_data:
                # Extract events from Zippypost response
                # Response format: {'success': True, 'result': {'events': [...], 'courier': '...', ...}}
                result = api_data.get('result') or api_data.get('RESULT') or {}
                
                # Extract extra tracking details
                tracking_data = {
                    'courier': result.get('courier'),
                    'status': result.get('status'),
                    'mode': result.get('mode'),
                    'zone': result.get('zone'),
                    'order_number': result.get('order_number')
                }
                
                events = result.get('events', [])
                
                for event in events:
                    # Parse timestamp
                    scan_time = event.get('scan_time')
                    timestamp = None
                    if scan_time:
                        try:
                            timestamp = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    # Map scan codes to icons
                    scan_code = event.get('scan_code')
                    icon = 'check-circle'
                    if scan_code == 3: # In-transit
                        icon = 'truck'
                    elif scan_code == 4: # Out for delivery
                        icon = 'truck'
                    elif scan_code == 5: # Delivered
                         icon = 'check-circle'
                    elif scan_code == 6: # Cancelled
                        icon = 'x-circle'
                    elif scan_code in [7, 10, 11, 18]: # Lost/Damaged/Exception
                        icon = 'alert-circle'
                            
                    timeline.append({
                        'title': event.get('scan', 'Update'),
                        'description': event.get('remark', ''),
                        'location': event.get('location', ''),
                        'date': timestamp,
                        'completed': True,
                        'icon': icon,
                        'is_cancelled': scan_code == 6
                    })
                
                # Sort by date descending (latest first)
                timeline.sort(key=lambda x: x['date'] or datetime.min, reverse=True)
                
        except Exception as e:
            logger.error(f"Error fetching tracking for {order.order_id}: {e}")
            print(f"DEBUG: Exception: {e}")
            
    # 2. If no Zippypost data (or failure), fallback to local status
    if not timeline:
        # Simple local status timeline
        timeline = [{
            'title': 'Order Placed',
            'description': 'Order has been placed successfully',
            'date': order.created_at,
            'completed': True,
            'icon': 'check-circle'
        }]
        if order.status == 'confirmed':
             timeline.insert(0, {
                'title': 'Confirmed',
                'description': 'Order confirmed, preparing for shipment',
                'date': order.updated_at,
                'completed': True,
                'icon': 'check-circle'
            })
        elif order.status == 'shipped':
            timeline.insert(0, {
                'title': 'Shipped',
                'description': f"Shipped with {order.courier_partner or 'courier'}",
                'date': order.updated_at,
                'completed': True,
                'icon': 'truck'
            })
        elif order.status == 'delivered':
            timeline.insert(0, {
                'title': 'Delivered',
                'description': 'Package delivered to you',
                'date': order.delivered_at,
                'completed': True,
                'icon': 'check-circle'
            })

    # Calculate Order Summary
    items = order.items.all()
    subtotal = sum(item.total_price for item in items)
    total_quantity = sum(item.quantity for item in items)
    
    # Try to get shipping from order if available (assuming added in prev steps or existing)
    # Default to 0 if not found for robust display
    shipping_fee = getattr(order, 'shipping_fee', Decimal('0.00')) 
    
    order_summary = {
        'subtotal': subtotal,
        'shipping': shipping_fee,
        'discount': Decimal('0.00'),
        'tax': Decimal('0.00'),
        'total': order.total_amount,
        'total_quantity': total_quantity,
        'item_count': items.count()
    }

    context = {
        'order': order,
        'order_items': items,
        'can_cancel': order.can_be_cancelled(),
        'timeline': timeline,
        'tracking_data': tracking_data,
        'order_summary': order_summary,
        'delivery_info': {
             'estimated_delivery': getattr(order, 'estimated_delivery', None),
             'delivery_date': order.delivered_at if order.status == 'delivered' else None,
             'tracking_available': bool(timeline)
        },
        'status_updates': [] 
    }
    
    return render(request, 'user_orders/order_detail.html', context)


@require_POST
def cancel_order(request, order_id):
    """
    Cancel order and release reserved stock
    """
    import sys
    print(f"\n{'='*50}", flush=True)
    print(f"🔔 DEBUG: cancel_order VIEW HIT", flush=True)
    print(f"📦 DEBUG: Order ID: {order_id}", flush=True)
    print(f"👤 DEBUG: User: {request.user}", flush=True)
    print(f"🔧 DEBUG: Method: {request.method}", flush=True)
    print(f"{'='*50}\n", flush=True)
    sys.stdout.flush()
    
    try:
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        print(f"✅ DEBUG: Order found: {order.order_id}, Status: {order.status}", flush=True)
        
        if not order.can_be_cancelled():
            print("❌ DEBUG: Order cannot be cancelled", flush=True)
            messages.error(request, 'Order cannot be cancelled at this stage')
            return redirect('user-orders')
        # 1. ALWAYS try to cancel Zippypost shipment if it exists
        print(f"🔍 DEBUG: Checking for Zippypost shipment...", flush=True)
        if hasattr(order, 'zippypost') and order.zippypost.tracking_number:
            print(f"📮 DEBUG: Found Zippypost shipment: {order.zippypost.tracking_number}", flush=True)
            print(f"📊 DEBUG: Current shipping status: {order.zippypost.shipping_status}", flush=True)
            
            try:
                from .zippypost_utils import cancel_shipment
                print(f"🚀 DEBUG: Calling Zippypost cancel API...", flush=True)
                zip_success, zip_resp, zip_error = cancel_shipment(order.zippypost.tracking_number)
                print(f"📥 DEBUG: Zippypost API response - Success: {zip_success}", flush=True)
                print(f"📝 DEBUG: Error (if any): {zip_error}", flush=True)
                
                if zip_success:
                    order.zippypost.shipping_status = 'CANCELLED'
                    order.zippypost.save()
                    print(f"✅ DEBUG: Zippypost status updated to CANCELLED", flush=True)
                    messages.success(request, 'Shipment cancellation request sent to courier partner.')
                else:
                    print(f"⚠️ DEBUG: Zippypost cancellation failed: {zip_error}", flush=True)
                    logger.error(f"Failed to cancel Zippypost shipment: {zip_error}")
                    messages.warning(request, f"Could not cancel courier shipment automatically: {zip_error}. Please contact support.")
            except Exception as e:
                print(f"💥 DEBUG: Exception in Zippypost cancel: {str(e)}", flush=True)
                logger.exception(f"Error in Zippypost cancel flow: {e}")
                messages.warning(request, f"Could not cancel courier shipment: {str(e)}")
        else:
            print(f"ℹ️ DEBUG: No Zippypost shipment found for this order", flush=True)
        
        # 2. ALWAYS cancel local order
        print(f"🔄 DEBUG: Starting local order cancellation...", flush=True)
        with transaction.atomic():
            # Release reserved stock
            print(f"📦 DEBUG: Releasing stock for {order.items.count()} items...", flush=True)
            for item in order.items.all():
                variant = item.variant
                variant.reserved_stock -= item.quantity
                variant.save()
                print(f" ✅ Released {item.quantity} units of {variant}", flush=True)
                
                # Record stock movement
                StockMovement.objects.create(
                    variant=variant,
                    movement_type='released',
                    reason='cancellation',
                    quantity=item.quantity,
                    reference_id=order.order_id,
                    notes=f'Stock released due to order cancellation',
                    created_by=request.user
                )
            
            # Update order status
            print(f"📝 DEBUG: Updating order status to 'cancelled'...", flush=True)
            order.status = 'cancelled'
            order.save()
            
            # Reverse discount usage if applied
            if order.coupon_code:
                try:
                    discount = Discount.objects.get(code=order.coupon_code)
                    discount.used_count = max(0, discount.used_count - 1)
                    discount.save()
                    print(f"🎟️ DEBUG: Reversed discount usage for code: {order.coupon_code}", flush=True)
                except Discount.DoesNotExist:
                    print(f"⚠️ DEBUG: Discount code not found: {order.coupon_code}", flush=True)
                    pass
        
        print(f"✅ DEBUG: Order cancellation completed successfully!", flush=True)
        messages.success(request, f'Order {order.order_id} cancelled successfully')
        return redirect('user-orders')
        
    except Exception as e:
        print(f"💥 DEBUG: Exception occurred: {str(e)}", flush=True)
        logger.exception(f"Error cancelling order {order_id}: {str(e)}")
        messages.error(request, f'Error cancelling order: {str(e)}')
        return redirect('user-orders')
# =============================================================================================================
@login_required
def user_orders(request):
    """
    List user's orders
    """
    orders = Order.objects.filter(user=request.user).prefetch_related('items__variant__product')
    
    context = {
        'orders': orders
    }
    
    return render(request, 'orders/user_orders.html', context)

