# products/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.inclusion_tag('products/partials/price_range_slider.html')
def price_range_slider(min_price, max_price, current_min, current_max):
    return {
        'min_price': min_price or 0,
        'max_price': max_price or 1000,
        'current_min': current_min or min_price or 0,
        'current_max': current_max or max_price or 1000,
    }

@register.inclusion_tag('products/partials/product_card.html')
def product_card(product, show_compare=True, show_wishlist=True):
    return {
        'product': product,
        'show_compare': show_compare,
        'show_wishlist': show_wishlist,
    }
