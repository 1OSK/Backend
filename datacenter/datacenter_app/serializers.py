from rest_framework import serializers
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService, AuthUser

class DatacenterServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['id', 'name', 'description', 'status', 'image_url', 'price']

class DatacenterOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterOrder
        fields = ['id', 'status', 'creation_date', 'formation_date', 'completion_date', 'creator', 'moderator', 'delivery_address', 'delivery_time', 'total_price']

class DatacenterOrderServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterOrderService
        fields = ['id', 'order', 'service', 'quantity']

class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined']