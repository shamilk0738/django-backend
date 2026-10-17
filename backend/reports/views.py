from datetime import date

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Case, Count, F, IntegerField, Sum, When
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from catalog.models import Brand, Product
from orders.models import Order, OrderItem


def pieces(field):
    """bag ആണെങ്കിൽ pieces_per_bag കൊണ്ട് ഗുണിച്ച് piece ആക്കും"""
    return Case(
        When(unit='bag', then=F(field) * F('product__pieces_per_bag')),
        default=F(field),
        output_field=IntegerField(),
    )


def valid_orders():
    return Order.objects.exclude(status=Order.Status.CANCELLED)


def chart_series(rows, label, value, limit=None):
    """queryset/list of dict -> {'labels': [...], 'values': [...]} (chart-നു വേണ്ടി)"""
    rows = list(rows)
    if limit:
        rows = rows[:limit]
    return {'labels': [str(r[label]) for r in rows],
            'values': [float(r[value] or 0) for r in rows]}


def summarize(orders):
    """ഒരു orders queryset-ന്റെ എല്ലാ breakdown-ഉം"""
    totals = orders.aggregate(total=Sum('total_amount'), count=Count('id'))
    by_salesman = (orders.values('salesman__username')
                   .annotate(total=Sum('total_amount'), count=Count('id'))
                   .order_by('-total'))
    by_shop = (orders.values('shop__name')
               .annotate(total=Sum('total_amount'), count=Count('id'))
               .order_by('-total'))
    by_product = (OrderItem.objects.filter(order__in=orders)
                  .values('product__name', 'product__brand__name')
                  .annotate(qty=Sum(pieces('quantity')),
                            free=Sum(pieces('free_quantity')),
                            amount=Sum('line_total'))
                  .order_by('-amount'))
    return {
        'total': totals['total'] or 0,
        'count': totals['count'] or 0,
        'by_salesman': by_salesman,
        'by_shop': by_shop,
        'by_product': by_product,
    }


@staff_member_required
def daily_report(request):
    try:
        day = date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        day = timezone.localdate()

    orders = valid_orders().filter(created_at__date=day)
    ctx = summarize(orders)
    ctx['day'] = day
    ctx['is_today'] = day == timezone.localdate()
    ctx['status_counts'] = (Order.objects.filter(created_at__date=day)
                            .values('status').annotate(c=Count('id')))
    ctx['orders'] = (Order.objects.filter(created_at__date=day)
                     .select_related('shop', 'salesman'))
    status = list(ctx['status_counts'])
    ctx['charts'] = {
        'shop': chart_series(ctx['by_shop'], 'shop__name', 'total', 8),
        'salesman': chart_series(ctx['by_salesman'], 'salesman__username', 'total', 8),
        'product': chart_series(ctx['by_product'], 'product__name', 'amount', 10),
        'status': {'labels': [s['status'].title() for s in status],
                   'values': [s['c'] for s in status]},
    }
    ctx.update(admin.site.each_context(request))   # sidebar
    return render(request, 'admin/reports/daily.html', ctx)


@staff_member_required
def monthly_report(request):
    today = timezone.localdate()
    try:
        year, month = map(int, request.GET.get('month', '').split('-'))
        date(year, month, 1)
    except ValueError:
        year, month = today.year, today.month

    orders = valid_orders().filter(created_at__year=year, created_at__month=month)
    ctx = summarize(orders)
    ctx['month_value'] = f'{year}-{month:02d}'
    ctx['by_day'] = (orders.annotate(d=TruncDate('created_at')).values('d')
                     .annotate(total=Sum('total_amount'), count=Count('id'))
                     .order_by('d'))
    # എല്ലാ മാസങ്ങളുടെയും summary
    ctx['months'] = (valid_orders().annotate(m=TruncMonth('created_at')).values('m')
                     .annotate(total=Sum('total_amount'), count=Count('id'))
                     .order_by('-m'))
    last12 = list(ctx['months'])[:12][::-1]          # പഴയത് → പുതിയത്
    ctx['charts'] = {
        'day': {'labels': [r['d'].strftime('%d %b') for r in ctx['by_day']],
                'values': [float(r['total'] or 0) for r in ctx['by_day']]},
        'months': {'labels': [r['m'].strftime('%b %Y') for r in last12],
                   'values': [float(r['total'] or 0) for r in last12]},
        'salesman': chart_series(ctx['by_salesman'], 'salesman__username', 'total', 8),
        'product': chart_series(ctx['by_product'], 'product__name', 'amount', 10),
    }
    ctx.update(admin.site.each_context(request))   # sidebar
    return render(request, 'admin/reports/monthly.html', ctx)


@staff_member_required
def stock_report(request):
    products = Product.objects.select_related('brand').filter(is_active=True)

    q = request.GET.get('q', '').strip()
    brand = request.GET.get('brand', '')
    low = request.GET.get('low', '')          # ഈ piece-ൽ താഴെ ഉള്ളത് മാത്രം

    if q:
        products = products.filter(name__icontains=q)
    if brand:
        products = products.filter(brand_id=brand)
    if low.isdigit():
        products = products.filter(stock__lte=int(low))

    rows, total_value, total_pieces = [], 0, 0
    for p in products:
        per_bag = p.pieces_per_bag or 1
        value = p.stock * p.price
        total_value += value
        total_pieces += p.stock
        rows.append({
            'p': p,
            'bags': p.stock // per_bag,
            'loose': p.stock % per_bag,
            'value': value,
        })

    by_brand = {}
    for r in rows:
        name = r['p'].brand.name
        by_brand[name] = by_brand.get(name, 0) + float(r['value'])
    brand_top = sorted(by_brand.items(), key=lambda x: -x[1])[:10]
    top = sorted(rows, key=lambda r: -r['value'])[:10]

    ctx = {
        'rows': rows, 'total_value': total_value, 'total_pieces': total_pieces,
        'brands': Brand.objects.filter(is_active=True),
        'q': q, 'brand': brand, 'low': low,
        'charts': {
            'brand': {'labels': [b for b, _ in brand_top],
                      'values': [v for _, v in brand_top]},
            'top': {'labels': [r['p'].name for r in top],
                    'values': [float(r['value']) for r in top]},
        },
    }
    ctx.update(admin.site.each_context(request))   # sidebar
    return render(request, 'admin/reports/stock.html', ctx)