"""
Quick test script to diagnose Zippypost API issue
Run this with: python test_zippypost.py
"""

import sys
import os
import django
import logging

# Set up simple logging to file
logging.basicConfig(
    filename='zippypost_test_result.txt',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sketezo.settings')
django.setup()

from orders.models import Order
from orders.zippypost_utils import create_shipment, get_auth_headers
import json

def log_print(msg):
    print(msg)
    logging.info(msg)

log_print("=" * 80)
log_print("ZIPPYPOST API TEST")
log_print("=" * 80)

# Check Constants
from orders.constants import ZIPPYPOST_WAREHOUSE_ID, ZIPPYPOST_COURIER_ID, ZIPPYPOST_MODE_ID
log_print(f"Configured IDs: Warehouse={ZIPPYPOST_WAREHOUSE_ID}, Courier={ZIPPYPOST_COURIER_ID}, Mode={ZIPPYPOST_MODE_ID}")


# Test authentication headers
log_print("\n1. Testing Authentication Headers:")
log_print("-" * 40)
try:
    headers = get_auth_headers()
    log_print(f"Headers keys: {list(headers.keys())}")
    for key, value in headers.items():
        if key == 'authorization':
            pass # Don't log full token
        else:
            log_print(f"{key}: {value}")
    log_print("✅ Headers generated successfully")
except Exception as e:
    log_print(f"❌ Header generation failed: {e}")
    sys.exit(1)

# Get the most recent paid order
log_print("\n2. Finding Recent Paid Order:")
log_print("-" * 40)
try:
    # Try getting any confirmed order if no paid ones, just for testing payload generation
    order = Order.objects.filter(payment_status='paid').order_by('-created_at').first()
    if not order:
        order = Order.objects.last()
        log_print("⚠️ No paid orders found. Using last created order for testing payload generation.")
    
    if not order:
        log_print("❌ No orders found in database.")
        sys.exit(1)
    
    log_print(f"✅ Using order: {order.order_id}")
    log_print(f"   Total Amount: {order.total_amount}")
    
    if order.shipping_address:
        log_print(f"   Shipping to: {order.shipping_address.city}, {order.shipping_address.pincode}")
    else:
        log_print("   ❌ No shipping address!")
        
except Exception as e:
    log_print(f"❌ Error finding order: {e}")
    sys.exit(1)

# Test Zippypost API Call
log_print("\n3. Testing Zippypost API Call:")
log_print("-" * 40)
try:
    # We will invoke create_shipment but catch extensive logs
    success, response_data, error = create_shipment(order)
    
    if success:
        log_print("\n✅✅✅ SUCCESS! Shipment created!")
        log_print(json.dumps(response_data, indent=2))
    else:
        log_print("\n❌ Shipment creation FAILED")
        log_print(f"Error Message: {error}")
        if response_data:
            log_print("Full Response Data:")
            log_print(json.dumps(response_data, indent=2))
            
except Exception as e:
    log_print(f"\n❌ Exception occurred: {type(e).__name__}")
    log_print(f"Error: {str(e)}")
    import traceback
    logging.error(traceback.format_exc())

log_print("\n" + "=" * 80)
log_print("TEST COMPLETE")
