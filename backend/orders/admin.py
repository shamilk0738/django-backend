from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .models import Order

# Hides the "Bill" label and stretches the bill across the full page width
BILL_CSS = mark_safe(
    '<style>'
    '.field-bill_details label{display:none !important}'
    '.field-bill_details .readonly{margin-left:0 !important;'
    'width:100% !important;display:block}'
    '.field-bill_details{padding:0 !important}'
    '</style>'
)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'salesman',
                    'total_amount', 'status', 'created_at')
    list_display_links = ('id', 'shop')
    list_filter = ('status', 'salesman', 'created_at')
    search_fields = ('id', 'shop__name', 'salesman__username',
                     'items__product__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('shop', 'salesman', 'total_amount', 'created_at',
                       'bill_details')

    fieldsets = (
        (None, {
            'fields': ('shop', 'salesman', 'status', 'notes',
                       'total_amount', 'created_at'),
        }),
        ('Bill', {
            'classes': ('wide',),
            'fields': ('bill_details',),
        }),
    )

    actions = ['mark_confirmed', 'mark_delivered', 'undo_status']

    def get_queryset(self, request):
        return (super().get_queryset(request)
                .select_related('shop', 'salesman')
                .prefetch_related('items__product'))

    @admin.display(description='Bill')
    def bill_details(self, obj):
        if not obj.pk:
            return '-'

        rows = format_html_join(
            '',
            '<tr style="border-bottom:1px solid #eee">'
            '<td style="padding:14px 16px">{}</td>'
            '<td style="padding:14px 16px;text-align:center">{} {}</td>'
            '<td style="padding:14px 16px;text-align:right">{}</td>'
            '<td style="padding:14px 16px;text-align:right">{}</td>'
            '</tr>',
            ((i.product.name, i.quantity, i.unit, i.unit_price, i.line_total)
             for i in obj.items.all()),
        )

        return format_html(
            '{}'
            '<div style="width:100%;background:#fff;border:1px solid #ddd;'
            'border-radius:8px;padding:24px;box-sizing:border-box">'
            '<div style="display:flex;justify-content:space-between;'
            'margin-bottom:20px;font-size:15px">'
            '<div><b style="font-size:20px">{}</b><br>Salesman: {}</div>'
            '<div style="text-align:right">Order #{}<br>{}</div>'
            '</div>'
            '<table style="width:100%;border-collapse:collapse;font-size:16px">'
            '<thead><tr style="background:#f4f6fb;text-align:left;'
            'border-bottom:2px solid #ddd">'
            '<th style="padding:14px 16px">DESCRIPTION</th>'
            '<th style="padding:14px 16px;text-align:center">QTY</th>'
            '<th style="padding:14px 16px;text-align:right">COST PRICE</th>'
            '<th style="padding:14px 16px;text-align:right">AMOUNT</th>'
            '</tr></thead><tbody>{}</tbody></table>'
            '<p style="text-align:right;font-size:22px;margin:20px 16px 0 0">'
            '<b>Total: {}</b></p>'
            '</div>',
            BILL_CSS,
            obj.shop, obj.salesman, obj.pk,
            obj.created_at.strftime('%d %b %Y, %I:%M %p'),
            rows, obj.total_amount,
        )

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
        # Order matters: first confirmed→pending, then delivered→confirmed
        a = queryset.filter(status='confirmed').update(status='pending')
        b = queryset.filter(status='delivered').update(status='confirmed')
        self.message_user(request, f'{a + b} order(s) moved back one step.',
                          messages.WARNING)