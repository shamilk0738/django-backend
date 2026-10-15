from types import SimpleNamespace

from django.db import transaction
from rest_framework.exceptions import ValidationError

from catalog.models import Product
from orders import services
from orders.models import Order
from orders.serializers import OrderSerializer

print('services file:', services.__file__)
print('ENFORCE_STOCK =', services.ENFORCE_STOCK)
print('take_stock available:', hasattr(services, 'take_stock'))

ShopModel = Order._meta.get_field('shop').related_model
shop = ShopModel.objects.exclude(salesman__isnull=True).first()
product = Product.objects.filter(is_active=True, stock__gt=0).first()

if shop is None:
    print('No shop has a salesman assigned. Assign a salesman to a shop in admin.')
elif product is None:
    print('No product has stock. Set Stock on a product in admin.')
else:
    print('Shop:', shop.name, ' Salesman:', shop.salesman)
    print('Product:', product.name, ' stock =', product.stock,
          'pcs  pieces/bag =', product.pieces_per_bag)
    print('-' * 60)

    with transaction.atomic():
        for unit in ('piece', 'bag'):
            before = Product.objects.get(pk=product.pk).stock
            serializer = OrderSerializer(
                data={
                    'shop': shop.pk,
                    'items': [{'product': product.pk, 'unit': unit, 'quantity': 1}],
                },
                context={'request': SimpleNamespace(user=shop.salesman)},
            )
            try:
                serializer.is_valid(raise_exception=True)
                order = serializer.save()
            except ValidationError as e:
                print('[%s] order rejected: %s' % (unit, e.detail))
                continue

            after = Product.objects.get(pk=product.pk).stock
            per_bag = max(product.pieces_per_bag or 1, 1)
            expected = per_bag if unit == 'bag' else 1
            verdict = 'OK' if before - after >= expected else 'NOT REDUCED  <-- problem'
            print('[%s] stock %s -> %s (should drop by >= %s)  %s'
                  % (unit, before, after, expected, verdict))

        transaction.set_rollback(True)   # undo all test data

    print('-' * 60)
    print('Test orders rolled back. Your data is unchanged.')