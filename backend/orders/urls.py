from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import OrderViewSet, SalesmanPerformanceView

router = SimpleRouter()
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('reports/salesman-performance/', SalesmanPerformanceView.as_view()),
] + router.urls