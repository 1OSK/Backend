from collections import OrderedDict
from rest_framework import serializers
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService, AuthUser

class DatacenterServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['id', 'name', 'description', 'status', 'image_url', 'price']

    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем все поля необязательными
            new_fields[name] = field
        return new_fields

class DatacenterOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterOrder
        fields = ['id', 'status', 'creation_date', 'formation_date', 'completion_date', 'creator', 'moderator', 'delivery_address', 'delivery_time', 'total_price']

    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем все поля необязательными
            new_fields[name] = field
        return new_fields

class DatacenterOrderServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterOrderService
        fields = ['id', 'order', 'service', 'quantity']

    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем все поля необязательными
            new_fields[name] = field
        return new_fields

class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined']

    def get_fields(self):
        new_fields = OrderedDict()
        for name, field in super().get_fields().items():
            field.required = False  # Делаем все поля необязательными
            new_fields[name] = field
        return new_fields

class DatacenterServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['image_url']  # Только поле image_url