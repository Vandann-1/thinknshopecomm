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


def check_courier_serviceability(
    token: str,
    origin_pincode: str,
    destination_pincode: str,
    weight: float,
    payment_type: str,
    order_amount: float
) -> Tuple[bool, Optional[List], Optional[str]]:
    """
    Check which couriers can service a particular route.
    
    Args:
        token: Authentication token
        origin_pincode: Pickup pincode
        destination_pincode: Delivery pincode
        weight: Package weight in grams
        payment_type: 'prepaid' or 'cod'
        order_amount: Total order amount
        
    Returns:
        tuple: (success, serviceable_couriers_list, error_message)
    """
    url = f"{NIMBUSPOST_BASE_URL}/courier/serviceability"
    
    payload = {
        "origin": origin_pincode,
        "destination": destination_pincode,
        "weight": weight,
        "payment_type": payment_type,
        "order_amount": order_amount
    }
    
    try:
        logger.info(f"Checking courier serviceability:")
        logger.info(f"  Origin: {origin_pincode} → Destination: {destination_pincode}")
        logger.info(f"  Weight: {weight}g, Payment: {payment_type}, Amount: ₹{order_amount}")
        
        response = requests.post(url, headers=get_headers(token), json=payload, timeout=30)
        data = response.json()
        
        logger.debug(f"Serviceability API Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('status'):
            serviceable_couriers = data.get('data', [])
            
            if serviceable_couriers:
                logger.info(f"[SUCCESS] Found {len(serviceable_couriers)} serviceable couriers:")
                # Log the raw data to see actual key names
                logger.debug(f"First courier data: {json.dumps(serviceable_couriers[0], indent=2)}")
                
                for courier in serviceable_couriers[:5]:
                    # Handle multiple possible key formats
                    courier_name = (courier.get('name') or 
                                  courier.get('courier_name') or 
                                  courier.get('courier') or 
                                  'Unknown')
                    courier_id = (courier.get('id') or 
                                courier.get('courier_id') or 
                                courier.get('courier'))
                    freight = courier.get('freight_charges') or courier.get('freight_charge') or courier.get('rate') or 0
                    edd = courier.get('edd') or courier.get('estimated_delivery_days') or 'N/A'
                    
                    logger.info(f"  - {courier_name} (ID: {courier_id})")
                    logger.info(f"    Rate: ₹{freight}, EDD: {edd}")
                
                return True, serviceable_couriers, None
            else:
                logger.warning("[WARNING] No serviceable couriers found for this route")
                return True, [], "No couriers available for this pincode combination"
        
        error_msg = data.get('message', 'Serviceability check failed')
        logger.error(f"[FAILED] {error_msg}")
        return False, None, error_msg
        
    except Exception as e:
        logger.exception(f"[ERROR] Serviceability check error: {str(e)}")
        return False, None, str(e)


def select_best_courier(serviceable_couriers: List[Dict]) -> Optional[Dict]:
    """
    Select the best courier from serviceable options.
    Priority: 1) Lowest cost, 2) Fastest delivery
    
    Args:
        serviceable_couriers: List of serviceable courier options
        
    Returns:
        Selected courier dict or None
    """
    if not serviceable_couriers:
        logger.error("No serviceable couriers provided to select from")
        return None
    
    # Log raw courier data for debugging
    logger.debug(f"Selecting from {len(serviceable_couriers)} couriers")
    logger.debug(f"Sample courier data: {json.dumps(serviceable_couriers[0], indent=2)}")
    
    # Helper function to safely get freight charge
    def get_freight(courier):
        freight = (courier.get('freight_charges') or 
                  courier.get('freight_charge') or 
                  courier.get('rate') or 
                  courier.get('total_charges') or
                  999999)
        try:
            return float(freight)
        except (ValueError, TypeError):
            return 999999.0
    
    # Helper function to parse EDD date and calculate days from today
    def get_edd_days(courier):
        from datetime import datetime
        
        edd = (courier.get('edd') or 
              courier.get('estimated_delivery_days') or 
              courier.get('delivery_days'))
        
        if not edd:
            return 999
        
        # If it's already a number, return it
        if isinstance(edd, (int, float)):
            return int(edd)
        
        # If it's a date string like "25-01-2026", calculate days from today
        if isinstance(edd, str):
            try:
                # Try parsing date format: DD-MM-YYYY
                edd_date = datetime.strptime(edd, '%d-%m-%Y')
                today = datetime.now()
                days_diff = (edd_date - today).days
                return max(0, days_diff)  # Don't return negative days
            except ValueError:
                try:
                    # Try alternative format: YYYY-MM-DD
                    edd_date = datetime.strptime(edd, '%Y-%m-%d')
                    today = datetime.now()
                    days_diff = (edd_date - today).days
                    return max(0, days_diff)
                except ValueError:
                    # If it's a plain number as string
                    try:
                        return int(edd)
                    except (ValueError, TypeError):
                        return 999
        
        return 999
    
    # Sort by freight charge (ascending) then by delivery days (ascending)
    sorted_couriers = sorted(
        serviceable_couriers,
        key=lambda x: (get_freight(x), get_edd_days(x))
    )
    
    selected = sorted_couriers[0]
    
    # Extract courier info with fallback key names
    courier_name = (selected.get('name') or 
                   selected.get('courier_name') or 
                   selected.get('courier') or 
                   'Unknown')
    courier_id = (selected.get('id') or 
                 selected.get('courier_id') or 
                 selected.get('courier'))
    freight = get_freight(selected)
    edd_days = get_edd_days(selected)
    edd_display = selected.get('edd') or selected.get('estimated_delivery_days') or 'N/A'
    
    logger.info(f"[SELECTED] Best courier: {courier_name}")
    logger.info(f"[SELECTED] Courier ID: {courier_id}")
    logger.info(f"[SELECTED] Rate: ₹{freight}, EDD: {edd_display} ({edd_days} days)")
    
    # Validate that we have a courier_id
    if not courier_id:
        logger.error(f"[ERROR] Selected courier has no ID! Data: {json.dumps(selected, indent=2)}")
        return None
    
    return selected


def get_enabled_couriers() -> Tuple[bool, Optional[List], Optional[str]]:
    """
    Get list of couriers enabled in your NimbusPost account.
    
    Returns:
        tuple: (success, courier_list, error_message)
    """
    token = login_nimbuspost()
    if not token:
        return False, None, "Authentication failed"
    
    url = f"{NIMBUSPOST_BASE_URL}/courier"
    
    try:
        logger.info("Fetching enabled couriers from account...")
        response = requests.get(url, headers=get_headers(token), timeout=30)
        data = response.json()
        
        if response.status_code == 200 and data.get('status'):
            couriers = data.get('data', [])
            logger.info(f"[SUCCESS] Found {len(couriers)} enabled couriers in account")
            if couriers:
                for courier in couriers[:5]:
                    logger.info(f"  - {courier.get('name')} (ID: {courier.get('id')})")
            return True, couriers, None
        
        error_msg = data.get('message', 'Failed to fetch couriers')
        logger.error(f"[FAILED] {error_msg}")
        return False, None, error_msg
        
    except Exception as e:
        logger.exception(f"[ERROR] Courier list error: {str(e)}")
        return False, None, str(e)


def create_nimbuspost_shipment(order) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Create a shipment on NimbusPost - with proper serviceability check.
    
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
        
        # STEP 1: Check courier serviceability for this specific route
        logger.info("=" * 80)
        logger.info("STEP 1: Checking Courier Serviceability")
        logger.info("=" * 80)
        
        success_check, serviceable_couriers, error_check = check_courier_serviceability(
            token=token,
            origin_pincode=NIMBUSPOST_PICKUP_PINCODE,
            destination_pincode=shipping_addr.pincode,
            weight=total_weight,
            payment_type=payment_type,
            order_amount=float(order.total_amount)
        )
        
        if not success_check:
            error_msg = f"Serviceability check failed: {error_check}"
            logger.error(f"[FAILED] {error_msg}")
            return False, None, error_msg
        
        if not serviceable_couriers or len(serviceable_couriers) == 0:
            error_msg = (
                f"No courier can service the route from {NIMBUSPOST_PICKUP_PINCODE} "
                f"to {shipping_addr.pincode}. This pincode may not be serviceable or "
                f"you need to enable more courier partners in your NimbusPost account."
            )
            logger.error(f"[FAILED] {error_msg}")
            logger.error("=" * 80)
            logger.error("RECOMMENDED ACTIONS:")
            logger.error("1. Verify the destination pincode is correct")
            logger.error("2. Enable more courier partners in NimbusPost dashboard:")
            logger.error("   Settings → Courier Partners → Enable Delhivery, Blue Dart, DTDC, etc.")
            logger.error("3. Contact NimbusPost support: tech@nimbuspost.com")
            logger.error("=" * 80)
            return False, None, error_msg
        
        # STEP 2: Select the best courier from serviceable options
        logger.info("=" * 80)
        logger.info("STEP 2: Selecting Best Courier")
        logger.info("=" * 80)
        
        selected_courier = select_best_courier(serviceable_couriers)
        if not selected_courier:
            error_msg = "Failed to select a valid courier from serviceable options"
            logger.error(f"[FAILED] {error_msg}")
            return False, None, error_msg
        
        # Extract courier ID with multiple fallback key names
        selected_courier_id = str(
            selected_courier.get('id') or 
            selected_courier.get('courier_id') or 
            selected_courier.get('courier') or 
            ''
        )
        
        selected_courier_name = (
            selected_courier.get('name') or 
            selected_courier.get('courier_name') or 
            selected_courier.get('courier') or 
            'Unknown'
        )
        
        # Final validation
        if not selected_courier_id or selected_courier_id == 'None':
            error_msg = f"Courier ID is invalid or missing. Courier data: {json.dumps(selected_courier, indent=2)}"
            logger.error(f"[FAILED] {error_msg}")
            return False, None, error_msg
        
        logger.info(f"Selected: {selected_courier_name} (ID: {selected_courier_id})")
        
        # STEP 3: Create shipment payload
        logger.info("=" * 80)
        logger.info("STEP 3: Creating Shipment")
        logger.info("=" * 80)
        
        payload = {
            "order_number": order.order_id,
            "shipping_charges": float(order.shipping_cost) if order.shipping_cost else 0,
            "discount": float(order.discount_amount) if order.discount_amount else 0,
            "cod_charges": cod_charges,
            "payment_type": payment_type,
            "order_amount": float(order.total_amount),
            "package_weight": total_weight,
            "package_length": 10,
            "package_breadth": 10,
            "package_height": 10,
            "courier_id": selected_courier_id,  # Use the verified serviceable courier
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
                "phone": NIMBUSPOST_PICKUP_PHONE,
                "email": NIMBUSPOST_SUPPORT_EMAIL
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
            logger.info(f"  AWB Number: {data.get('data', {}).get('awb_number')}")
            logger.info(f"  Courier: {data.get('data', {}).get('courier_name')}")
            logger.info(f"  Shipment ID: {data.get('data', {}).get('shipment_id')}")
            logger.info(f"  Label URL: {data.get('data', {}).get('label')}")
            logger.info("=" * 80)
            return True, data, None
        
        error_msg = data.get('message', 'Unknown error')
        logger.error(f"[FAILED] Shipment creation failed: {error_msg}")
        
        # Provide helpful error context
        if "Invalid Courier ID" in error_msg:
            logger.error("=" * 80)
            logger.error("CRITICAL: Courier ID was marked serviceable but got rejected!")
            logger.error("This might be a temporary issue with the courier.")
            logger.error("Please try again or contact NimbusPost support.")
            logger.error("=" * 80)
        
        return False, data, error_msg

    except Exception as e:
        logger.exception(f"[ERROR] NimbusPost Create Shipment Error: {str(e)}")
        return False, None, str(e)


def process_nimbuspost_shipment(order):
    """
    Orchestrate the entire NimbusPost shipment process.
    
    Args:
        order: Order instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from .models import NimbuspostOrder
        
        logger.info(f"Processing NimbusPost shipment for order {order.order_id}")
        
        # Check if shipment already exists
        if hasattr(order, 'nimbuspost') and order.nimbuspost.awb_number:
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
            order.tracking_id = shipment_data.get('awb_number')
            order.courier_partner = shipment_data.get('courier_name')
            order.save(update_fields=['tracking_id', 'courier_partner'])
            
            logger.info(f"[SUCCESS] NimbusPost shipment processed successfully")
            logger.info(f"AWB: {shipment_data.get('awb_number')}, Courier: {shipment_data.get('courier_name')}")
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