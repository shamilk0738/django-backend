from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import LoginView
from config.dashboard import dashboard_data

admin.site.site_header = 'Distributor Admin'
admin.site.site_title = 'Distributor Admin'
admin.site.index_title = 'Dashboard'

# Admin home page-ൽ dashboard data ചേർക്കുന്നു
# (admin.site.urls ഉപയോഗിക്കുന്നതിന് മുൻപ് തന്നെ ഇത് വരണം)
_original_index = admin.site.index


def _dashboard_index(request, extra_context=None):
    extra_context = extra_context or {}
    extra_context['dash'] = dashboard_data()
    return _original_index(request, extra_context)


admin.site.index = _dashboard_index

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/')),
    path('admin/', admin.site.urls),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/', include('accounts.urls')),
    path('api/', include('shops.urls')),
    path('api/', include('catalog.urls')),
    path('api/', include('orders.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)