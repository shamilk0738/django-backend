from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from orders.models import Order

from .models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_name', 'phone', 'district', 'route',
                    'salesman', 'gst_number', 'is_active', 'view_orders')
    list_filter = ('district', 'route', 'salesman', 'is_active')
    search_fields = ('name', 'owner_name', 'phone', 'gst_number')
    list_editable = ('is_active',)
    fieldsets = (
        ('Shop details', {'fields': ('name', 'owner_name', 'phone', 'gst_number')}),
        ('Address', {'fields': ('address', 'district', 'pincode')}),
        ('Assignment', {'fields': ('route', 'salesman', 'user', 'is_active')}),
    )

    @admin.display(description='Orders')
    def view_orders(self, obj):
        url = reverse('admin:shops_shop_orders', args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#2f6bff;color:#fff;padding:6px 14px;'
            'border-radius:8px;text-decoration:none;font-weight:600;'
            'white-space:nowrap">View orders</a>', url)

    def get_urls(self):
        custom = [
            path('<int:shop_id>/orders/',
                 self.admin_site.admin_view(self.shop_orders_view),
                 name='shops_shop_orders'),
        ]
        return custom + super().get_urls()

    def shop_orders_view(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id)
        orders = (Order.objects.filter(shop=shop)
                  .select_related('salesman')
                  .prefetch_related('items__product')
                  .order_by('-created_at'))
        total = sum(o.total_amount for o in orders)
        context = {
            **self.admin_site.each_context(request),
            'title': f'{shop.name} - Orders',
            'shop': shop,
            'orders': orders,
            'grand_total': total,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/shops/shop_orders.html', context)