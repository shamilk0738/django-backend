
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
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return OrderStatusSerializer
        return OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.select_related(
            'shop',
            'salesman',
        ).prefetch_related('items__product')

        user = self.request.user

        if not user.is_admin_role:
            if user.role == 'salesman':
                queryset = queryset.filter(salesman=user)
            else:
                queryset = queryset.filter(shop__user=user)

        shop = self.request.query_params.get('shop')
        status = self.request.query_params.get('status')

        if shop:
            queryset = queryset.filter(shop_id=shop)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    @action(detail=True, methods=['patch'], url_path='edit')
    def edit(self, request, pk=None):
        order = self.get_object()
        user = request.user

        if not (user.is_admin_role or user.role == 'salesman'):
            return Response(
                {'detail': 'Permission denied.'},
                status=403,
            )

        if order.status != Order.Status.PENDING:
            return Response(
                {'status': ['Only pending orders can be edited.']},
                status=400,
            )

        serializer = OrderEditSerializer(
            order,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(
            OrderSerializer(
                order,
                context={'request': request},
            ).data
        )


def _date_param(request, name, default):
    try:
        return parse_date(
            request.query_params.get(name) or ''
        ) or default
    except ValueError:
        return default


class SalesmanPerformanceView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        today = timezone.localdate()
        date_from = _date_param(
            request,
            'from',
            today.replace(day=1),
        )
        date_to = _date_param(request, 'to', today)

        rows = []

        salesmen = User.objects.filter(
            role=User.Role.SALESMAN,
            is_active=True,
        )

        for salesman in salesmen:
            orders = Order.objects.filter(
                salesman=salesman,
                created_at__date__range=(date_from, date_to),
            ).exclude(status=Order.Status.CANCELLED)

            aggregate = orders.aggregate(
                total_orders=Count('id'),
                total_sales=Sum('total_amount'),
            )

            total_sales = aggregate['total_sales'] or 0
            profile = getattr(salesman, 'salesman_profile', None)
            target = profile.monthly_target if profile else 0

            rows.append({
                'salesman_id': salesman.id,
                'name': salesman.get_full_name() or salesman.username,
                'route': (
                    profile.route.name
                    if profile and profile.route
                    else None
                ),
                'total_orders': aggregate['total_orders'] or 0,
                'total_sales': total_sales,
                'shops_covered': orders.values('shop').distinct().count(),
                'attendance_days': Attendance.objects.filter(
                    salesman=salesman,
                    date__range=(date_from, date_to),
                ).count(),
                'monthly_target': target,
                'target_achieved_percent': (
                    round(
                        float(total_sales) / float(target) * 100,
                        1,
                    )
                    if target
                    else None
                ),
            })

        rows.sort(
            key=lambda row: row['total_sales'],
            reverse=True,
        )

        return Response({
            'from': date_from,
            'to': date_to,
            'salesmen': rows,
        })
