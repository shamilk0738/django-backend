
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import OrderItem

from .views import pieces, valid_orders


def _parse(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


class MySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        start = _parse(
            request.query_params.get('from'),
            today.replace(day=1),
        )
        end = _parse(
            request.query_params.get('to'),
            today,
        )

        if start > end:
            start, end = end, start

        orders = valid_orders().filter(
            salesman=request.user,
            created_at__date__range=(start, end),
        )

        totals = orders.aggregate(
            total=Sum('total_amount'),
            count=Count('id'),
        )

        day_rows = {
            row['d']: row
            for row in (
                orders.annotate(d=TruncDate('created_at'))
                .values('d')
                .annotate(
                    total=Sum('total_amount'),
                    count=Count('id'),
                )
            )
        }

        by_day = []
        current_day = start

        if (end - start).days <= 62:
            while current_day <= end:
                row = day_rows.get(current_day)

                by_day.append({
                    'date': current_day.isoformat(),
                    'total': float(row['total'] or 0) if row else 0,
                    'count': row['count'] if row else 0,
                })

                current_day += timedelta(days=1)
        else:
            by_day = [
                {
                    'date': key.isoformat(),
                    'total': float(value['total'] or 0),
                    'count': value['count'],
                }
                for key, value in sorted(day_rows.items())
            ]

        by_shop = (
            orders.values('shop__name')
            .annotate(
                total=Sum('total_amount'),
                count=Count('id'),
            )
            .order_by('-total')
        )

        by_product = (
            OrderItem.objects.filter(order__in=orders)
            .values(
                'product__name',
                'product__brand__name',
            )
            .annotate(
                qty=Sum(pieces('quantity')),
                free=Sum(pieces('free_quantity')),
                amount=Sum('line_total'),
            )
            .order_by('-amount')
        )

        return Response({
            'from': start.isoformat(),
            'to': end.isoformat(),
            'total': float(totals['total'] or 0),
            'count': totals['count'] or 0,
            'by_day': by_day,
            'by_shop': [
                {
                    'name': row['shop__name'],
                    'count': row['count'],
                    'total': float(row['total'] or 0),
                }
                for row in by_shop
            ],
            'by_product': [
                {
                    'name': row['product__name'],
                    'brand': row['product__brand__name'],
                    'qty': row['qty'] or 0,
                    'free': row['free'] or 0,
                    'amount': float(row['amount'] or 0),
                }
                for row in by_product
            ],
        })
