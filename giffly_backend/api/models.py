from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    ROLES = (
        ('buyer', 'Покупатель'),
        ('seller', 'Продавец'),
        ('admin', 'Администратор'),
    )
    
    role = models.CharField(max_length=20, choices=ROLES, default='buyer')
    phone = models.CharField(max_length=20, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    photo_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.username



# товар
class Product(models.Model):
    seller = models.ForeignKey('User', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# корзина
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField('Product', through='CartItem')

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('product', 'cart')
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'cart'],
                name='unique_cart_item'
            )
        ]


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В обработке'),
        ('completed', 'Завершён'),
        ('canceled', 'Отменён'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_favorite')
        ]

class SalesStatistics(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    period = models.DateField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    order_count = models.PositiveIntegerField()