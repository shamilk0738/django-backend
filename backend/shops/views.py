from rest_framework import viewsets

from accounts.permissions import IsAdminOrReadOnly
from .models import Shop
from .serializers import ShopSerializer


class ShopViewSet(viewsets.ModelViewSet):
    serializer_class = ShopSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Shop.objects.select_related('route', 'salesman')
        user = self.request.user
        if not user.is_admin_role:
            if user.role == 'salesman':
                qs = qs.filter(salesman=user)      
            else:
                qs = qs.filter(user=user)
        q = self.request.query_params.get('q')
        district = self.request.query_params.get('district')
        if q:
            qs = qs.filter(name__icontains=q)
        if district:
            qs = qs.filter(district=district)
        return qs