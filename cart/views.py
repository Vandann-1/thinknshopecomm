from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db import transaction
import json
from .models import (Cart,CartItem)
from .utils import (get_or_create_cart,merge_guest_cart_with_user_cart)
from product.models import * 
import logging
# Create your views here.

# Add Product To Cart 
# Set up logger
logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def fill_product_into_cart(request, product_id):
    """
    Add product to cart with variant selection via AJAX
    """
    logger.info(f"=== FILL PRODUCT INTO CART START ===")
    logger.info(f"Product ID: {product_id}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request body: {request.body}")
    
    try:
        # Check if product exists
        logger.info(f"Searching for product with ID: {product_id}")
        product = get_object_or_404(Product, id=product_id, status='active')
        logger.info(f"Product found: {product.name}")
        
        # Get product variants for modal
        variants = product.variants.filter(is_active=True).select_related('color', 'size')
        colors = product.get_available_colors()
        sizes = product.get_available_sizes()
        
        logger.info(f"Variants count: {variants.count()}")
        logger.info(f"Colors count: {colors.count()}")
        logger.info(f"Sizes count: {sizes.count()}")
        
        # Check if product has variants
        if variants.exists():
            logger.info("Product has variants - preparing variant selection data")
            
            # Return variant data for modal selection
            variant_data = []
            for variant in variants:
                logger.info(f"Processing variant: {variant.id} - Color: {variant.color.name if variant.color else 'None'} - Size: {variant.size.name if variant.size else 'None'} - Stock: {variant.get_available_stock()}")
                
                if variant.is_in_stock():
                    variant_info = {
                        'id': variant.id,
                        'color_id': variant.color.id if variant.color else None,
                        'color_name': variant.color.name if variant.color else None,
                        'color_hex': variant.color.hex_code if variant.color else None,
                        'size_id': variant.size.id if variant.size else None,
                        'size_name': variant.size.name if variant.size else None,
                        'price': float(variant.get_effective_price()),
                        'stock': variant.get_available_stock(),
                        'sku': variant.sku,
                        'image': variant.image.url if variant.image else None,
                    }
                    variant_data.append(variant_info)
                    logger.info(f"Added variant to data: {variant_info}")
                else:
                    logger.info(f"Variant {variant.id} is out of stock - skipping")
            
            color_data = []
            for c in colors:
                color_info = {'id': c.id, 'name': c.name, 'hex_code': c.hex_code}
                color_data.append(color_info)
                logger.info(f"Added color: {color_info}")
            
            size_data = []
            for s in sizes:
                size_info = {'id': s.id, 'name': s.name, 'category': getattr(s, 'category', 'default')}
                size_data.append(size_info)
                logger.info(f"Added size: {size_info}")
            
            # IMPROVED: Get product image with proper fallback strategy
            primary_image = get_product_primary_image(product)
            logger.info(f"Primary image resolved: {primary_image}")
            
            response_data = {
                'success': True,
                'requires_variant_selection': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'base_price': float(product.get_effective_price()),
                    'image': primary_image,
                },
                'variants': variant_data,
                'colors': color_data,
                'sizes': size_data,
            }
            
            logger.info(f"Returning variant selection response: {response_data}")
            return JsonResponse(response_data)
        else:
            logger.info("Product has no variants - adding directly to cart")
            # Product without variants - add directly
            return add_to_cart_direct(request, product)
            
    except Product.DoesNotExist:
        logger.error(f"Product with ID {product_id} not found")
        return JsonResponse({
            'success': False,
            'message': 'Product not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in fill_product_into_cart: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

# Get Product Gallery Image 
def get_product_primary_image(product):
    """
    Get the primary image for a product with proper fallback strategy
    """
    try:
        # Strategy 1: Look for primary image in gallery
        primary_gallery = product.gallery.filter(is_primary=True).first()
        if primary_gallery and primary_gallery.image:
            return primary_gallery.image.url
        
        # Strategy 2: Get first available gallery image
        first_gallery = product.gallery.filter(image__isnull=False).first()
        if first_gallery and first_gallery.image:
            return first_gallery.image.url
        
        # Strategy 3: Get image from first available variant
        first_variant = product.variants.filter(
            is_active=True, 
            image__isnull=False
        ).first()
        if first_variant and first_variant.image:
            return first_variant.image.url
        
        # Strategy 4: Return None if no image found
        return None
        
    except Exception as e:
        logger.error(f"Error getting primary image for product {product.id}: {str(e)}")
        return None

# Add To Cart Direct with Enhanced Logging
@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart_direct(request, product, variant_id=None, quantity=1):
    """
    Add product directly to cart (internal function)
    """
    logger.info(f"=== ADD TO CART DIRECT START ===")
    logger.info(f"Product: {product.name} (ID: {product.id})")
    logger.info(f"Variant ID: {variant_id}")
    logger.info(f"Quantity: {quantity}")
    logger.info(f"Request user: {request.user}")
    logger.info(f"Request session key: {request.session.session_key}")
    
    try:
        with transaction.atomic():
            # Get or create cart
            logger.info("Getting or creating cart...")
            cart = get_or_create_cart(request)
            logger.info(f"Cart obtained: {cart}")
            
            variant = None
            if variant_id:
                logger.info(f"Looking for variant with ID: {variant_id}")
                try:
                    variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
                    logger.info(f"Variant found: {variant} - Stock: {variant.get_available_stock()}")
                    
                    # Check stock
                    if not variant.is_in_stock():
                        logger.warning(f"Variant {variant_id} is out of stock")
                        return JsonResponse({
                            'success': False,
                            'message': 'This variant is out of stock'
                        })
                    
                    if variant.get_available_stock() < quantity:
                        logger.warning(f"Insufficient stock for variant {variant_id}. Available: {variant.get_available_stock()}, Requested: {quantity}")
                        return JsonResponse({
                            'success': False,
                            'message': f'Only {variant.get_available_stock()} items available'
                        })
                except Exception as e:
                    logger.error(f"Error finding variant {variant_id}: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'message': f'Variant not found: {str(e)}'
                    })
            
            # Check if item already exists in cart
            logger.info("Checking for existing cart item...")
            try:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    defaults={
                        'quantity': quantity,
                        'unit_price': variant.get_effective_price() if variant else product.get_effective_price()
                    }
                )
                logger.info(f"CartItem created: {created}, Item: {cart_item}")
            except Exception as e:
                logger.error(f"Error creating/getting cart item: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'message': f'Failed to create cart item: {str(e)}'
                })
            
            if not created:
                logger.info("Updating existing cart item...")
                # Update existing item
                new_quantity = cart_item.quantity + quantity
                max_stock = variant.get_available_stock() if variant else product.get_total_stock()
                
                logger.info(f"New quantity: {new_quantity}, Max stock: {max_stock}")
                
                if new_quantity > max_stock:
                    logger.warning(f"Cannot add more items. Max: {max_stock}, Requested total: {new_quantity}")
                    return JsonResponse({
                        'success': False,
                        'message': f'Cannot add more items. Maximum available: {max_stock}'
                    })
                
                cart_item.quantity = new_quantity
                cart_item.unit_price = variant.get_effective_price() if variant else product.get_effective_price()
                cart_item.save()
                logger.info(f"Cart item updated successfully. New quantity: {cart_item.quantity}")
                action = 'updated'
            else:
                logger.info("New cart item created successfully")
                action = 'added'
            
            # Get updated cart info
            logger.info("Getting updated cart information...")
            try:
                cart_info = {
                    'total_items': cart.get_total_items(),
                    'total_amount': cart.get_total_amount(),
                    'items_count': cart.get_items_count(),
                }
                logger.info(f"Cart info: {cart_info}")
            except Exception as e:
                logger.error(f"Error getting cart info: {str(e)}")
                cart_info = {'total_items': 0, 'total_amount': 0.0, 'items_count': 0}
            
            response_data = {
                'success': True,
                'action': action,
                'message': f'Product {action} to cart successfully!',
                'cart': cart_info,
                'item': {
                    'id': cart_item.id,
                    'product_name': product.name,
                    'variant_info': f"{variant.color.name} - {variant.size.name}" if variant else None,
                    'quantity': cart_item.quantity,
                    'unit_price': float(cart_item.unit_price),
                    'total_price': float(cart_item.get_total_price()),
                }
            }
            
            logger.info(f"SUCCESS: Returning response: {response_data}")
            return JsonResponse(response_data)
            
    except Exception as e:
        logger.error(f"Unexpected error in add_to_cart_direct: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Failed to add to cart: {str(e)}'
        }, status=500)

# Add Variant To Cart with Enhanced Logging
@csrf_exempt
@require_http_methods(["POST"])
def add_variant_to_cart(request):
    """
    Add specific variant to cart via AJAX
    """
    logger.info(f"=== ADD VARIANT TO CART START ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request content type: {request.content_type}")
    logger.info(f"Request body: {request.body}")
    
    try:
        # Parse JSON data
        try:
            data = json.loads(request.body)
            logger.info(f"Parsed JSON data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Invalid JSON data: {str(e)}'
            }, status=400)
        
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        quantity = data.get('quantity', 1)
        
        logger.info(f"Extracted data - Product ID: {product_id}, Variant ID: {variant_id}, Quantity: {quantity}")
        
        # Validate required fields
        if not all([product_id, variant_id]):
            logger.error("Missing required fields")
            return JsonResponse({
                'success': False,
                'message': 'Product ID and Variant ID are required'
            }, status=400)
        
        # Validate and convert quantity
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            logger.info(f"Validated quantity: {quantity}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid quantity: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Invalid quantity: {str(e)}'
            }, status=400)
        
        # Get product
        try:
            product = get_object_or_404(Product, id=product_id, status='active')
            logger.info(f"Product found: {product.name}")
        except Exception as e:
            logger.error(f"Product not found: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Product not found: {str(e)}'
            }, status=404)
        
        # Call add_to_cart_direct
        logger.info("Calling add_to_cart_direct...")
        return add_to_cart_direct(request, product, variant_id, quantity)
        
    except Exception as e:
        logger.error(f"Unexpected error in add_variant_to_cart: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

# Helper function to get or create cart (you'll need to implement this)
def get_or_create_cart(request):
    """
    Get or create a cart for the current user/session
    """
    logger.info("Getting or creating cart...")
    
    if request.user.is_authenticated:
        logger.info(f"User is authenticated: {request.user}")
        # For authenticated users, get cart by user
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'session_key': request.session.session_key}
        )
    else:
        logger.info("User is anonymous, using session")
        # For anonymous users, get cart by session
        if not request.session.session_key:
            request.session.create()
            logger.info(f"Created new session: {request.session.session_key}")
        
        cart, created = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            user=None,
            defaults={}
        )
    
    logger.info(f"Cart {'created' if created else 'found'}: {cart}")
    return cart


# Get Cart Summary--------=========================================================================================================================================================
@require_http_methods(["GET"])
def get_cart_summary(request):
    """
    Get cart summary for displaying in header/sidebar
    """
    try:
        cart = get_or_create_cart(request)
        
        items = []
        for item in cart.items.select_related('product', 'variant__color', 'variant__size')[:5]:  # Limit to 5 recent items
            item_data = {
                'id': item.id,
                'product_name': item.product.name,
                'product_slug': item.product.slug,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.get_total_price()),
                'image': None,
            }
            
            if item.variant:
                item_data.update({
                    'variant_info': f"{item.variant.color.name} - {item.variant.size.name}",
                    'color': item.variant.color.name,
                    'size': item.variant.size.name,
                })
                if item.variant.image:
                    item_data['image'] = item.variant.image.url
            
            # Fallback to product primary image
            if not item_data['image']:
                primary_image = item.product.gallery.filter(is_primary=True).first()
                if primary_image:
                    item_data['image'] = primary_image.image.url
            
            items.append(item_data)
        
        return JsonResponse({
            'success': True,
            'cart': {
                'total_items': cart.get_total_items(),
                'total_amount': cart.get_total_amount(),
                'items_count': cart.get_items_count(),
                'items': items,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get cart summary: {str(e)}'
        }, status=500)


# Remove From Cart
@csrf_exempt
@require_http_methods(["POST"])
def remove_from_cart(request, item_id):
    """
    Remove item from cart
    """
    try:
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        product_name = cart_item.product.name
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{product_name} removed from cart',
            'cart': {
                'total_items': cart.get_total_items(),
                'total_amount': cart.get_total_amount(),
                'items_count': cart.get_items_count(),
            }
        })
        
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Item not found in cart'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to remove item: {str(e)}'
        }, status=500)


# Update Crt Quantity
@csrf_exempt
@require_http_methods(["POST"])
def update_cart_quantity(request, item_id):
    """
    Update cart item quantity
    """
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            return JsonResponse({
                'success': False,
                'message': 'Quantity must be at least 1'
            }, status=400)
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        # Validate stock
        max_stock = cart_item.variant.get_available_stock() if cart_item.variant else cart_item.product.get_total_stock()
        
        if quantity > max_stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {max_stock} items available'
            })
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Quantity updated successfully',
            'item': {
                'quantity': cart_item.quantity,
                'total_price': float(cart_item.get_total_price()),
            },
            'cart': {
                'total_items': cart.get_total_items(),
                'total_amount': cart.get_total_amount(),
                'items_count': cart.get_items_count(),
            }
        })
        
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid quantity'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to update quantity: {str(e)}'
        }, status=500)
