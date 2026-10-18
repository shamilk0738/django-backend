
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
    return Case(
        When(
            unit='bag',
            then=F(field) * F('product__pieces_per_bag'),
        ),
        default=F(field),
        output_field=IntegerField(),
    )


def valid_orders():
    return Order.objects.exclude(status=Order.Status.CANCELLED)


def chart_series(rows, label, value, limit=None):
    rows = list(rows)

    if limit:
        rows = rows[:limit]

    return {
        'labels': [str(row[label]) for row in rows],
        'values': [float(row[value] or 0) for row in rows],
    }


def summarize(orders):
    totals = orders.aggregate(
        total=Sum('total_amount'),
        count=Count('id'),
    )

    by_salesman = (
        orders.values('salesman__username')
        .annotate(
            total=Sum('total_amount'),
            count=Count('id'),
        )
        .order_by('-total')
    )

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
    except (TypeError, ValueError):
        day = timezone.localdate()

    orders = valid_orders().filter(created_at__date=day)
    context = summarize(orders)

    context['day'] = day
    context['is_today'] = day == timezone.localdate()

    context['status_counts'] = (
        Order.objects.filter(created_at__date=day)
        .values('status')
        .annotate(c=Count('id'))
    )

    context['orders'] = (
        Order.objects.filter(created_at__date=day)
        .select_related('shop', 'salesman')
    )

    status = list(context['status_counts'])

    context['charts'] = {
        'shop': chart_series(
            context['by_shop'],
            'shop__name',
            'total',
            8,
        ),
        'salesman': chart_series(
            context['by_salesman'],
            'salesman__username',
            'total',
            8,
        ),
        'product': chart_series(
            context['by_product'],
            'product__name',
            'amount',
            10,
        ),
        'status': {
            'labels': [item['status'].title() for item in status],
            'values': [item['c'] for item in status],
        },
    }

    context.update(admin.site.each_context(request))

    return render(
        request,
        'admin/reports/daily.html',
        context,
    )


@staff_member_required
def monthly_report(request):
    today = timezone.localdate()

    try:
        year, month = map(
            int,
            request.GET.get('month', '').split('-'),
        )
        date(year, month, 1)
    except (TypeError, ValueError):
        year, month = today.year, today.month

    orders = valid_orders().filter(
        created_at__year=year,
        created_at__month=month,
    )

    context = summarize(orders)
    context['month_value'] = f'{year}-{month:02d}'

    context['by_day'] = (
        orders.annotate(d=TruncDate('created_at'))
        .values('d')
        .annotate(
            total=Sum('total_amount'),
            count=Count('id'),
        )
        .order_by('d')
    )

    context['months'] = (
        valid_orders()
        .annotate(m=TruncMonth('created_at'))
        .values('m')
        .annotate(
            total=Sum('total_amount'),
            count=Count('id'),
        )
        .order_by('-m')
    )

    last12 = list(context['months'])[:12][::-1]

    context['charts'] = {
        'day': {
            'labels': [
                row['d'].strftime('%d %b')
                for row in context['by_day']
            ],
            'values': [
                float(row['total'] or 0)
                for row in context['by_day']
            ],
        },
        'months': {
            'labels': [
                row['m'].strftime('%b %Y')
                for row in last12
            ],
            'values': [
                float(row['total'] or 0)
                for row in last12
            ],
        },
        'salesman': chart_series(
            context['by_salesman'],
            'salesman__username',
            'total',
            8,
        ),
        'product': chart_series(
            context['by_product'],
            'product__name',
            'amount',
            10,
        ),
    }

    context.update(admin.site.each_context(request))

    return render(
        request,
        'admin/reports/monthly.html',
        context,
    )


@staff_member_required
def stock_report(request):
    products = Product.objects.select_related('brand').filter(
        is_active=True,
    )

    query = request.GET.get('q', '').strip()
    brand = request.GET.get('brand', '')
    low = request.GET.get('low', '')

    if query:
        products = products.filter(name__icontains=query)

    if brand:
        products = products.filter(brand_id=brand)

    if low.isdigit():
        products = products.filter(stock__lte=int(low))

    rows = []
    total_value = 0
    total_pieces = 0

    for product in products:
        per_bag = product.pieces_per_bag or 1
        value = product.stock * product.price

        total_value += value
        total_pieces += product.stock

        rows.append({
            'p': product,
            'bags': product.stock // per_bag,
            'loose': product.stock % per_bag,
            'value': value,
        })

    by_brand = {}

    for row in rows:
        name = row['p'].brand.name
        by_brand[name] = (
            by_brand.get(name, 0) + float(row['value'])
        )

    brand_top = sorted(
        by_brand.items(),
        key=lambda item: -item[1],
    )[:10]

    top = sorted(
        rows,
        key=lambda row: -row['value'],
    )[:10]

    context = {
        'rows': rows,
        'total_value': total_value,
        'total_pieces': total_pieces,
        'brands': Brand.objects.filter(is_active=True),
        'q': query,
        'brand': brand,
        'low': low,
        'charts': {
            'brand': {
                'labels': [name for name, _ in brand_top],
                'values': [value for _, value in brand_top],
            },
            'top': {
                'labels': [row['p'].name for row in top],
                'values': [
                    float(row['value'])
                    for row in top
                ],
            },
        },
    }

    context.update(admin.site.each_context(request))

    return render(
        request,
        'admin/reports/stock.html',
        context,
    )
