from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatacenterServiceAPIView, DatacenterOrderView, DatacenterServiceOrderView, UserView
from rest_framework import permissions
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="My API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@myapi.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # Список услуг и создание новой услуги
    path('datacenters/', DatacenterServiceAPIView.as_view(), name='datacenter-list-create'),
    
    # Получение, обновление и удаление конкретной услуги
    path('datacenters/<int:pk>/', DatacenterServiceAPIView.as_view(), name='datacenter-detail'),

    # Добавление услуги в черновик заявки
    path('datacenters/<int:pk>/add-to-draft/', DatacenterServiceAPIView.as_view(), name='datacenter-add-to-draft'),

    # Добавление изображения через POST
    path('datacenters/<int:pk>/add-image/', DatacenterServiceAPIView.as_view(), name='datacenter-add-image'),
    
    path('datacenter-orders/', DatacenterOrderView.as_view(), name='datacenter-order-list'),  # для списка заявок
    path('datacenter-orders/<int:pk>/', DatacenterOrderView.as_view(), name='datacenter-order-detail'),  # для получения деталей заявки
    path('datacenter-orders/<int:pk>/submit/', DatacenterOrderView.as_view(), name='datacenter-order-submit'),  # PUT: отправка заявки
    path('datacenter-orders/<int:pk>/finalize/', DatacenterOrderView.as_view(), name='datacenter-order-finalize'),  # PUT: завершение заявки
    path('datacenter-orders/<int:pk>/update/', DatacenterOrderView.as_view(), name='datacenter-order-update'),  # PUT: обновление заявки
    path('datacenter-orders/<int:pk>/delete/', DatacenterOrderView.as_view(), name='datacenter-order-delete'),  # DELETE: удаление заявки
    
    # URL для удаления услуги из заявки
    path('datacenter-orders/<int:datacenter_order_id>/datacenters/<int:datacenter_service_id>/', 
         DatacenterServiceOrderView.as_view(), name='delete_datacenter_service'),
    
    # URL для изменения количества услуги в заявке
    path('datacenter-orders/<int:datacenter_order_id>/datacenters/<int:datacenter_service_id>/update/', 
         DatacenterServiceOrderView.as_view(), name='update_datacenter_service'),
    
    path('users/register/', UserView.as_view({'post': 'register'}), name='user-register'),  # Регистрация пользователя
    path('users/update/<int:pk>/', UserView.as_view({'put': 'update_user'}), name='user-update'),  # Обновление информации о пользователе
    path('users/login/', UserView.as_view({'post': 'login_user'}), name='user-login'),  # Вход пользователя
    path('users/logout/', UserView.as_view({'post': 'logout_user'}), name='user-logout'),  # Выход пользователя
]