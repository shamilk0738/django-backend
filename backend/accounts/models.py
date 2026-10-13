from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        SALESMAN = 'salesman', 'Salesman'
        SHOP = 'shop', 'Shop'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    phone = models.CharField(max_length=15, blank=True)

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


class Route(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SalesmanProfile(models.Model):
    photo = models.ImageField(upload_to='salesman_photos/', blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='salesman_profile')
    employee_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='salesmen', verbose_name='Supply route')
    address = models.TextField(blank=True)
    monthly_target = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                         help_text='Monthly sales target (Rs)')

    def __str__(self):
        return f'Profile: {self.user}'


class Attendance(models.Model):
    salesman = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    login_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('salesman', 'date')
        ordering = ['-date', '-login_time']

    def __str__(self):
        return f'{self.salesman} - {self.date}'
        