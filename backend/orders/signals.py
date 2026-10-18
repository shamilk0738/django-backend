from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import Attendance, User
from .models import Order


@receiver(post_save, sender=Order)
def mark_attendance_on_order(sender, instance, created, **kwargs):
    if not created:
        return

    salesman = instance.salesman
    if salesman.role != User.Role.SALESMAN:
        return

    
    Attendance.objects.get_or_create(
        salesman=salesman,
        date=timezone.localdate(),
    )