# reports/api.py  (പുതിയ ഫയൽ)
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
    """Login ചെയ്ത salesman-ന്റെ സ്വന്തം sales report (JSON)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        start = _parse(request.query_params.get('from'), today.replace(day=1))
        end = _parse(request.query_params.get('to'), today)
        if start > end:
            start, end = end, start

        orders = valid_orders().filter(
            salesman=request.user,
            created_at__date__range=(start, end),
        )

        totals = orders.aggregate(total=Sum('total_amount'), count=Count('id'))

        day_rows = {
            r['d']: r for r in orders.annotate(d=TruncDate('created_at'))
            .values('d').annotate(total=Sum('total_amount'), count=Count('id'))
        }
        by_day, d = [], start
        while d <= end and (end - start).days <= 62:   # ചാർട്ടിൽ order ഇല്ലാത്ത ദിവസവും 0 ആയി
            r = day_rows.get(d)
            by_day.append({
                'date': d.isoformat(),
                'total': float(r['total'] or 0) if r else 0,
                'count': r['count'] if r else 0,
            })
            d += timedelta(days=1)
        if (end - start).days > 62:
            by_day = [{'date': k.isoformat(), 'total': float(v['total'] or 0),
                       'count': v['count']} for k, v in sorted(day_rows.items())]

        by_shop = (orders.values('shop__name')
                   .annotate(total=Sum('total_amount'), count=Count('id'))
                   .order_by('-total'))
        by_product = (OrderItem.objects.filter(order__in=orders)
                      .values('product__name', 'product__brand__name')
                      .annotate(qty=Sum(pieces('quantity')),
                                free=Sum(pieces('free_quantity')),
                                amount=Sum('line_total'))
                      .order_by('-amount'))

        return Response({
            'from': start.isoformat(),
            'to': end.isoformat(),
            'total': float(totals['total'] or 0),
            'count': totals['count'] or 0,
            'by_day': by_day,
            'by_shop': [{'name': r['shop__name'], 'count': r['count'],
                         'total': float(r['total'] or 0)} for r in by_shop],
            'by_product': [{'name': r['product__name'],
                            'brand': r['product__brand__name'],
                            'qty': r['qty'] or 0, 'free': r['free'] or 0,
                            'amount': float(r['amount'] or 0)} for r in by_product],
        })