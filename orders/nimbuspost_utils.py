import requests
import json
import logging
from typing import Dict, Optional, Tuple, List
from decimal import Decimal
from django.conf import settings
from .constants import (
    NIMBUSPOST_EMAIL, 
    NIMBUSPOST_PASSWORD,
    NIMBUSPOST_WAREHOUSE_NAME,
    NIMBUSPOST_SUPPORT_EMAIL,
    NIMBUSPOST_SUPPORT_PHONE,
    NIMBUSPOST_PICKUP_NAME,
    NIMBUSPOST_PICKUP_ADDRESS,
    NIMBUSPOST_PICKUP_CITY,
    NIMBUSPOST_PICKUP_STATE,
    NIMBUSPOST_PICKUP_PINCODE,
    NIMBUSPOST_PICKUP_PHONE
)

# Set up logger
logger = logging.getLogger(__name__)

# Base URL for NimbusPost API
NIMBUSPOST_BASE_URL = "https://api.nimbuspost.com/v1"

def login_nimbuspost() -> Optional[str]:
    """
    Authenticate with NimbusPost and retrieve a Bearer Token.
    
    Returns:
        str: Bearer token if successful, None otherwise.
    """
    url = f"{NIMBUSPOST_BASE_URL}/users/login"
    payload = {
        "email": NIMBUSPOST_EMAIL,
        "password": NIMBUSPOST_PASSWORD
    }
    
    try:
        logger.info(f"Attempting NimbusPost login for {NIMBUSPOST_EMAIL}")
        
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            error_msg = data.get('message', 'Unknown error')
            logger.error(f"[FAILED] Login failed: {error_msg}")
            return None
        
        if data.get('status') and data.get('data'):
            token = data.get('data')
            if isinstance(token, str) and token:
                logger.info("[SUCCESS] NimbusPost login successful")
                return token
        
        logger.error(f"[FAILED] No token in response")
        return None
        
    except Exception as e:
        logger.error(f"[ERROR] NimbusPost Login Error: {str(e)}")
        return None


def get_headers(token: str) -> Dict[str, str]:
    """Generate headers for NimbusPost API requests."""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

def create_nimbuspost_shipment(order) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Create a shipment on NimbusPost - WITHOUT automatic courier selection.
    Courier will be assigned manually from NimbusPost dashboard.
    
    Args:
        order: Order instance
        
    Returns:
        tuple: (success, response_data, error_message)
    """
    logger.info(f"{'='*80}")
    logger.info(f"Creating NimbusPost shipment for order {order.order_id}")
    logger.info(f"{'='*80}")
    
    token = login_nimbuspost()
    if not token:
        return False, None, "Authentication failed"

    try:
        shipping_addr = order.shipping_address
        if not shipping_addr:
            return False, None, "Order missing shipping address"
        
        # Calculate total weight
        total_weight = 0.0
        for item in order.items.all():
            product = item.product
            item_weight_g = float(product.weight) if hasattr(product, 'weight') and product.weight else 500.0
            total_weight += item_weight_g * item.quantity
        
        if total_weight < 300:
            total_weight = 300
        
        logger.info(f"Total package weight: {total_weight}g")
        
        # Prepare order items
        order_items = []
        for item in order.items.all():
            order_items.append({
                "name": item.product.name,
                "qty": str(item.quantity),
                "price": str(float(item.unit_price)),
                "sku": item.variant.sku if item.variant and item.variant.sku else f"SKU-{item.product.id}"
            })
        
        # Calculate COD charges
        cod_charges = 0
        payment_type = "cod" if order.payment_method == 'cod' else "prepaid"
        if payment_type == 'cod':
            cod_charges = 30
        
        # Create shipment payload - as per NimbusPost API documentation
        logger.info("=" * 80)
        logger.info("Creating Shipment (Courier will be assigned manually from dashboard)")
        logger.info("=" * 80)
        
        payload = {
            "order_number": order.order_id,
            "shipping_charges": float(order.shipping_cost) if order.shipping_cost else 0,
            "discount": float(order.discount_amount) if order.discount_amount else 0,
            "cod_charges": cod_charges,
            "payment_type": payment_type,
            "order_amount": float(order.total_amount),
            "package_weight": total_weight,
            "package_length": 25,
            "package_breadth": 9,
            "package_height": 9,
            "consignee": {
                "name": shipping_addr.full_name,
                "address": shipping_addr.address_line_1,
                "address_2": shipping_addr.address_line_2 or "",
                "city": shipping_addr.city,
                "state": shipping_addr.state,
                "pincode": shipping_addr.pincode,
                "phone": shipping_addr.phone_number
            },
            "pickup": {
                "warehouse_name": NIMBUSPOST_WAREHOUSE_NAME,
                "name": NIMBUSPOST_PICKUP_NAME,
                "address": NIMBUSPOST_PICKUP_ADDRESS,
                "city": NIMBUSPOST_PICKUP_CITY,
                "state": NIMBUSPOST_PICKUP_STATE,
                "pincode": NIMBUSPOST_PICKUP_PINCODE,
                "phone": NIMBUSPOST_PICKUP_PHONE
            },
            "order_items": order_items
        }
        
        logger.debug(json.dumps(payload, indent=2))
        
        url = f"{NIMBUSPOST_BASE_URL}/shipments"
        headers = get_headers(token)
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        logger.info(f"Response Status Code: {response.status_code}")
        logger.debug(f"Response Body: {response.text}")
        
        data = response.json()
        
        # Check for success
        if response.status_code in [200, 201] and data.get('status'):
            logger.info("=" * 80)
            logger.info("[SUCCESS] Shipment Created Successfully!")
            logger.info("=" * 80)
            logger.info(f"  Order ID: {data.get('data', {}).get('order_id')}")
            logger.info(f"  Shipment ID: {data.get('data', {}).get('shipment_id')}")
            logger.info(f"  Status: {data.get('data', {}).get('status')}")
            logger.info(f"  Payment Type: {data.get('data', {}).get('payment_type')}")
            logger.info("  Note: Assign courier manually from NimbusPost dashboard")
            logger.info("=" * 80)
            return True, data, None
        
        error_msg = data.get('message', 'Unknown error')
        logger.error(f"[FAILED] Shipment creation failed: {error_msg}")
        return False, data, error_msg

    except Exception as e:
        logger.exception(f"[ERROR] NimbusPost Create Shipment Error: {str(e)}")
        return False, None, str(e)


def process_nimbuspost_shipment(order):
    """
    Process NimbusPost shipment creation without automatic courier selection.
    
    Args:
        order: Order instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from .models import NimbuspostOrder
        
        logger.info(f"Processing NimbusPost shipment for order {order.order_id}")
        
        # Check if shipment already exists
        if hasattr(order, 'nimbuspost') and order.nimbuspost.shipment_id:
            logger.info(f"Shipment already exists for order {order.order_id}")
            return True

        # Create shipment
        success, response_data, error = create_nimbuspost_shipment(order)
        
        if success and response_data:
            shipment_data = response_data.get('data', {})
            
            # Save to Database
            nimbuspost_order, created = NimbuspostOrder.objects.update_or_create(
                order=order,
                defaults={
                    'shipment_id': str(shipment_data.get('shipment_id', '')),
                    'awb_number': shipment_data.get('awb_number', ''),
                    'courier_id': str(shipment_data.get('courier_id', '')),
                    'courier_name': shipment_data.get('courier_name', ''),
                    'status': shipment_data.get('status', 'CREATED').upper(),
                    'label_url': shipment_data.get('label', ''),
                    'additional_info': shipment_data
                }
            )
            
            # Update main order
            if shipment_data.get('awb_number'):
                order.tracking_id = shipment_data.get('awb_number')
            if shipment_data.get('courier_name'):
                order.courier_partner = shipment_data.get('courier_name')
            order.save(update_fields=['tracking_id', 'courier_partner'])
            
            logger.info(f"[SUCCESS] NimbusPost shipment processed successfully")
            logger.info(f"Shipment ID: {shipment_data.get('shipment_id')}, Status: {shipment_data.get('status')}")
            return True
            
        else:
            logger.error(f"[FAILED] NimbusPost shipment processing failed: {error}")
            return False

    except Exception as e:
        logger.exception(f"NimbusPost integration error for order {order.order_id}: {str(e)}")
        return False
# ============================================================================================================================================
def track_shipment(awb: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Track shipment using AWB - Returns complete tracking data."""
    token = login_nimbuspost()
    if not token:
        return False, None, "Authentication failed"
        
    url = f"{NIMBUSPOST_BASE_URL}/shipments/track/{awb}"
    
    try:
        logger.info(f"Tracking shipment with AWB: {awb}")
        response = requests.get(url, headers=get_headers(token), timeout=30)
        data = response.json()
        
        if response.status_code == 200 and data.get('status'):
            logger.info(f"[SUCCESS] Tracking data retrieved for AWB: {awb}")
            logger.debug(f"Tracking response: {data}")
            return True, data, None
            
        error_msg = data.get('message', 'Tracking failed')
        logger.error(f"[FAILED] Tracking failed for AWB {awb}: {error_msg}")
        return False, data, error_msg
        
    except Exception as e:
        logger.exception(f"[ERROR] Tracking error for AWB {awb}: {str(e)}")
        return False, None, str(e)


def parse_tracking_data(api_response: Dict) -> Dict:
    """
    Parse NimbusPost tracking API response into structured data.
    
    Returns:
        Dict with keys: shipment_info, tracking_events, status_summary
    """
    if not api_response or not api_response.get('data'):
        return {}
    
    data = api_response.get('data', {})
    
    # Basic shipment information
    shipment_info = {
        'id': data.get('id'),
        'order_id': data.get('order_id'),
        'order_number': data.get('order_number'),
        'awb_number': data.get('awb_number'),
        'rto_awb': data.get('rto_awb'),
        'courier_id': data.get('courier_id'),
        'warehouse_id': data.get('warehouse_id'),
        'rto_warehouse_id': data.get('rto_warehouse_id'),
        'status': data.get('status'),
        'rto_status': data.get('rto_status'),
        'shipment_info': data.get('shipment_info'),
        'created': data.get('created'),
    }
    
    # Parse tracking history/events
    history = data.get('history', [])
    tracking_events = []
    
    for event in history:
        parsed_event = {
            'status_code': event.get('status_code'),
            'location': event.get('location'),
            'event_time': event.get('event_time'),
            'message': event.get('message'),
            'timestamp': None,
            'is_rto': False,
            'is_delivered': False,
            'is_exception': False,
            'icon': 'check-circle'
        }
        
        # Parse timestamp
        try:
            from datetime import datetime
            time_str = event.get('event_time')
            if time_str:
                # Format: "2021-03-02 18:19"
                parsed_event['timestamp'] = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        except Exception as e:
            logger.warning(f"Failed to parse timestamp: {time_str}, error: {e}")
        
        # Categorize event based on status code
        status_code = event.get('status_code', '')
        
        if status_code == 'DL':
            parsed_event['is_delivered'] = True
            parsed_event['icon'] = 'check-circle'
        elif status_code == 'RT-DL':
            parsed_event['is_delivered'] = True
            parsed_event['is_rto'] = True
            parsed_event['icon'] = 'rotate-ccw'
        elif status_code in ['RT', 'RT-IT']:
            parsed_event['is_rto'] = True
            parsed_event['icon'] = 'rotate-ccw'
        elif status_code == 'OFD':
            parsed_event['icon'] = 'truck'
        elif status_code == 'IT':
            parsed_event['icon'] = 'navigation'
        elif status_code == 'EX':
            parsed_event['is_exception'] = True
            parsed_event['icon'] = 'alert-circle'
        elif status_code == 'PP':
            parsed_event['icon'] = 'package'
        
        tracking_events.append(parsed_event)
    
    # Status summary
    status_summary = {
        'current_status': shipment_info.get('status', 'unknown').upper(),
        'rto_status': shipment_info.get('rto_status'),
        'is_rto': shipment_info.get('status', '').lower() in ['rto', 'rt'],
        'is_delivered': shipment_info.get('status', '').lower() == 'delivered' or 
                       shipment_info.get('rto_status', '').lower() == 'delivered',
        'total_events': len(tracking_events),
        'latest_location': tracking_events[0].get('location') if tracking_events else None,
        'latest_update': tracking_events[0].get('event_time') if tracking_events else None,
    }
    
    return {
        'shipment_info': shipment_info,
        'tracking_events': tracking_events,
        'status_summary': status_summary
    }


def get_status_display_info(status_code: str) -> Dict:
    """
    Get human-readable status information.
    
    Returns dict with: display_name, color, icon
    """
    status_map = {
        'PP': {
            'display_name': 'Pending Pickup',
            'color': 'yellow',
            'icon': 'clock',
            'description': 'Awaiting courier pickup'
        },
        'IT': {
            'display_name': 'In Transit',
            'color': 'blue',
            'icon': 'navigation',
            'description': 'Shipment is on the way'
        },
        'EX': {
            'display_name': 'Exception',
            'color': 'orange',
            'icon': 'alert-circle',
            'description': 'Delivery exception occurred'
        },
        'OFD': {
            'display_name': 'Out For Delivery',
            'color': 'purple',
            'icon': 'truck',
            'description': 'Out for delivery today'
        },
        'DL': {
            'display_name': 'Delivered',
            'color': 'green',
            'icon': 'check-circle',
            'description': 'Successfully delivered'
        },
        'RT': {
            'display_name': 'RTO Initiated',
            'color': 'red',
            'icon': 'rotate-ccw',
            'description': 'Return to origin initiated'
        },
        'RT-IT': {
            'display_name': 'RTO In Transit',
            'color': 'red',
            'icon': 'rotate-ccw',
            'description': 'Returning to origin'
        },
        'RT-DL': {
            'display_name': 'RTO Delivered',
            'color': 'red',
            'icon': 'rotate-ccw',
            'description': 'Returned to origin'
        },
    }
    
    return status_map.get(status_code.upper(), {
        'display_name': status_code,
        'color': 'gray',
        'icon': 'info',
        'description': 'Status update'
    })
# ======================================================================================================================
def cancel_shipment(awb: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Cancel shipment using AWB number via Nimbuspost API."""
    token = login_nimbuspost()
    if not token:
        return False, None, "Authentication failed"
    
    # ✅ Correct Nimbuspost API endpoint
    url = f"{NIMBUSPOST_BASE_URL}/shipments/cancel"
    payload = {"awb": awb}
    
    try:
        logger.info(f"Attempting to cancel shipment with AWB: {awb}")
        response = requests.post(
            url, 
            headers=get_headers(token), 
            json=payload, 
            timeout=30
        )
        data = response.json()
        
        # ✅ Check response according to Nimbuspost docs
        if response.status_code == 200 and data.get('status') is True:
            success_msg = data.get('message', 'Shipment cancelled successfully')
            logger.info(f"[SUCCESS] {success_msg}")
            return True, data, None
        
        # Handle failure response
        error_msg = data.get('message', 'Cancellation failed')
        logger.error(f"[FAILED] Cancellation failed: {error_msg} (Status: {response.status_code})")
        return False, data, error_msg
        
    except requests.exceptions.Timeout:
        logger.error(f"[ERROR] Request timeout while cancelling AWB: {awb}")
        return False, None, "Request timeout - please try again"
    except requests.exceptions.RequestException as e:
        logger.exception(f"[ERROR] Network error during cancellation: {str(e)}")
        return False, None, f"Network error: {str(e)}"
    except Exception as e:
        logger.exception(f"[ERROR] Unexpected cancellation error: {str(e)}")
        return False, None, str(e)