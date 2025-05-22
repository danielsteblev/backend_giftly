from rest_framework import serializers
from .models import User, Product, Cart, Order, Favorite, SalesStatistics, CartItem
from django.contrib.auth.hashers import make_password
from django.core.validators import EmailValidator

class UserSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"], required=False, allow_null=True)
    role = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'phone', 'birth_date', 'photo_url']
        read_only_fields = ['id', 'email']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password', 'first_name', 'last_name', 'role', 'phone', 'birth_date')

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Пароли не совпадают")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        email = validated_data.get('email')
        
        # Создаем пользователя с email в качестве username
        user = User.objects.create_user(
            username=email,  # Устанавливаем email как username
            email=email,
            password=password,
            is_active=True,
            **validated_data
        )
        return user

class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    is_favorite = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'seller', 'name', 'description', 'price', 'image_url', 'created_at', 'updated_at', 'is_favorite']
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_favorite']
        extra_kwargs = {
            'seller': {'required': True},
            'name': {'required': True, 'min_length': 3, 'max_length': 200},
            'description': {'required': False, 'allow_blank': True},
            'price': {'required': True, 'min_value': 0},
            'image_url': {'required': False},
        }

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            try:
                return Favorite.objects.filter(user=request.user, product=obj).exists()
            except:
                return False
        return False

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительным числом")
        return value

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Название товара должно содержать минимум 3 символа")
        return value

    def validate_seller(self, value):
        if not hasattr(value, 'role') or value.role != 'seller':
            raise serializers.ValidationError("Только пользователи с ролью 'seller' могут создавать товары")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['seller'] = request.user
        return super().create(validated_data)

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cartitem_set', many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price']
        read_only_fields = ['id', 'user', 'total_price']

    def get_total_price(self, obj):
        total = 0
        for item in obj.cartitem_set.all():
            total += item.product.price * item.quantity
        return total

class OrderSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'products', 'total_amount', 'status', 'status_display', 'created_at']
        read_only_fields = ['id', 'user', 'total_amount', 'created_at']

class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'product', 'created_at']
        read_only_fields = ['id', 'created_at']

class SalesStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesStatistics
        fields = '__all__'