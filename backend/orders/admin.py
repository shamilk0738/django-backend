from django.contrib import admin, messages

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('product', 'unit', 'quantity', 'free_quantity',
              'unit_price', 'discount_percent', 'line_total')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'salesman', 'products_summary',
                    'total_amount', 'status', 'created_at')
    list_filter = ('status', 'salesman', 'created_at')
    search_fields = ('id', 'shop__name', 'salesman__username',
                     'items__product__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('shop', 'salesman', 'total_amount', 'created_at')
    inlines = [OrderItemInline]
    actions = ['mark_confirmed', 'mark_delivered', 'undo_status']

    def get_queryset(self, request):
        return (super().get_queryset(request)
                .select_related('shop', 'salesman')
                .prefetch_related('items__product'))

    @admin.display(description='Products')
    def products_summary(self, obj):
        parts = [f'{i.product.name} × {i.quantity} {i.unit}'
                 for i in obj.items.all()]
        return ', '.join(parts) or '—'

    @admin.action(description='Mark selected as CONFIRMED')
    def mark_confirmed(self, request, queryset):
        n = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'{n} order(s) confirmed.', messages.SUCCESS)

    @admin.action(description='Mark selected as DELIVERED')
    def mark_delivered(self, request, queryset):
        n = queryset.filter(status__in=['pending', 'confirmed']) \
                    .update(status='delivered')
        self.message_user(request, f'{n} order(s) delivered.', messages.SUCCESS)

    @admin.action(description='UNDO last status (Delivered > Confirmed > Pending)')
    def undo_status(self, request, queryset):
        # ക്രമം പ്രധാനം: ആദ്യം confirmed→pending, പിന്നെ delivered→confirmed
        a = queryset.filter(status='confirmed').update(status='pending')
        b = queryset.filter(status='delivered').update(status='confirmed')
        self.message_user(request, f'{a + b} order(s) moved back one step.',
                          messages.WARNING)