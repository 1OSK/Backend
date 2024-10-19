from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  DatacenterOrderViewSet, ServiceOrderViewSet, UserViewSet
from .views import DatacenterServiceAPIView, DatacenterOrderView


urlpatterns = [
    # Список услуг и создание новой услуги
    path('services/', DatacenterServiceAPIView.as_view(), name='service-list-create'),
    
    # Получение, обновление и удаление конкретной услуги
    path('services/<int:pk>/', DatacenterServiceAPIView.as_view(), name='service-detail'),

    # Добавление услуги в черновик заказа
    path('services/<int:pk>/add-to-draft/', DatacenterServiceAPIView.as_view(), name='service-add-to-draft'),

     # Добавление изображения через POST
    path('services/<int:pk>/add-image/', DatacenterServiceAPIView.as_view(), name='service-add-image'),
    
    
    path('orders/', DatacenterOrderView.as_view(), name='order-list'),  # для списка заказов
    path('orders/<int:pk>/', DatacenterOrderView.as_view(), name='order-detail'),  # для получения деталей заказа
    path('orders/<int:pk>/submit/', DatacenterOrderView.as_view(), name='order-submit'),  # PUT: отправка заказа
    path('orders/<int:pk>/finalize/', DatacenterOrderView.as_view(), name='order-finalize'),  # PUT: завершение заказа
    path('orders/<int:pk>/update/', DatacenterOrderView.as_view(), name='order-update'),  # PUT: обновление заказа
    path('orders/<int:pk>/delete/', DatacenterOrderView.as_view(), name='order-delete'),  # DELETE: удаление заказа
]