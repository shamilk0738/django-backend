from django.db.models import Prefetch
from rest_framework import viewsets

from .models import Brand, Product, Scheme
from .serializers import BrandDetailSerializer, BrandListSerializer, ProductSerializer


def active_products():
    return Product.objects.filter(is_active=True).select_related('brand').prefetch_related(
        Prefetch('schemes', queryset=Scheme.objects.filter(is_active=True))
    )


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return Brand.objects.filter(is_active=True).prefetch_related(
            Prefetch('products', queryset=active_products())
        )

    def get_serializer_class(self):
        return BrandDetailSerializer if self.action == 'retrieve' else BrandListSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = active_products()
        brand = self.request.query_params.get('brand')
        q = self.request.query_params.get('q')
        if brand:
            qs = qs.filter(brand_id=brand)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs