from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from catalog.models import Product

from .models import Order, OrderItem
from .services import calculate_line


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'unit', 'quantity',
                  'unit_price', 'free_quantity', 'discount_percent', 'line_total']
        read_only_fields = ['unit_price', 'free_quantity', 'discount_percent', 'line_total']

    def validate_product(self, product):
        if not product.is_active:
            raise serializers.ValidationError('This product is not available.')
        return product


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    salesman_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'shop', 'shop_name', 'salesman', 'salesman_name', 'status',
                  'notes', 'total_amount', 'created_at', 'items']
        read_only_fields = ['salesman', 'status', 'total_amount', 'created_at']

    def get_salesman_name(self, obj):
        return obj.salesman.get_full_name() or obj.salesman.username

    def validate_shop(self, shop):
        user = self.context['request'].user
        if shop.salesman_id != user.id:
            raise serializers.ValidationError('This shop is not assigned to you.')
        return shop

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('Add at least one item.')
        return items

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        salesman = self.context['request'].user
        today = timezone.localdate()
        with transaction.atomic():
            order = Order.objects.create(salesman=salesman, **validated_data)
            total = Decimal('0.00')
            for item in items_data:
                rate, free, disc, line_total = calculate_line(
                    item['product'], item['unit'], item['quantity'], today
                )
                OrderItem.objects.create(
                    order=order, product=item['product'], unit=item['unit'],
                    quantity=item['quantity'], unit_price=rate, free_quantity=free,
                    discount_percent=disc, line_total=line_total,
                )
                total += line_total
            order.total_amount = total
            order.save(update_fields=['total_amount'])
        return order


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'status']


# ---------- Order edit ----------

class EditItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True))
    unit = serializers.ChoiceField(choices=['bag', 'piece'])
    quantity = serializers.IntegerField(min_value=1)


class OrderEditSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
    items = EditItemSerializer(many=True, allow_empty=False)

    def update(self, order, validated_data):
        today = timezone.localdate()
        with transaction.atomic():
            if 'notes' in validated_data:
                order.notes = validated_data['notes']

            order.items.all().delete()
            total = Decimal('0.00')
            for item in validated_data['items']:
                rate, free, disc, line_total = calculate_line(
                    item['product'], item['unit'], item['quantity'], today
                )
                OrderItem.objects.create(
                    order=order, product=item['product'], unit=item['unit'],
                    quantity=item['quantity'], unit_price=rate, free_quantity=free,
                    discount_percent=disc, line_total=line_total,
                )
                total += line_total

            order.total_amount = total
            order.save()
        return order