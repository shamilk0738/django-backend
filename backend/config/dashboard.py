"""Dashboard numbers for the custom admin home page."""
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import Attendance, SalesmanProfile, User
from orders.models import Order, OrderItem
from shops.models import Shop


def inr(value):
    """Indian number format: 1234567 -> 12,34,567"""
    value = int(round(float(value or 0)))
    sign = '-' if value < 0 else ''
    s = str(abs(value))
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ','.join(parts + [tail])


def _name(first, last, username):
    return (f'{first} {last}'.strip()) or username


def dashboard_data():
    today = timezone.localdate()
    month_start = today.replace(day=1)
    valid = Order.objects.exclude(status=Order.Status.CANCELLED)

    # ---- today -------------------------------------------------------
    today_agg = valid.filter(created_at__date=today).aggregate(
        total=Sum('total_amount'), cnt=Count('id'))

    # ---- this month --------------------------------------------------
    month_qs = valid.filter(created_at__date__gte=month_start)
    month_agg = month_qs.aggregate(total=Sum('total_amount'), cnt=Count('id'))
    month_sales = month_agg['total'] or 0

    # same number of days of last month, for the growth badge
    prev_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_end = min(prev_start + timedelta(days=today.day - 1),
                   month_start - timedelta(days=1))
    prev_sales = valid.filter(
        created_at__date__range=(prev_start, prev_end)
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    growth = None
    if prev_sales:
        growth = round((float(month_sales) - float(prev_sales)) / float(prev_sales) * 100, 1)

    # ---- targets -----------------------------------------------------
    targets = dict(SalesmanProfile.objects.filter(user__is_active=True)
                   .values_list('user_id', 'monthly_target'))
    target_total = sum(float(t) for t in targets.values())
    target_pct = min(int(float(month_sales) / target_total * 100), 100) if target_total else 0

    # ---- people ------------------------------------------------------
    salesmen_count = User.objects.filter(role=User.Role.SALESMAN, is_active=True).count()
    present = Attendance.objects.filter(date=today).count()
    present_pct = min(int(present / salesmen_count * 100), 100) if salesmen_count else 0

    # ---- chart: last 30 days ----------------------------------------
    start = today - timedelta(days=29)
    rows = (valid.filter(created_at__date__gte=start)
            .annotate(d=TruncDate('created_at'))
            .values('d').annotate(total=Sum('total_amount')).order_by('d'))
    by_day = {r['d']: float(r['total'] or 0) for r in rows}
    labels, values = [], []
    for i in range(30):
        day = start + timedelta(days=i)
        labels.append(day.strftime('%d %b'))
        values.append(by_day.get(day, 0))

    # ---- top salesmen (this month) ----------------------------------
    top_rows = (month_qs.values('salesman', 'salesman__first_name',
                                'salesman__last_name', 'salesman__username')
                .annotate(total=Sum('total_amount'), cnt=Count('id'))
                .order_by('-total')[:5])
    top_max = max([float(r['total'] or 0) for r in top_rows], default=0)
    top_salesmen = []
    for r in top_rows:
        total = float(r['total'] or 0)
        target = float(targets.get(r['salesman'], 0) or 0)
        t_pct = round(total / target * 100) if target else None
        name = _name(r['salesman__first_name'], r['salesman__last_name'],
                     r['salesman__username'])
        top_salesmen.append({
            'name': name,
            'initial': name[:1].upper(),
            'total': inr(total),
            'orders': r['cnt'],
            'target_pct': t_pct,
            'bar': min(t_pct, 100) if t_pct is not None
            else (int(total / top_max * 100) if top_max else 0),
        })

    # ---- popular products (this month) ------------------------------
    prod_rows = (OrderItem.objects
                 .exclude(order__status=Order.Status.CANCELLED)
                 .filter(order__created_at__date__gte=month_start)
                 .values('product__name', 'product__brand__name')
                 .annotate(qty=Sum('quantity'), amount=Sum('line_total'))
                 .order_by('-amount')[:5])
    popular = [{
        'name': r['product__name'],
        'brand': r['product__brand__name'],
        'qty': r['qty'],
        'amount': inr(r['amount']),
    } for r in prod_rows]

    # ---- recent orders / attendance ---------------------------------
    recent_orders = list(Order.objects.select_related('shop', 'salesman')
                         .order_by('-created_at')[:8])
    for o in recent_orders:
        o.amount_display = inr(o.total_amount)
        o.salesman_display = o.salesman.get_full_name() or o.salesman.username

    attendance_today = []
    for a in Attendance.objects.filter(date=today).select_related('salesman'):
        name = a.salesman.get_full_name() or a.salesman.username
        attendance_today.append({
            'name': name, 'initial': name[:1].upper(), 'time': a.login_time,
        })

    return {
        'today': today,
        'today_sales': inr(today_agg['total']),
        'today_orders': today_agg['cnt'] or 0,
        'month_sales': inr(month_sales),
        'month_orders': month_agg['cnt'] or 0,
        'growth': growth,
        'target_total': inr(target_total),
        'target_pct': target_pct,
        'pending': Order.objects.filter(status=Order.Status.PENDING).count(),
        'salesmen': salesmen_count,
        'present': present,
        'present_pct': present_pct,
        'active_shops': Shop.objects.filter(is_active=True).count(),
        'chart': {'labels': labels, 'values': values},
        'top_salesmen': top_salesmen,
        'popular': popular,
        'recent_orders': recent_orders,
        'attendance_today': attendance_today,
    }