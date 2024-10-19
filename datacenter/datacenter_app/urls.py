from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  DatacenterOrderViewSet, ServiceOrderViewSet, UserViewSet
from .views import DatacenterServiceAPIView


urlpatterns = [
    # Список услуг и создание новой услуги
    path('services/', DatacenterServiceAPIView.as_view(), name='service-list-create'),
    
    # Получение, обновление и удаление конкретной услуги
    path('services/<int:pk>/', DatacenterServiceAPIView.as_view(), name='service-detail'),

    # Добавление услуги в черновик заказа
    path('services/<int:pk>/add-to-draft/', DatacenterServiceAPIView.as_view(), name='service-add-to-draft'),

     # Добавление изображения через POST
    path('services/<int:pk>/add-image/', DatacenterServiceAPIView.as_view(), name='service-add-image'),
]