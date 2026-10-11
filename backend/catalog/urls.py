from rest_framework.routers import SimpleRouter

from .views import BrandViewSet, ProductViewSet

router = SimpleRouter()
router.register('brands', BrandViewSet, basename='brand')
router.register('products', ProductViewSet, basename='product')

urlpatterns = router.urls