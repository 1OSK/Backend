from rest_framework import serializers
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService, AuthUser

# Сериализатор для услуги
class DatacenterServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['id', 'name', 'description', 'image_url', 'price']

# Сериализатор для связки заказ-услуга
class DatacenterOrderServiceSerializer(serializers.ModelSerializer):
    service = DatacenterServiceSerializer()  # Вложенный сериализатор для самой услуги

    class Meta:
        model = DatacenterOrderService
        fields = ['id', 'service', 'quantity']  # Отображаем услугу и количество

# Основной сериализатор для заказа
class DatacenterOrderSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)  # Имя создателя
    moderator_name = serializers.CharField(source='moderator.username', read_only=True, allow_null=True)  # Имя модератора
    services = DatacenterOrderServiceSerializer(many=True, source='datacenterorderservice_set')  # Используем сериализатор для связи заказа с услугами

    class Meta:
        model = DatacenterOrder
        fields = [
            'id', 
            'status', 
            'creation_date', 
            'formation_date', 
            'completion_date', 
            'creator_name', 
            'moderator_name', 
            'delivery_address', 
            'delivery_time', 
            'total_price', 
            'services'  # Услуги в составе заказа
        ]

# Сериализатор для пользователя
class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined']

# Сериализатор для изображений услуг
class DatacenterServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['image_url']  # Только поле image_url