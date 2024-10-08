from rest_framework import serializers
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from django.contrib.auth.models import User
from .singleton import Creator 

class DatacenterServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterService
        fields = ['id', 'name', 'price', 'status', 'image_url'] 


class DatacenterOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatacenterOrder
        fields = ['id', 'status', 'creation_date', 'completion_date', 'creator', 'moderator', 'delivery_address','delivery_time', 'total_price']  # Укажите нужные поля

class DatacenterOrderServiceSerializer(serializers.ModelSerializer):
    service = DatacenterServiceSerializer()  # Вложенный сериализатор для услуги
    order = DatacenterOrderSerializer()  # Вложенный сериализатор для заказа

    class Meta:
        model = DatacenterOrderService
        fields = ['id', 'order', 'service', 'quantity']  # Укажите нужные поля

    def create(self, validated_data):
        service_data = validated_data.pop('service')
        service = DatacenterService.objects.get(id=service_data['id'])  # Получение услуги
        order_data = validated_data.pop('order')
        order = DatacenterOrder.objects.get(id=order_data['id'])  # Получение заказа
        order_service = DatacenterOrderService.objects.create(service=service, order=order, **validated_data)
        return order_service

    def update(self, instance, validated_data):
        service_data = validated_data.pop('service', None)
        order_data = validated_data.pop('order', None)

        if service_data:
            service = DatacenterService.objects.get(id=service_data['id'])
            instance.service = service

        if order_data:
            order = DatacenterOrder.objects.get(id=order_data['id'])
            instance.order = order

        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.save()
        return instance
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']