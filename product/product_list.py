from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max, Count, Avg,When,Case
from django.http import JsonResponse
from django.views.generic import ListView
from django.db import models
from .models import (
    Product, Category, Brand, Color, Size, Material, 
    ProductVariant, Collection, ProductAttribute, ProductAttributeValue,ProductReview
)
from django.db.models import (
    Q, F, Case, When, Value, Count, Avg, Min, Max, 
    DecimalField, FloatField, IntegerField,Sum
)
from .models import *
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, F,When,Value
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import logging
from .utils import (get_additional_homepage_context)
logger = logging.getLogger(__name__)
from django.views.decorators.cache import cache_page
from django.db.models.functions import Coalesce
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings



# Add To cart 


