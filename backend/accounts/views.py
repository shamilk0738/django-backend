from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Attendance
from .serializers import AttendanceSerializer, LoginSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = []


class MeView(APIView):
    def get(self, request):
        u = request.user
        profile = getattr(u, 'salesman_profile', None)
        return Response({
            'id': u.id,
            'username': u.username,
            'name': u.get_full_name() or u.username,
            'role': 'admin' if u.is_admin_role else u.role,
            'phone': u.phone,
            'route': profile.route.name if profile and profile.route else None,
        })


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        qs = Attendance.objects.select_related('salesman')
        user = self.request.user
        if not user.is_admin_role:
            qs = qs.filter(salesman=user)
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(date=date)
        return qs