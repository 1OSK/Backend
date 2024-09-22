from django.urls import path
from .views import (
    equipment_list_view_datacenter,
    equipment_detail_view_datacenter,
    order_detail_view_datacenter,
    add_service_to_order_datacenter,
    update_order_status_datacenter,  
)

urlpatterns = [
    path('', equipment_list_view_datacenter, name='equipment_list_view_datacenter'),
    path('equipment/<int:equipment_id>/', equipment_detail_view_datacenter, name='equipment_detail_view_datacenter'),
    path('order/<int:order_id_datacenter>/', order_detail_view_datacenter, name='order_detail_view_datacenter'),
    path('add_service/<int:service_id>/', add_service_to_order_datacenter, name='add_service_to_order_datacenter'),
    path('update_order/<int:order_id_datacenter>/', update_order_status_datacenter, name='update_order_status_datacenter'), 
]