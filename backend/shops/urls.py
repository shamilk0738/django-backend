from rest_framework.routers import SimpleRouter

from .views import ShopViewSet

router = SimpleRouter()
router.register('shops', ShopViewSet, basename='shop')

urlpatterns = router.urls