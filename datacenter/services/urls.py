# services/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.equipment_list_view, name='equipment_list'),
    path('equipment/<int:equipment_id>/', views.equipment_detail_view, name='equipment_detail_view'),
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail_view'),
]