# middleware.py
from django.utils.deprecation import MiddlewareMixin
from redis import StrictRedis
from django.conf import settings
from django.contrib.auth.models import User

# Настройки Redis
redis_instance = StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

class CookiePermissionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        session_id = request.COOKIES.get('session_id')

        if session_id:
            username = redis_instance.get(session_id)  # Получаем username из Redis
            if username:
                request.user = User.objects.get(username=username.decode('utf-8'))
            else:
                request.user = None
        else:
            request.user = None

    @staticmethod
    def check_user_permissions(user):
        # Проверка прав доступа
        if user is not None:
            return user.is_authenticated and (user.is_superuser or user.is_staff)
        return False