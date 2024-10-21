from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
import redis
import logging
logger = logging.getLogger(__name__)

session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

class IsManager(permissions.BasePermission):
    """
    Проверяет, является ли пользователь менеджером (is_staff) или администратором (is_superuser).
    """
    def has_permission(self, request, view):
        # Возвращает True, если пользователь менеджер или администратор
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))



class IsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        # Получаем session_id из куки
        session_id = request.COOKIES.get('session_id')
        
        if not session_id:
            logger.warning("Session ID is missing.")
            return False
        
        # Получаем идентификатор пользователя из Redis
        user_id = session_storage.get(session_id)

        if user_id is None:
            logger.warning("Invalid session.")
            return False
        
        # Декодируем идентификатор пользователя
        user_id = user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        # Проверяем, является ли пользователь администратором
        # Ваша логика может отличаться в зависимости от структуры данных
        return request.user.is_authenticated and request.user.is_superuser
    
class IsManagerOrAdmin(permissions.BasePermission):
    """
    Проверяет, является ли пользователь менеджером (is_staff) или администратором (is_superuser).
    """
    def has_permission(self, request, view):
        # Возвращает True, если пользователь менеджер или администратор
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))

# Класс разрешений для проверки роли пользователя
class IsAuthenticatedAndManagerOrOwnOrders(permissions.BasePermission):
   
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Если пользователь — менеджер или администратор, разрешаем доступ
        if request.user.is_staff or request.user.is_superuser:
            return True
        # Иначе проверяем, принадлежит ли заказ пользователю
        return obj.creator == request.user