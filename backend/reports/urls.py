from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('daily/', views.daily_report, name='daily'),
    path('monthly/', views.monthly_report, name='monthly'),
    path('stock/', views.stock_report, name='stock'),
]