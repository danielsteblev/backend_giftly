from rest_framework import viewsets
from .models import User, Product, Cart, Order, Favorite, SalesStatistics
from .serializers import UserSerializer, ProductSerializer, CartSerializer, OrderSerializer, FavoriteSerializer, SalesStatisticsSerializer
from .permissions import IsSellerOrAdmin, IsOwner
from rest_framework.permissions import IsAuthenticated

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdmin]

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdmin]

    def get_queryset(self):
        if self.request.user.role == 'seller':
            return Product.objects.filter(seller=self.request.user)
        return Product.objects.all()

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'seller':
            return Order.objects.filter(products__seller=self.request.user).distinct()
        return Order.objects.filter(user=self.request.user)

class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

class SalesStatisticsViewSet(viewsets.ModelViewSet):
    serializer_class = SalesStatisticsSerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdmin]

    def get_queryset(self):
        if self.request.user.role == 'seller':
            return SalesStatistics.objects.filter(seller=self.request.user)
        return SalesStatistics.objects.all()