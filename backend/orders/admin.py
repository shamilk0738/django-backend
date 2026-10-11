from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'unit', 'quantity', 'unit_price', 'free_quantity',
                       'discount_percent', 'line_total')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'salesman', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'salesman', 'created_at')
    search_fields = ('shop__name', 'salesman__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('shop', 'salesman', 'total_amount', 'created_at')
    inlines = [OrderItemInline]