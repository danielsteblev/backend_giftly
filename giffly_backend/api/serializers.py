from rest_framework import serializers
from .models import User, Product, Cart, Order, Favorite, SalesStatistics
from django.contrib.auth.hashers import make_password
from django.core.validators import EmailValidator

class UserSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"], required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'phone', 'birth_date']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone': {'required': False},
        }
        read_only_fields = ['id']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(validators=[EmailValidator()])
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value
    
    def create(self, validated_data):
        username = validated_data['email']
        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='buyer'
        )
        return user

class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='seller'), required=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', "seller", 'price', 'image_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': True, 'min_length': 3, 'max_length': 200},
            'description': {'required': False, 'allow_blank': True},
            'price': {'required': True, 'min_value': 0},
            'image_url': {'required': False},
            'seller': {'required': True},
        }

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительным числом")
        return value

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Название товара должно содержать минимум 3 символа")
        return value

    def validate_seller(self, value):
        if value.role != 'seller':
            raise serializers.ValidationError("Только пользователи с ролью 'seller' могут создавать товары")
        return value

class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'

class SalesStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesStatistics
        fields = '__all__'