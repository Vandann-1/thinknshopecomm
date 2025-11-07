from .models import Cart, CartItem



# Cart utility functions
def get_or_create_cart(request):
    """
    Get or create cart for user or guest session
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={'session_key': None}
        )
    else:
        if not request.session.session_key:
            request.session.create()
        
        cart, created = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            is_active=True,
            defaults={'user': None}
        )
    
    return cart

def merge_guest_cart_with_user_cart(request):
    """
    Merge guest cart with user cart after login
    """
    if not request.session.session_key:
        return
    
    try:
        guest_cart = Cart.objects.get(
            session_key=request.session.session_key,
            is_active=True
        )
        
        user_cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )
        
        # Merge cart items
        for guest_item in guest_cart.items.all():
            try:
                user_item = user_cart.items.get(
                    product=guest_item.product,
                    variant=guest_item.variant
                )
                # Update quantity and price
                user_item.quantity += guest_item.quantity
                user_item.unit_price = guest_item.get_current_price()
                user_item.save()
            except CartItem.DoesNotExist:
                # Move item to user cart
                guest_item.cart = user_cart
                guest_item.save()
        
        # Deactivate guest cart
        guest_cart.is_active = False
        guest_cart.save()
        
    except Cart.DoesNotExist:
        pass
