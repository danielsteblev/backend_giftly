from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Product, Cart, Order, Favorite, SalesStatistics, CartItem
from .serializers import (
    UserSerializer, ProductSerializer, CartSerializer, OrderSerializer,
    FavoriteSerializer, SalesStatisticsSerializer, UserRegistrationSerializer
)
from .permissions import IsSellerOrAdmin, IsOwner
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.conf import settings
from .gift_service import GiftRecommendationService

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({"status": "healthy"}, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegistrationSerializer
        return UserSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        try:
            print("Debug: Начало регистрации")
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                print("Debug: Данные валидны")
                user = serializer.save()
                print(f"Debug: Пользователь создан с ID: {user.id}")
                
                # Создаем токен напрямую через Token.objects.create
                token = Token.objects.create(user=user)
                print(f"Debug: Токен создан: {token.key}")
                
                return Response({
                    'user': UserSerializer(user, context=self.get_serializer_context()).data,
                    'token': token.key,
                    'message': 'Пользователь успешно зарегистрирован'
                }, status=status.HTTP_201_CREATED)
                
            print(f"Debug: Ошибки валидации: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Debug: Ошибка при регистрации: {str(e)}")
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при регистрации пользователя'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email и пароль обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            if not user.check_password(password):
                return Response(
                    {'error': 'Неверный email или пароль'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Проверяем, существует ли пользователь в auth_user
            if not user.id:
                return Response(
                    {'error': 'Ошибка аутентификации: пользователь не найден в системе'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Создаем или получаем существующий токен
            token, _ = Token.objects.get_or_create(user=user)
            
            serializer = UserSerializer(user)
            return Response({
                'user': serializer.data,
                'token': token.key
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_update(self, serializer):
        serializer.save()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'toggle_favorite']:
            return [IsAuthenticated(), IsSellerOrAdmin()]
        return [AllowAny()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self.request, 'user'):
            context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Требуется авторизация'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        product = self.get_object()
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
        
        if not created:
            favorite.delete()
            return Response({'status': 'removed from favorites'})
        
        return Response({'status': 'added to favorites'})

    def create(self, request, *args, **kwargs):
        try:
            # Проверяем обязательные поля
            required_fields = ['name', 'price']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        {'error': f'Поле {field} обязательно для заполнения'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Проверяем, что цена положительная
            try:
                price = float(request.data.get('price', 0))
                if price <= 0:
                    return Response(
                        {'error': 'Цена должна быть положительным числом'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Некорректное значение цены'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создаем товар
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            return Response({
                'message': 'Товар успешно создан',
                'product': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при создании товара'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        recent_products = Product.objects.order_by('-created_at')[:5]
        serializer = self.get_serializer(recent_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def recommend(self, request):
        """
        Получает рекомендации подарков с помощью DeepSeek API
        """
        try:
            query = request.data.get('query')
            if not query:
                return Response(
                    {'error': 'Поле query обязательно для заполнения'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получаем рекомендации
            service = GiftRecommendationService()
            result = service.get_recommendations(query)

            if not result['success']:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_or_create_cart(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))

            if not product_id:
                return Response(
                    {'error': 'ID товара обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if quantity <= 0:
                return Response(
                    {'error': 'Количество должно быть положительным числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Товар не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Проверяем, не пытается ли продавец добавить свой товар
            if product.seller == request.user:
                return Response(
                    {'error': 'Продавец не может добавить свой товар в корзину'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart = self.get_or_create_cart()
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            serializer = self.get_serializer(cart)
            return Response({
                'message': 'Товар успешно добавлен в корзину',
                'cart': serializer.data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'error': 'Некорректное значение количества',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при добавлении товара в корзину'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        try:
            product_id = request.data.get('product_id')

            if not product_id:
                return Response(
                    {'error': 'ID товара обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Товар не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            cart = self.get_or_create_cart()
            # Удаляем все записи для данного товара
            CartItem.objects.filter(cart=cart, product=product).delete()

            serializer = self.get_serializer(cart)
            return Response({
                'message': 'Товар успешно удален из корзины',
                'cart': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при удалении товара из корзины'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def get_cart(self, request):
        try:
            cart = self.get_or_create_cart()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при получении корзины'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def clear_cart(self, request):
        try:
            cart = self.get_or_create_cart()
            CartItem.objects.filter(cart=cart).delete()
            return Response({
                'message': 'Корзина успешно очищена'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при очистке корзины'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))

            if not product_id:
                return Response(
                    {'error': 'ID товара обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if quantity <= 0:
                return Response(
                    {'error': 'Количество должно быть положительным числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                cart = Cart.objects.get(user=self.request.user)
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            except (Cart.DoesNotExist, CartItem.DoesNotExist):
                return Response(
                    {'error': 'Товар не найден в корзине'},
                    status=status.HTTP_404_NOT_FOUND
                )

            cart_item.quantity = quantity
            cart_item.save()

            serializer = self.get_serializer(cart)
            return Response({
                'message': 'Количество товара успешно обновлено',
                'cart': serializer.data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'error': 'Некорректное значение количества',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при обновлении количества товара'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'seller':
            # Получаем все заказы, где есть товары текущего продавца
            return Order.objects.filter(
                products__seller=self.request.user
            ).distinct()
        return Order.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def seller_orders(self, request):
        if request.user.role != 'seller':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем все заказы, где есть товары текущего продавца
        orders = Order.objects.filter(
            products__seller=request.user
        ).distinct()
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        try:
            # Получаем корзину пользователя
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверяем, есть ли товары в корзине
            cart_items = CartItem.objects.filter(cart=cart)
            if not cart_items.exists():
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Рассчитываем общую сумму заказа
            total_amount = sum(item.product.price * item.quantity for item in cart_items)

            # Создаем заказ
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                status='pending'
            )

            # Добавляем товары в заказ
            for item in cart_items:
                order.products.add(item.product)

            # Очищаем корзину
            cart_items.delete()

            # Сериализуем и возвращаем созданный заказ
            serializer = self.get_serializer(order)
            return Response({
                'message': 'Заказ успешно создан',
                'order': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при создании заказа'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        try:
            # Получаем заказ и проверяем, есть ли в нем товары текущего продавца
            order = Order.objects.filter(
                id=pk,
                products__seller=request.user
            ).first()

            if not order:
                return Response(
                    {'error': 'Заказ не найден или у вас нет прав на его обновление'},
                    status=status.HTTP_404_NOT_FOUND
                )

            new_status = request.data.get('status')

            if not new_status:
                return Response(
                    {'error': 'Статус заказа обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_status not in dict(Order.STATUS_CHOICES):
                return Response(
                    {'error': 'Некорректный статус заказа'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order.status = new_status
            order.save()

            serializer = self.get_serializer(order)
            return Response({
                'message': 'Статус заказа успешно обновлен',
                'order': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при обновлении статуса заказа'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def add(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return Response(
                    {'error': 'ID товара обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Товар не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                product=product
            )

            if not created:
                return Response(
                    {'message': 'Товар уже в избранном'},
                    status=status.HTTP_200_OK
                )

            serializer = self.get_serializer(favorite)
            return Response({
                'message': 'Товар успешно добавлен в избранное',
                'favorite': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при добавлении в избранное'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return Response(
                    {'error': 'ID товара обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                favorite = Favorite.objects.get(
                    user=request.user,
                    product_id=product_id
                )
            except Favorite.DoesNotExist:
                return Response(
                    {'error': 'Товар не найден в избранном'},
                    status=status.HTTP_404_NOT_FOUND
                )

            favorite.delete()
            return Response({
                'message': 'Товар успешно удален из избранного'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при удалении из избранного'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SalesStatisticsViewSet(viewsets.ModelViewSet):
    serializer_class = SalesStatisticsSerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdmin]

    def get_queryset(self):
        if self.request.user.role == 'seller':
            return SalesStatistics.objects.filter(seller=self.request.user)
        return SalesStatistics.objects.all()

    @action(detail=False, methods=['get'])
    def seller(self, request):
        if request.user.role != 'seller':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Получаем все заказы продавца
            orders = Order.objects.filter(
                products__seller=request.user
            ).distinct()

            # Рассчитываем общую сумму продаж
            total_sales = sum(order.total_amount for order in orders)

            # Получаем количество заказов
            order_count = orders.count()

            # Получаем статистику по дням
            daily_stats = []
            for order in orders:
                date = order.created_at.date()
                daily_stat = next(
                    (stat for stat in daily_stats if stat['date'] == date),
                    {'date': date, 'sales': 0, 'orders': 0}
                )
                daily_stat['sales'] += order.total_amount
                daily_stat['orders'] += 1
                if daily_stat not in daily_stats:
                    daily_stats.append(daily_stat)

            # Сортируем статистику по дням
            daily_stats.sort(key=lambda x: x['date'])

            # Получаем топ продуктов
            top_products = []
            for order in orders:
                for product in order.products.filter(seller=request.user):
                    product_stat = next(
                        (stat for stat in top_products if stat['product_id'] == product.id),
                        {
                            'product_id': product.id,
                            'product_name': product.name,
                            'sales_count': 0,
                            'total_revenue': 0
                        }
                    )
                    product_stat['sales_count'] += 1
                    product_stat['total_revenue'] += product.price
                    if product_stat not in top_products:
                        top_products.append(product_stat)

            # Сортируем продукты по количеству продаж
            top_products.sort(key=lambda x: x['sales_count'], reverse=True)
            top_products = top_products[:5]  # Берем только топ-5

            return Response({
                'total_sales': total_sales,
                'order_count': order_count,
                'daily_stats': daily_stats,
                'top_products': top_products
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Произошла ошибка при получении статистики'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)