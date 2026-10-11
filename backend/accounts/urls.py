from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AttendanceViewSet, MeView

router = SimpleRouter()
router.register('attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [path('me/', MeView.as_view())] + router.urls