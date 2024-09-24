from django.urls import path
from .views import (
    # Импортируем представления, которые будут связаны с маршрутами
    equipment_list_view_datacenter,  # Отображение списка оборудования
    equipment_detail_view_datacenter,  # Отображение подробной информации об оборудовании
    order_detail_view_datacenter,  # Отображение деталей заказа
    add_service_to_order_datacenter,  # Добавление услуги в заказ
    update_order_status_datacenter,  # Обновление статуса заказа
)

# Определение маршрутов для приложения
urlpatterns = [
    # Главная страница списка оборудования
    path('', equipment_list_view_datacenter, name='equipment_list_view_datacenter'),
    
    # Страница с детальной информацией об отдельной услуге (оборудовании)
    # <int:equipment_id> — переменная часть URL, которая передает идентификатор оборудования
    path('equipment/<int:equipment_id>/', equipment_detail_view_datacenter, name='equipment_detail_view_datacenter'),
    
    # Страница с деталями определенного заказа
    # <int:order_id_datacenter> — переменная часть URL, передающая идентификатор заказа
    path('order/<int:order_id_datacenter>/', order_detail_view_datacenter, name='order_detail_view_datacenter'),
    
    # Добавление услуги в заказ
    # <int:service_id> — идентификатор услуги, которую нужно добавить в заказ
    path('add_service/<int:service_id>/', add_service_to_order_datacenter, name='add_service_to_order_datacenter'),
    
    # Обновление статуса заказа (например, завершение или удаление)
    # <int:order_id_datacenter> — идентификатор заказа, для которого обновляется статус
    path('update_order/<int:order_id_datacenter>/', update_order_status_datacenter, name='update_order_status_datacenter'), 
]