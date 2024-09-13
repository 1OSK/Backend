# services/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.equipment_list_view, name='equipment_list'),
    path('equipment/<int:equipment_id>/', views.equipment_detail_view, name='equipment_detail_view'),
    path('request/<int:request_id>/', views.request_detail_view, name='request_detail_view'),
]