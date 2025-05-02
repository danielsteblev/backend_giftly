from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProductViewSet, CartViewSet, OrderViewSet, FavoriteViewSet, SalesStatisticsViewSet

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='users')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'favorites', FavoriteViewSet, basename='favorites')
router.register(r'statistics', SalesStatisticsViewSet, basename='statistics')

urlpatterns = [
    path('', include(router.urls)),
]