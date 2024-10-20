from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
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
    
    path('datacenter-services/', get_datacenter_service_list, name='datacenter_service_list'),  # Путь для списка услуг
    path('datacenter-services/<int:pk>/', get_datacenter_service, name='datacenter_service_detail'),  # Путь для получения услуги по ID
    path('datacenter-services/create/', create_datacenter_service, name='datacenter_service_create'),  # Путь для добавления новой услуги
    path('datacenter-services/<int:pk>/update/', update_datacenter_service, name='datacenter_service_update'),  # Путь для обновления услуги
    path('datacenter-services/<int:pk>/delete/', delete_datacenter_service, name='datacenter_service_delete'),  # Путь для удаления услуги
    path('datacenter-services/<int:pk>/add-to-draft/', add_to_draft, name='datacenter_service_add_to_draft'),  # Путь для добавления услуги в черновик
    path('datacenter-services/<int:pk>/add-image/', add_image, name='datacenter_service_add_image'),  # Путь для добавления изображения
    
    # 1. Получение списка заказов
    path('datacenter-orders/', list_orders, name='list_orders'),

    # 2. Получение информации о конкретном заказе
    path('datacenter-orders/<int:pk>/', retrieve_order, name='retrieve_order'),

    # 3. Удаление заявки
    path('datacenter-orders/<int:pk>/delete/', delete_order, name='delete_order'),

    # 4. Подтверждение заявки
    path('datacenter-orders/<int:pk>/submit/', submit_order, name='submit_order'),

    # 5. Завершение или отклонение заявки
    path('datacenter-orders/<int:pk>/finalize/', finalize_order, name='finalize_order'),

    # 6. Изменение заявки
    path('datacenter-orders/<int:pk>/update/', update_order, name='update_order'),
    
    # DELETE: Удаление услуги из заказа
    path('datacenter-orders-services/<int:datacenter_order_id>/datacenter-services/<int:datacenter_service_id>/delete/', delete_service_from_order, name='delete_service_from_order'),

    # PUT: Изменение количества услуги в заказе
    path('datacenter-orders-services/<int:datacenter_order_id>/datacenter-services/<int:datacenter_service_id>/update/', update_service_quantity_in_order, name='update_service_quantity_in_order'),
    
    path('users/register/', register_user, name='register_user'),
    
    path('users/login/', login_user, name='login_user'),
    
    path('users/logout/', logout_user, name='logout_user'),
    
    path('users/update/<int:pk>/', update_user, name='update_user'),
    
]