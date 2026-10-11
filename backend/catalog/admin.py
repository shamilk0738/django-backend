from django.contrib import admin

from .models import Brand, Product, Scheme


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1
    fields = ('name', 'price', 'pieces_per_bag', 'bag_price', 'is_active')
    show_change_link = True      # scheme ചേർക്കാൻ product page തുറക്കാം


class SchemeInline(admin.TabularInline):
    model = Scheme
    extra = 1


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'is_active')
    search_fields = ('name',)
    inlines = [ProductInline]

    @admin.display(description='Products')
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'price', 'pieces_per_bag', 'bag_rate', 'is_active')
    list_filter = ('brand', 'is_active')
    search_fields = ('name', 'brand__name')
    list_editable = ('is_active',)
    inlines = [SchemeInline]