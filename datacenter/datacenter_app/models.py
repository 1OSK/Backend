from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
class DatacenterService(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('deleted', 'Удален'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    image_url = models.URLField()
    price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

class DatacenterOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удален'),
        ('formed', 'Сформирован'),
        ('completed', 'Завершен'),
        ('rejected', 'Отклонен'),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    creation_date = models.DateTimeField(default=timezone.now) 
    formation_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    creator = models.ForeignKey(User, related_name='orders_created', on_delete=models.CASCADE)
    moderator = models.ForeignKey(User, related_name='orders_moderated', on_delete=models.SET_NULL, null=True, blank=True)

    delivery_address = models.CharField(max_length=255, blank=True, null=True)  # Сделать необязательным
    delivery_time = models.DateTimeField(null=True, blank=True)  # Оставить необязательным
    total_price = models.PositiveIntegerField(default=0)

    def calculate_total_price(self):
        self.total_price = sum(item.service.price * item.quantity for item in self.datacenterorderservice_set.all())
        print(f"Итоговая стоимость для заказа {self.id}: {self.total_price}")  # Для отладки
        self.save(update_fields=['total_price'])  # Сохраняем только поле total_price

    def save(self, *args, **kwargs):
        # Проверка на изменение статуса, чтобы пересчитать общую стоимость
        if 'update_fields' in kwargs and 'status' in kwargs['update_fields']:
            self.calculate_total_price()  # Вычисляем общую стоимость только при изменении статуса
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ {self.id} от {self.creator.username}"

class DatacenterOrderService(models.Model):
    order = models.ForeignKey(DatacenterOrder, on_delete=models.CASCADE)
    service = models.ForeignKey(DatacenterService, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    main_status = models.BooleanField(default=False)

    class Meta:
        unique_together = ('order', 'service')

    def __str__(self):
        return f"Заказ {self.order.id} - Услуга {self.service.name}"