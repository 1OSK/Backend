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
    
    description = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    image_url = models.URLField(max_length=200, blank=True, null=True)
   
    price = models.PositiveIntegerField(null=True, blank=True, default=0)

    
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

    
    delivery_address = models.CharField(max_length=255, blank=True, null=True)  
    
    delivery_time = models.DateTimeField(null=True, blank=True)  
    
    total_price = models.PositiveIntegerField(null=True, blank=True)

    
    def __str__(self):
        return f"Заказ {self.id} от {self.creator.username}"


class DatacenterOrderService(models.Model):
    
    order = models.ForeignKey(DatacenterOrder, on_delete=models.CASCADE)
    
    service = models.ForeignKey(DatacenterService, on_delete=models.CASCADE)
    
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)


    
    class Meta:
       
        unique_together = ('order', 'service')

    
    def __str__(self):
        return f"Заказ {self.order.id} - Услуга {self.service.name}"
    
class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField(default=False)
    username = models.CharField(unique=True, max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now=True)
    first_name = models.CharField(max_length=150)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        managed = False
        db_table = 'auth_user'

