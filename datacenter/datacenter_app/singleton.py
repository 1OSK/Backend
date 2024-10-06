from django.contrib.auth.models import User

class Creator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Получаем фиксированного пользователя по имени
            cls._instance.user = User.objects.get(username='creator_username')
        return cls._instance

    @classmethod
    def get_instance(cls):
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