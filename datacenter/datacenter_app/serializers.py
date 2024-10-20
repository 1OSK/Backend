from rest_framework import serializers
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService, AuthUser, CustomUser
from collections import OrderedDict
from datetime import datetime
# Сериализатор для услуги
class DatacenterServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['id', 'name', 'description', 'image_url', 'price']
        
    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем поле необязательным
            new_fields[name] = field
        return new_fields

# Сериализатор для связки заказ-услуга
class DatacenterOrderServiceSerializer(serializers.ModelSerializer):
    service = DatacenterServiceSerializer()  # Вложенный сериализатор для самой услуги

    class Meta:
        model = DatacenterOrderService
        fields = ['id', 'service', 'quantity']  # Отображаем услугу и количество
        
    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем поле необязательным
            new_fields[name] = field
        return new_fields

class DatacenterOrderSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)  # Имя создателя
    moderator_name = serializers.CharField(source='moderator.username', read_only=True, allow_null=True)  # Имя модератора
    services = DatacenterOrderServiceSerializer(many=True, source='datacenterorderservice_set')  # Связь с услугами
    creation_date = serializers.DateTimeField(format='%Y-%m-%dT%H:%M', read_only=True)
    formation_date = serializers.DateTimeField(format='%Y-%m-%dT%H:%M', allow_null=True, required=False)
    completion_date = serializers.DateTimeField(format='%Y-%m-%dT%H:%M', allow_null=True, required=False)
    delivery_time = serializers.DateTimeField(format='%Y-%m-%dT%H:%M', allow_null=True, required=False)

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
    
    def get_fields(self):
        """Делаем все поля необязательными."""
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем поле необязательным
            new_fields[name] = field
        return new_fields


# Сериализатор для пользователя
class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = [
            'id',  
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_creator',    
            'is_moderator',   
            'date_joined',
            'last_login',
        ]
        
    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем поле необязательным
            new_fields[name] = field
        return new_fields

# Сериализатор для изображений услуг
class DatacenterServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['image_url']  # Только поле image_url
    
    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем поле необязательным
            new_fields[name] = field
        return new_fields


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']