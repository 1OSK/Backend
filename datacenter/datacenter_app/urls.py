# datacenter_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.equipment_list_view_datacenter, name='equipment_list_datacenter'),
    path('equipment/<int:equipment_id>/', views.equipment_detail_view_datacenter, name='equipment_detail_view_datacenter'),
    path('order/<int:order_id_datacenter>/', views.order_detail_view_datacenter, name='order_detail_view_datacenter'),
]