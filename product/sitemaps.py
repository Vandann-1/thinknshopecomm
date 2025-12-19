# sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    protocol = 'https'
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            'main_page',
            'login',
            'register',
            'policy',
            'terms',
        ]

    def location(self, item):
        return reverse(item)
