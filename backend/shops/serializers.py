from rest_framework import serializers

from .models import Shop


class ShopSerializer(serializers.ModelSerializer):
    salesman_name = serializers.SerializerMethodField()
    route_name = serializers.CharField(source='route.name', read_only=True, default=None)

    class Meta:
        model = Shop
        fields = ['id', 'name', 'owner_name', 'phone', 'gst_number', 'address',
                  'district', 'pincode', 'route', 'route_name', 'salesman',
                  'salesman_name', 'is_active']

    def get_salesman_name(self, obj):
        return (obj.salesman.get_full_name() or obj.salesman.username) if obj.salesman else None