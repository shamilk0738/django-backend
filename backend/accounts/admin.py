from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.utils.html import format_html

from .models import Attendance, Route, SalesmanProfile, User


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'role', 'phone')


class SalesmanProfileInline(admin.StackedInline):
    model = SalesmanProfile
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name_plural = 'Salesman details (role = Salesman ആണെങ്കിൽ മാത്രം പൂരിപ്പിക്കുക)'
    fields = ('employee_code', 'route', 'address', 'monthly_target',
              'photo', 'photo_preview')
    readonly_fields = ('photo_preview',)

    @admin.display(description='Preview')
    def photo_preview(self, obj):
        if obj and obj.photo:
            return format_html(
                '<img src="{}" style="height:90px;width:90px;'
                'object-fit:cover;border-radius:50%;" />', obj.photo.url)
        return '—'


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreateForm
    list_display = ('username', 'get_full_name', 'role', 'phone', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'phone')
    fieldsets = DjangoUserAdmin.fieldsets + (('Role & Contact', {'fields': ('role', 'phone')}),)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'role', 'phone',
                       'password1', 'password2'),
        }),
    )
    inlines = [SalesmanProfileInline]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('salesman', 'date', 'login_time')
    list_filter = ('date', 'salesman')
    date_hierarchy = 'date'