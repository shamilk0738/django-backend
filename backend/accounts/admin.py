from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Max
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .models import Attendance, Route, SalesmanProfile, User


def build_history(salesman):
    """Last 60 days: Present with time, Absent, or Not yet (today)."""
    today = timezone.localdate()
    joined = timezone.localtime(salesman.date_joined).date()
    start = max(today - timedelta(days=59), joined)

    records = {
        a.date: a
        for a in Attendance.objects.filter(salesman=salesman, date__gte=start)
    }

    rows = []
    present = 0
    absent = 0
    day = today
    while day >= start:
        rec = records.get(day)
        if rec:
            present += 1
            status = mark_safe('<b style="color:#16a34a">✔ Present</b>')
            time_txt = timezone.localtime(rec.login_time).strftime('%I:%M %p')
        elif day == today:
            status = mark_safe('<b style="color:#6b7280">Not yet</b>')
            time_txt = '—'
        else:
            absent += 1
            status = mark_safe('<b style="color:#dc2626">✘ Absent</b>')
            time_txt = '—'
        rows.append((day.strftime('%d %b %Y'), day.strftime('%A'), status, time_txt))
        day -= timedelta(days=1)

    body = format_html_join(
        '',
        '<tr><td style="padding:6px 14px">{}</td>'
        '<td style="padding:6px 14px">{}</td>'
        '<td style="padding:6px 14px">{}</td>'
        '<td style="padding:6px 14px">{}</td></tr>',
        rows,
    )
    return format_html(
        '<button type="button" class="button" '
        'onclick="document.getElementById(\'att-wrap\').requestFullscreen()">'
        '⛶ Full screen</button>'
        '<div id="att-wrap" style="width:100%;box-sizing:border-box;'
        'padding:12px;overflow:auto;background:#fff;color:#000">'
        '<p><b>Present: {}</b> &nbsp;|&nbsp; <b>Absent: {}</b> '
        '&nbsp;(last 60 days)</p>'
        '<table style="width:100%"><thead><tr>'
        '<th style="padding:6px 14px">Date</th>'
        '<th style="padding:6px 14px">Day</th>'
        '<th style="padding:6px 14px">Status</th>'
        '<th style="padding:6px 14px">Time</th>'
        '</tr></thead><tbody>{}</tbody></table></div>',
        present, absent, body,
    )


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'role', 'phone')


class SalesmanProfileInline(admin.StackedInline):
    model = SalesmanProfile
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name_plural = 'Salesman details (fill only if role = Salesman)'
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
    readonly_fields = ('attendance_history',)
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Role & Contact', {'fields': ('role', 'phone')}),
        ('Attendance History', {'fields': ('attendance_history',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'role', 'phone',
                       'password1', 'password2'),
        }),
    )
    inlines = [SalesmanProfileInline]

    @admin.display(description='Last 60 days')
    def attendance_history(self, obj):
        if not obj or not obj.pk or obj.role != User.Role.SALESMAN:
            return '—'
        return build_history(obj)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('salesman_link', 'date', 'login_time')
    list_display_links = ('salesman_link',)
    list_filter = ('date', 'salesman')
    date_hierarchy = 'date'

    # These GET params mean the admin picked a date or salesman filter.
    FILTER_KEYS = ('date__year', 'date__month', 'date__day',
                   'date__gte', 'date__lt', 'date__range__gte',
                   'salesman__id__exact')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        match = getattr(request, 'resolver_match', None)
        is_list = bool(match) and match.url_name == 'accounts_attendance_changelist'
        if not is_list:
            return qs
        if any(k in request.GET for k in self.FILTER_KEYS):
            return qs  # filtered: show every matching record
        # Default list: one row per salesman (their latest record)
        latest_ids = list(
            Attendance.objects.values('salesman_id')
            .annotate(last_id=Max('id'))
            .values_list('last_id', flat=True)
        )
        return qs.filter(id__in=latest_ids)

    @admin.display(description='Salesman', ordering='salesman__first_name')
    def salesman_link(self, obj):
        return str(obj.salesman)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is None:
            return super().change_view(request, object_id, form_url, extra_context)

        context = {
            **self.admin_site.each_context(request),
            'title': f'Attendance history: {obj.salesman}',
            'opts': self.model._meta,
            'table': build_history(obj.salesman),
            'back_url': reverse('admin:accounts_attendance_changelist'),
        }
        return TemplateResponse(request, 'admin/attendance_history.html', context)

    def has_add_permission(self, request):
        return False