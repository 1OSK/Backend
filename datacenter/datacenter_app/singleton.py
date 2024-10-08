from django.contrib.auth.models import User
from .models import DatacenterOrder  

class Creator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Получаем или создаем пользователя
            cls._instance.user = cls.get_or_create_user('admin_datacenter', 'your_password')  
        return cls._instance

    @classmethod
    def get_or_create_user(cls, username, password):
        user, created = User.objects.get_or_create(username=username, defaults={'is_staff': True, 'is_superuser': True})
        if created:
            # Убедитесь, что пароль зашифрован
            user.set_password(password)
            user.save()
        return user

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()  # Создаем экземпляр, если он еще не создан
        return cls._instance
    
class Moderator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Получаем фиксированного пользователя по имени
            cls._instance.user = User.objects.get(username='moderator_username')
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls._instance