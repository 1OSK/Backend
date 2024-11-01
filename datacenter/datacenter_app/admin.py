# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, DatacenterService, DatacenterOrder, DatacenterOrderService

# Создаем кастомный класс админки для CustomUser
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'is_staff', 'is_superuser')  # Определяем, какие поля будут видны в списке
    list_filter = ('is_staff', 'is_superuser')  # Добавляем фильтры для удобства
    ordering = ('email',)  # Сортировка по email
    search_fields = ('email',)  # Поиск по email
    fieldsets = (
        (None, {'fields': ('email', 'password')}),  # Обязательно добавьте поля для email и пароля
        (('Permissions'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (None, {'fields': ('last_login',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets  # Используйте стандартный набор полей для создания нового пользователя

# Регистрируем кастомную модель пользователя в админке
admin.site.register(CustomUser, CustomUserAdmin)

# Регистрация других моделей для админ-панели
class DatacenterOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'status', 'total_price', 'creation_date')
    list_filter = ('status',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'status' in form.changed_data:
            obj.calculate_total_price()

admin.site.register(DatacenterService)
admin.site.register(DatacenterOrder, DatacenterOrderAdmin)
admin.site.register(DatacenterOrderService)