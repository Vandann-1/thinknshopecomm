from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class DevModeByHTTPS:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_https = request.is_secure()
        dev_path = reverse("sketezo_development")

        # If in production (HTTPS) and not visiting dev path, block access
        if is_https and request.path != dev_path:
            return redirect("sketezo_development")

        return self.get_response(request)
