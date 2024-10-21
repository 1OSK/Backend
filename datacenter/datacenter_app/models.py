from django.db import models
from django.contrib.auth.models import User  
from django.core.exceptions import ValidationError 
from django.utils import timezone  
from rest_framework import serializers
from datetime import datetime
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
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


from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime

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
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders_created', on_delete=models.CASCADE)
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders_moderated', on_delete=models.SET_NULL, null=True, blank=True)
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
    is_creator = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        managed = False
        db_table = 'auth_user'


class NewUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь менеджером?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")

    USERNAME_FIELD = 'email'

    objects = NewUserManager()

    def __str__(self):
        return self.email