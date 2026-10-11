from django.contrib import admin

from .models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_name', 'phone', 'district', 'route', 'salesman', 'gst_number', 'is_active')
    list_filter = ('district', 'route', 'salesman', 'is_active')
    search_fields = ('name', 'owner_name', 'phone', 'gst_number')
    list_editable = ('is_active',)
    fieldsets = (
        ('Shop details', {'fields': ('name', 'owner_name', 'phone', 'gst_number')}),
        ('Address', {'fields': ('address', 'district', 'pincode')}),
        ('Assignment', {'fields': ('route', 'salesman', 'user', 'is_active')}),
    )