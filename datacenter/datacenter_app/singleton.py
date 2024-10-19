from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist


class UserSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        """Получаем единственный экземпляр класса."""
        if cls._instance is None:
            cls._instance = cls._create_users()
        return cls._instance

    @classmethod
    def _create_users(cls):
        """Создаем пользователей."""
       
        creator, _ = User.objects.get_or_create(
            id=1,
            defaults={
                'username': "creator_user",
                'first_name': "Иван",
                'last_name': "Иванов",
                'email': "ivan@example.com",
                'is_superuser': False,
                'is_staff': False,
                'is_active': True,
            }
        )
        creator.set_password("1234")  
        creator.save()

       
        moderator, _ = User.objects.get_or_create(
            id=2,
            defaults={
                'username': "moderator_user",
                'first_name': "Петр",
                'last_name': "Петров",
                'email': "petr@example.com",
                'is_superuser': False,
                'is_staff': True, 
                'is_active': True,
            }
        )
        moderator.set_password("1234")  
        moderator.save()

        return creator, moderator

def get_mock_user():
    """Возвращает мокового пользователя (создателя)."""
    return UserSingleton.get_instance()[0]  
