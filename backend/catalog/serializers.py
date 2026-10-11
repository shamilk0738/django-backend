from rest_framework import serializers

from .models import Brand, Product, Scheme


class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = ['id', 'unit', 'min_quantity', 'free_quantity', 'discount_percent',
                  'description', 'start_date', 'end_date']


class ProductSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    bag_rate = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    schemes = SchemeSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'brand', 'brand_name', 'name', 'description', 'image', 'price',
                  'pieces_per_bag', 'bag_rate', 'schemes']


class BrandListSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo', 'product_count']

    def get_product_count(self, obj):
        return len(obj.products.all())


class BrandDetailSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo', 'products']