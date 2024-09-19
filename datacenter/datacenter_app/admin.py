from django.contrib import admin
from django.contrib.auth.models import User
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService

# Регистрация других моделей
admin.site.register(DatacenterService)
admin.site.register(DatacenterOrder)
admin.site.register(DatacenterOrderService)