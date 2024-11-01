from django.core.management.base import BaseCommand
from datacenter_app.models import CustomUser  # Импортируйте вашу модель пользователя

class Command(BaseCommand):
    help = 'Make all superusers have is_staff=True'

    def handle(self, *args, **kwargs):
        superusers = CustomUser.objects.filter(is_superuser=True)
        for user in superusers:
            if not user.is_staff:
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Updated is_staff for superuser {user.email}'))
        self.stdout.write(self.style.SUCCESS('All superusers updated with is_staff=True'))