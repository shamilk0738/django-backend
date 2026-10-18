from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Attendance, User


class LoginSerializer(TokenObtainPairSerializer):
    """Login only. Attendance is NOT marked here; it is marked when an order is created."""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'name': user.get_full_name() or user.username,
            'role': 'admin' if user.is_admin_role else user.role,
        }
        return data


class AttendanceSerializer(serializers.ModelSerializer):
    salesman_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'salesman', 'salesman_name', 'date', 'login_time']

    def get_salesman_name(self, obj):
        return obj.salesman.get_full_name() or obj.salesman.username