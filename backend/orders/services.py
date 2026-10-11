from decimal import Decimal

from django.db.models import Q

from catalog.models import Unit


def best_scheme(product, unit, quantity, on_date):
    qs = product.schemes.filter(is_active=True, unit=unit, min_quantity__lte=quantity)
    qs = qs.filter(Q(start_date__isnull=True) | Q(start_date__lte=on_date),
                   Q(end_date__isnull=True) | Q(end_date__gte=on_date))
    return qs.order_by('-min_quantity').first()


def calculate_line(product, unit, quantity, on_date):
    """returns (unit_price, free_quantity, discount_percent, line_total)"""
    rate = product.bag_rate if unit == Unit.BAG else product.price
    free = 0
    discount = Decimal('0')
    scheme = best_scheme(product, unit, quantity, on_date)
    if scheme:
        times = quantity // scheme.min_quantity
        free = times * scheme.free_quantity
        discount = scheme.discount_percent
    gross = rate * quantity
    total = (gross * (Decimal('100') - discount) / Decimal('100')).quantize(Decimal('0.01'))
    return rate, free, discount, total