"""
URL configuration for giffly_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from api.views import (
    UserViewSet, ProductViewSet, CartViewSet, OrderViewSet,
    FavoriteViewSet, SalesStatisticsViewSet, HealthCheckView,
    recommend_products
)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='users')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'favorites', FavoriteViewSet, basename='favorites')
router.register(r'statistics', SalesStatisticsViewSet, basename='statistics')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/token/', obtain_auth_token, name='api_token_auth'),
    path('api/recommend/', recommend_products, name='recommend-products'),
]
