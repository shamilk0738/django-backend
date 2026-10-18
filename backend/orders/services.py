
from decimal import Decimal

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from catalog.models import Product, Unit


ENFORCE_STOCK = True


def _per_bag(product):
    return max(product.pieces_per_bag or 1, 1)


def best_scheme(product, unit, quantity, on_date):
    queryset = product.schemes.filter(
        is_active=True,
        unit=unit,
        min_quantity__lte=quantity,
    )
    queryset = queryset.filter(
        Q(start_date__isnull=True) | Q(start_date__lte=on_date),
        Q(end_date__isnull=True) | Q(end_date__gte=on_date),
    )
    return queryset.order_by('-min_quantity').first()


def calculate_line(product, unit, quantity, on_date):
    rate = product.bag_rate if unit == Unit.BAG else product.price
    free = 0
    discount = Decimal('0')

    scheme = best_scheme(product, unit, quantity, on_date)

    if scheme:
        times = quantity // scheme.min_quantity
        free = times * scheme.free_quantity
        discount = scheme.discount_percent

    gross = rate * quantity
    total = (
        gross * (Decimal('100') - discount) / Decimal('100')
    ).quantize(Decimal('0.01'))

    return rate, free, discount, total


def _to_pieces(product, unit, quantity, free_quantity=0):
    count = int(quantity) + int(free_quantity or 0)

    if unit == Unit.BAG:
        return count * _per_bag(product)

    return count


def take_stock(product, unit, quantity, free_quantity=0):
    locked = Product.objects.select_for_update().get(pk=product.pk)
    pieces = _to_pieces(locked, unit, quantity, free_quantity)

    if ENFORCE_STOCK and locked.stock < pieces:
        raise ValidationError({
            'items': [
                'Not enough stock for %s. Available: %s pcs, needed: %s pcs.'
                % (locked.name, locked.stock, pieces)
            ]
        })

    locked.stock -= pieces
    locked.save(update_fields=['stock'])


def give_back_stock(product, unit, quantity, free_quantity=0):
    locked = Product.objects.select_for_update().get(pk=product.pk)
    pieces = _to_pieces(locked, unit, quantity, free_quantity)

    locked.stock += pieces
    locked.save(update_fields=['stock'])
