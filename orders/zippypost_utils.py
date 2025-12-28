"""
Zippypost Courier API Integration Utilities

This module provides helper functions to interact with Zippypost's courier API
for automated shipment creation, tracking, and label generation.

Based on official Zippypost API documentation.

Author: ThinkNShop Team
"""

import requests
import json
import logging
import hmac
import hashlib
import time
from typing import Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from django.utils import timezone

# Import Zippypost credentials
from .constants import (
    ZIPPYPOST_PUBLIC_KEY,
    ZIPPYPOST_PRIVATE_KEY,
    ZIPPYPOST_SELLER_ID,
    ZIPPYPOST_URL,
    ZIPPYPOST_SHIPMENT_URL,
    ZIPPYPOST_LABEL_URL,
    ZIPPYPOST_TRACKING_URL,
    ZIPPYPOST_WAREHOUSE_ID,
    ZIPPYPOST_COURIER_ID,
    ZIPPYPOST_MODE_ID
)

# Set up logger
logger = logging.getLogger(__name__)


def generate_auth_token(public_key: str, private_key: str, seller_id: str, timestamp: int) -> str:
    """
    Generate authentication token for Zippypost API using HMAC-SHA256.
    
    Args:
        public_key: Zippypost public key
        private_key: Zippypost private key
        seller_id: Seller ID
        timestamp: Unix timestamp
        
    Returns:
        str: HMAC-SHA256 authentication token
    """
    # Concatenate in the required query string format
    data_to_hash = f'public_key={public_key}&private_key={private_key}&seller_id={seller_id}&time_stamp={timestamp}'
    
    # Generate HMAC-SHA256 hash using private_key as the secret
    hash_obj = hmac.new(private_key.encode(), data_to_hash.encode(), hashlib.sha256)
    
    return hash_obj.hexdigest()


def get_auth_headers() -> Dict[str, str]:
    """
    Generate authentication headers for Zippypost API requests.
    
    Returns:
        dict: Headers with authentication credentials
    """
    timestamp = int(time.time())
    auth_token = generate_auth_token(
        ZIPPYPOST_PUBLIC_KEY,
        ZIPPYPOST_PRIVATE_KEY,
        ZIPPYPOST_SELLER_ID,
        timestamp
    )
    
    return {
        'Content-Type': 'application/json',
        'authorization': auth_token,
        'timestamp': str(timestamp),
        'sellerid': ZIPPYPOST_SELLER_ID
    }


def create_shipment(order) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Create a shipment on Zippypost for the given order.
    
    Args:
        order: Order instance with shipping details
        
    Returns:
        tuple: (success: bool, response_data: dict|None, error_message: str|None)
    """
    try:
        # Validate order has required information
        if not order.shipping_address:
            return False, None, "Order missing shipping address"
        
        if not order.items.exists():
            return False, None, "Order has no items"
        
        # Get shipping and billing addresses
        shipping_addr = order.shipping_address
        billing_addr = order.billing_address or shipping_addr
        
        # Prepare items array
        items = []
        total_weight = 0.0
        
        for item in order.items.all():
            product = item.product
            quantity = item.quantity
            
            # Convert weight to kg (assuming product weight is in grams)
            item_weight_g = float(product.weight) if product.weight else 500.0
            item_weight_kg = item_weight_g / 1000.0
            total_weight += item_weight_kg * quantity
            
            # Prepare SKU (must be at least 3 chars for Zippypost)
            raw_sku = product.sku or f"SKU-{product.id}"
            sku = str(raw_sku)
            if len(sku) < 3:
                sku = f"SKU-{sku}"
            
            items.append({
                "sku": sku,
                "item_name": product.name,
                "quantity": quantity,
                "item_weight": item_weight_kg,
                "item_price": float(item.unit_price)
            })
        
        # Ensure minimum weight
        if total_weight < 0.1:
            total_weight = 0.5
        
        # Determine payment type: 1 = prepaid, 2 = COD
        payment_type = 2 if order.payment_method == 'cod' else 1
        
        # Calculate COD amount
        collectable_cod = float(order.total_amount) if order.payment_method == 'cod' else 0.0
        
        # Prepare shipment payload according to Zippypost documentation
        payload = {
            "order_number": order.order_id,
            "purchase_amount": float(order.total_amount),
            "purchase_date": order.created_at.strftime('%Y-%m-%d'),
            "billing_details_same_as_shipping": shipping_addr.id == billing_addr.id,
            
            # Shipping details (customer delivery address)
            "shipping_details": {
                "full_name": shipping_addr.full_name,
                "contact_number": shipping_addr.phone_number,
                "customer_email": order.user.email if order.user else "",
                "address_line_one": shipping_addr.address_line_1,
                "address_line_two": shipping_addr.address_line_2 or "",
                "landmark": shipping_addr.landmark or "",
                "pincode": shipping_addr.pincode,
                "city": shipping_addr.city
            },
            
            # Billing details
            "billing_details": {
                "full_name": billing_addr.full_name,
                "contact_number": billing_addr.phone_number,
                "gstin": "",  # Add GSTIN if you have it
                "address_line_one": billing_addr.address_line_1,
                "address_line_two": billing_addr.address_line_2 or "",
                "company_name": "",  # Add company name if applicable
                "pincode": billing_addr.pincode,
                "city": billing_addr.city
            },
            
            # Items array
            "items": items,
            
            # Package dimensions (in cm)
            "package_length": 20.0,
            "package_width": 15.0,
            "package_height": 10.0,
            "package_weight": total_weight,
            
            # Charges and amounts
            "shipping_charge": float(order.shipping_cost) if order.shipping_cost else 0.0,
            "cod_charge": 50.0 if order.payment_method == 'cod' else 0.0,
            "purchase_tax": float(order.tax_amount) if order.tax_amount else 0.0,
            "purchase_discount": float(order.discount_amount) if order.discount_amount else 0.0,
            "collectable_cod": collectable_cod,
            
            # Required IDs
            "warehouse_id": ZIPPYPOST_WAREHOUSE_ID,
            "payment_type": payment_type,
            "courier_id": ZIPPYPOST_COURIER_ID,
            "mode_id": ZIPPYPOST_MODE_ID
        }
        
        # Log the request with full details
        logger.info(f"=" * 80)
        logger.info(f"Creating Zippypost shipment for order {order.order_id}")
        logger.info(f"=" * 80)
        
        # Log authentication details (without exposing full keys)
        headers = get_auth_headers()
        logger.debug(f"Headers: {json.dumps({k: v[:10]+'...' if k == 'authorization' else v for k, v in headers.items()}, indent=2)}")
        
        # Log full payload
        logger.debug(f"Full Payload:")
        logger.debug(json.dumps(payload, indent=2))
        
        # Make API request
        try:
            response = requests.post(
                ZIPPYPOST_SHIPMENT_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Log full response details
            logger.info(f"API Response Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.debug(f"Full Response Body:")
            logger.debug(response.text)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise
        
        # Parse response
        if response.status_code in [200, 201]:  # Success (200 OK or 201 Created)
            response_data = response.json()
            
            # Check if shipment was created successfully
            if response_data.get('success') is True or response_data.get('status') == 'success':
                logger.info(f"✅ Shipment created successfully for order {order.order_id}")
                return True, response_data, None
            else:
                error_msg = response_data.get('message', 'Unknown error')
                logger.error(f"❌ Shipment creation failed: {error_msg}")
                return False, response_data, error_msg
                
        elif response.status_code == 400:  # Bad Request
            response_data = response.json()
            errors = response_data.get('errors', {}) or response_data.get('error', {})
            error_msg = f"Validation failed: {json.dumps(errors)}"
            logger.error(f"❌ Zippypost validation error: {error_msg}")
            return False, response_data, error_msg
            
        elif response.status_code == 401:  # Unauthorized
            error_msg = "Authentication failed - Invalid API key or token"
            logger.error(f"❌ {error_msg}")
            return False, None, error_msg
            
        else:
            error_msg = f"API returned status {response.status_code}: {response.text}"
            logger.error(f"❌ Zippypost API error: {error_msg}")
            return False, None, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Zippypost API request timeout"
        logger.error(error_msg)
        return False, None, error_msg
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)}"
        logger.error(f"Zippypost API request failed: {error_msg}")
        return False, None, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Error creating Zippypost shipment: {error_msg}")
        return False, None, error_msg


def get_shipping_label(tracking_number: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Retrieve shipping label PDF URL from Zippypost.
    
    Args:
        tracking_number: Shipment AWB / Tracking number
        
    Returns:
        tuple: (success: bool, label_url: str|None, error_message: str|None)
    """
    try:
        # URL format: https://api.zipypost.com/label/:AWB
        url = f"{ZIPPYPOST_LABEL_URL}/{tracking_number}"
        
        response = requests.get(
            url,
            headers=get_auth_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            # Documentation says field is 'path', but checking fallbacks just in case
            label_url = response_data.get('path') or response_data.get('label_url') or response_data.get('url')
            
            if label_url:
                logger.info(f"Retrieved label URL for AWB {tracking_number}")
                return True, label_url, None
            else:
                error_msg = "Label path/url not found in response"
                logger.error(error_msg)
                return False, None, error_msg
        else:
            error_msg = f"API returned status {response.status_code}"
            logger.error(f"Failed to get label: {error_msg}")
            return False, None, error_msg
            
    except Exception as e:
        error_msg = f"Error retrieving label: {str(e)}"
        logger.exception(error_msg)
        return False, None, error_msg


def track_shipment(tracking_number: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Get tracking information for a shipment from Zippypost.
    
    Args:
        tracking_number: Shipment tracking number
        
    Returns:
        tuple: (success: bool, tracking_data: dict|None, error_message: str|None)
    """
    try:
        url = f"{ZIPPYPOST_TRACKING_URL}/{tracking_number}"
        
        response = requests.get(
            url,
            headers=get_auth_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            tracking_data = response.json()
            logger.info(f"Retrieved tracking info for {tracking_number}")
            return True, tracking_data, None
        else:
            error_msg = f"API returned status {response.status_code}"
            logger.error(f"Tracking failed: {error_msg}")
            return False, None, error_msg
            
    except Exception as e:
        error_msg = f"Error tracking shipment: {str(e)}"
        logger.exception(error_msg)
        return False, None, error_msg


def update_shipment_status(zippypost_order) -> bool:
    """
    Update local ZippypostOrder status from Zippypost API.
    
    Args:
        zippypost_order: ZippypostOrder instance
        
    Returns:
        bool: True if updated successfully
    """
    try:
        if not zippypost_order.tracking_number:
            logger.warning(f"No tracking number for ZippypostOrder {zippypost_order.id}")
            return False
        
        success, tracking_data, error = track_shipment(zippypost_order.tracking_number)
        
        if success and tracking_data:
            # Update status based on tracking data
            # Handle different response structures
            status = tracking_data.get('status', '').upper()
            if not status and 'data' in tracking_data:
                status = tracking_data['data'].get('status', '').upper()
            
            # Map Zippypost status to our status choices
            status_mapping = {
                'CREATED': 'CREATED',
                'PICKED_UP': 'PICKED_UP',
                'PICKED UP': 'PICKED_UP',
                'IN_TRANSIT': 'IN_TRANSIT',
                'IN TRANSIT': 'IN_TRANSIT',
                'OUT_FOR_DELIVERY': 'OUT_FOR_DELIVERY',
                'OUT FOR DELIVERY': 'OUT_FOR_DELIVERY',
                'DELIVERED': 'DELIVERED',
                'RTO': 'RTO_INITIATED',
                'RTO_INITIATED': 'RTO_INITIATED',
                'RTO_DELIVERED': 'RTO_DELIVERED',
                'CANCELLED': 'CANCELLED',
                'FAILED': 'FAILED'
            }
            
            new_status = status_mapping.get(status)
            if new_status and new_status != zippypost_order.shipping_status:
                zippypost_order.shipping_status = new_status
                zippypost_order.save(update_fields=['shipping_status', 'updated_at'])
                logger.info(f"Updated ZippypostOrder {zippypost_order.id} status to {new_status}")
                
                # Also update the main Order status if delivered
                if new_status == 'DELIVERED' and zippypost_order.order:
                    zippypost_order.order.status = 'delivered'
                    zippypost_order.order.delivered_at = timezone.now()
                    zippypost_order.order.save(update_fields=['status', 'delivered_at'])
                
            return True
        else:
            logger.error(f"Failed to get tracking data: {error}")
            return False
            
    except Exception as e:
        logger.exception(f"Error updating shipment status: {str(e)}")
        return False


# Helper function to extract response data safely
def extract_shipment_data(response_data: Dict) -> Dict:
    """
    Extract shipment data from Zippypost API response.
    
    Handles both 'data' key and 'RESULT' key formats.
    
    Args:
        response_data: API response dictionary
        
    Returns:
        dict: Extracted shipment information
    """
    # Try different keys where data might be present
    data = response_data.get('data', {})
    if not data:
        data = response_data.get('RESULT', {})
    
    # Extract fields with fallbacks
    # 'awb_number' might be 'awb'
    awb = data.get('awb_number') or data.get('awb')
    # 'courier_name' might be 'courier'
    courier = data.get('courier_name') or data.get('courier')
    # 'zippypost_order_id' might be 'order_id'
    order_id = data.get('order_id') or data.get('zippypost_order_id')
    
    # Fallback: If order_id is missing but we have AWB, use AWB as order_id
    if not order_id and awb:
        order_id = awb
    
    # If using 'RESULT' format, the 'awb' is the main tracking identifier
    
    return {
        'zippypost_order_id': order_id,
        'tracking_number': awb,
        'awb_number': awb,
        'courier_name': courier,
        'label_url': data.get('label', 'NA') if data.get('label') != 'NA' else None,
    }


def process_zippypost_shipment(order):
    """
    Orchestrate the entire Zippypost shipment process:
    1. Create shipment
    2. Extract data (AWB, etc.)
    3. Fetch shipping label
    4. Save to Database (ZippypostOrder & Order)
    
    Args:
        order: Order instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Avoid circular import
        from .models import ZippypostOrder
        
        logger.info(f"Attempting to process Zippypost shipment for order {order.order_id}")
        
        # Check if shipment already exists (prevent duplicates)
        if hasattr(order, 'zippypost') and order.zippypost.shipment_created:
            logger.info(f"Shipment already exists for order {order.order_id}")
            return True

        # 1. Create Shipment
        success, response_data, error = create_shipment(order)
        
        if success and response_data:
            # 2. Extract Data
            shipment_data = extract_shipment_data(response_data)
            
            # 3. Fetch Shipping Label
            if shipment_data.get('tracking_number'):
                label_success, label_url, label_error = get_shipping_label(shipment_data.get('tracking_number'))
                if label_success and label_url:
                    shipment_data['label_url'] = label_url
                    logger.info(f"✅ Fetched shipping label for AWB {shipment_data.get('tracking_number')}")
            
            # 4. Save to Database
            # Create or update ZippypostOrder record
            zippypost_order, created = ZippypostOrder.objects.update_or_create(
                order=order,
                defaults={
                    'zippypost_order_id': shipment_data.get('zippypost_order_id'),
                    'tracking_number': shipment_data.get('tracking_number'),
                    'awb_number': shipment_data.get('awb_number'),
                    'courier_name': shipment_data.get('courier_name'),
                    'shipping_status': shipment_data.get('shipping_status', 'CREATED'),
                    'label_url': shipment_data.get('label_url'),
                    'is_cod': order.payment_method == 'cod',
                    'shipment_created': True
                }
            )
            
            # Update main order with tracking info
            order.tracking_id = shipment_data.get('tracking_number')
            order.courier_partner = shipment_data.get('courier_name')
            order.save(update_fields=['tracking_id', 'courier_partner'])
            
            logger.info(f"✅ Zippypost shipment processed successfully: {shipment_data.get('tracking_number')}")
            return True
            
        else:
            # Log error but don't fail the order
            logger.error(f"❌ Zippypost shipment processing failed: {error}")
            return False

        return False
        
    except Exception as e:
        logger.exception(f"Zippypost integration error for order {order.order_id}: {str(e)}")
        return False


def cancel_shipment(tracking_number: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Cancel a shipment on Zippypost.
    
    Args:
        tracking_number: Shipment AWB / Tracking number
        
    Returns:
        tuple: (success: bool, response_data: dict|None, error_message: str|None)
    """
    try:
        # Endpoint: /cancel/shipment/:AWB
        url = f"{ZIPPYPOST_URL}/cancel/shipment/{tracking_number}"
        
        print(f"\n🌐 ZIPPYPOST: Attempting to cancel shipment: {tracking_number}", flush=True)
        print(f"🌐 ZIPPYPOST: URL: {url}", flush=True)
        
        headers = get_auth_headers()
        print(f"🌐 ZIPPYPOST: Headers: {headers}", flush=True)
        
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        # Log response
        print(f"🌐 ZIPPYPOST: Response Status: {response.status_code}", flush=True)
        print(f"🌐 ZIPPYPOST: Response Body: {response.text}", flush=True)
        
        if response.status_code == 200:
            response_data = response.json()
            # Check for success in response body logic
            if response_data.get('success') is True or response_data.get('status') == 'success':
                print(f"✅ ZIPPYPOST: Shipment {tracking_number} cancelled successfully", flush=True)
                return True, response_data, None
            else:
                error_msg = response_data.get('message', 'Unknown error from API')
                print(f"❌ ZIPPYPOST: Cancel failed: {error_msg}", flush=True)
                return False, response_data, error_msg
        else:
            error_msg = f"API returned status {response.status_code}"
            print(f"❌ ZIPPYPOST: Cancel failed: {error_msg}", flush=True)
            return False, None, error_msg
            
    except Exception as e:
        error_msg = f"Error cancelling shipment: {str(e)}"
        print(f"💥 ZIPPYPOST: Exception: {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        return False, None, error_msg
    """
    Cancel a shipment on Zippypost.
    
    Args:
        tracking_number: Shipment AWB / Tracking number
        
    Returns:
        tuple: (success: bool, response_data: dict|None, error_message: str|None)
    """
    try:
        # Endpoint: /cancel/shipment/:AWB
        url = f"{ZIPPYPOST_URL}/cancel/shipment/{tracking_number}"
        
        logger.info(f"Attempting to cancel Zippypost shipment: {tracking_number}")
        
        response = requests.get(
            url,
            headers=get_auth_headers(),
            timeout=30
        )
        
        # Log response
        logger.info(f"Cancel API Status: {response.status_code}")
        logger.debug(f"Cancel API Response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            # Check for success in response body logic
            if response_data.get('success') is True or response_data.get('status') == 'success':
                logger.info(f"✅ Shipment {tracking_number} cancelled successfully")
                return True, response_data, None
            else:
                error_msg = response_data.get('message', 'Unknown error from API')
                logger.error(f"❌ Cancel failed: {error_msg}")
                return False, response_data, error_msg
        else:
            error_msg = f"API returned status {response.status_code}"
            logger.error(f"❌ Cancel failed: {error_msg}")
            return False, None, error_msg
            
    except Exception as e:
        error_msg = f"Error cancelling shipment: {str(e)}"
        logger.exception(error_msg)
        return False, None, error_msg
