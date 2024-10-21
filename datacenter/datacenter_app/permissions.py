from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
class IsManager(permissions.BasePermission):
    """
    Проверяет, является ли пользователь менеджером (is_staff) или администратором (is_superuser).
    """
    def has_permission(self, request, view):
        # Возвращает True, если пользователь менеджер или администратор
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class IsAdmin(permissions.BasePermission):
    """
    Проверяет, является ли пользователь администратором (is_superuser).
    """
    def has_permission(self, request, view):
        # Возвращает True, если пользователь администратор
        if request.user and request.user.is_superuser:
            return True
        raise PermissionDenied("У вас нет прав на выполнение этого действия.")
    
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