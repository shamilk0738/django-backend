from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Attendance, User
from accounts.permissions import IsAdminRole, IsSalesmanRole
from .models import Order
from .serializers import OrderEditSerializer, OrderSerializer, OrderStatusSerializer


class OrderViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [IsSalesmanRole()]
        if self.action == 'partial_update':
            return [IsAdminRole()]
        # list, retrieve, edit → login ചെയ്ത ആർക്കും (edit-ൽ role താഴെ പരിശോധിക്കുന്നു)
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return OrderStatusSerializer
        return OrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related('shop', 'salesman').prefetch_related('items__product')
        user = self.request.user
        if not user.is_admin_role:
            if user.role == 'salesman':
                qs = qs.filter(salesman=user)
            else:
                qs = qs.filter(shop__user=user)
        shop = self.request.query_params.get('shop')
        status = self.request.query_params.get('status')
        if shop:
            qs = qs.filter(shop_id=shop)
        if status:
            qs = qs.filter(status=status)
        return qs

    @action(detail=True, methods=['patch'], url_path='edit')
    def edit(self, request, pk=None):
        """PATCH /api/orders/{id}/edit/ — pending order-ന്റെ items / notes മാറ്റാൻ."""
        order = self.get_object()   # salesman-ന് സ്വന്തം orders മാത്രം, മറ്റുള്ളവ 404

        user = request.user
        if not (user.is_admin_role or user.role == 'salesman'):
            return Response({'detail': 'ഇത് ചെയ്യാൻ അനുമതി ഇല്ല.'}, status=403)

        if order.status != Order.Status.PENDING:
            return Response(
                {'status': ['Pending ആയ order മാത്രമേ edit ചെയ്യാൻ കഴിയൂ.']},
                status=400)

        serializer = OrderEditSerializer(order, data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order, context={'request': request}).data)


def _date_param(request, name, default):
    try:
        return parse_date(request.query_params.get(name) or '') or default
    except ValueError:
        return default


class SalesmanPerformanceView(APIView):
    """GET /api/reports/salesman-performance/?from=2025-01-01&to=2025-01-31"""
    permission_classes = [IsAdminRole]

    def get(self, request):
        today = timezone.localdate()
        date_from = _date_param(request, 'from', today.replace(day=1))
        date_to = _date_param(request, 'to', today)

        rows = []
        for s in User.objects.filter(role=User.Role.SALESMAN, is_active=True):
            orders = Order.objects.filter(
                salesman=s, created_at__date__range=(date_from, date_to)
            ).exclude(status=Order.Status.CANCELLED)
            agg = orders.aggregate(total_orders=Count('id'), total_sales=Sum('total_amount'))
            total_sales = agg['total_sales'] or 0
            profile = getattr(s, 'salesman_profile', None)
            target = profile.monthly_target if profile else 0
            rows.append({
                'salesman_id': s.id,
                'name': s.get_full_name() or s.username,
                'route': profile.route.name if profile and profile.route else None,
                'total_orders': agg['total_orders'] or 0,
                'total_sales': total_sales,
                'shops_covered': orders.values('shop').distinct().count(),
                'attendance_days': Attendance.objects.filter(
                    salesman=s, date__range=(date_from, date_to)).count(),
                'monthly_target': target,
                'target_achieved_percent': round(float(total_sales) / float(target) * 100, 1) if target else None,
            })
        rows.sort(key=lambda r: r['total_sales'], reverse=True)
        return Response({'from': date_from, 'to': date_to, 'salesmen': rows})