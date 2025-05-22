from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import User, Product, Cart, Order, Favorite, SalesStatistics

admin.site.register(User)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(Favorite)
admin.site.register(SalesStatistics)

# тест
