# services/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    path('request/<int:request_id>/', views.request_detail, name='request_detail'),
]