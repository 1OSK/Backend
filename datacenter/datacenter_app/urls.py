from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DatacenterServiceViewSet, DatacenterOrderViewSet, ServiceOrderViewSet, UserViewSet

# Create a router for the main resources
router = DefaultRouter()
router.register(r'services', DatacenterServiceViewSet, basename='datacenter-service')
router.register(r'orders', DatacenterOrderViewSet, basename='datacenter-order')
router.register(r'users', UserViewSet, basename='user')
# Define custom routes for ServiceOrderViewSet
urlpatterns = [
    path('', include(router.urls)),
    path('orders/<int:order_id>/services/<int:service_id>/', ServiceOrderViewSet.as_view({'delete': 'destroy', 'put': 'update'}), name='service-order'),
]