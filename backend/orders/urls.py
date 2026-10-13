from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import OrderViewSet, SalesmanPerformanceView

router = SimpleRouter()
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('reports/salesman-performance/', SalesmanPerformanceView.as_view()),
] + router.urls
{
  "notes": "Deliver Monday",
  "items": [
    { "product": 1, "unit": "bag", "quantity": 30 },
    { "product": 2, "unit": "piece", "quantity": 12 }
  ]
}