from django.contrib import admin
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService

# Создаем класс для управления DatacenterOrder в админ-панели
class DatacenterOrderAdmin(admin.ModelAdmin):
    # Определяем поля, которые будут отображаться в списке заказов в админке
    list_display = ('id', 'creator', 'status', 'total_price', 'creation_date')
    # Добавляем фильтр по статусу заказа
    list_filter = ('status',)

    # Переопределяем метод сохранения объекта в админке
    def save_model(self, request, obj, form, change):
        # Вызываем стандартный метод сохранения
        super().save_model(request, obj, form, change)
        # Если объект был изменен и статус заказа поменялся
        if change and 'status' in form.changed_data:
            # Вызываем метод для пересчета общей стоимости заказа
            obj.calculate_total_price()

# Регистрируем модели для отображения в админ-панели
admin.site.register(DatacenterService)  # Регистрация модели DatacenterService без кастомизации
admin.site.register(DatacenterOrder, DatacenterOrderAdmin)  # Регистрация DatacenterOrder с кастомным админ-классом
admin.site.register(DatacenterOrderService)  # Регистрация модели DatacenterOrderService без кастомизации