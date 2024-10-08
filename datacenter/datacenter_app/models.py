from django.db import models
from django.contrib.auth.models import User  # Модель пользователя, используемая для связи с заказом
from django.core.exceptions import ValidationError  # Импорт исключения для обработки ошибок валидации
from django.utils import timezone  # Импорт для работы с временными метками

class DatacenterService(models.Model):
    # Варианты статуса для услуги: "Активный" или "Удален"
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('deleted', 'Удален'),
    ]

    # Название услуги с максимальной длиной 255 символов (обязательно)
    name = models.CharField(max_length=255)
    # Описание услуги (текстовое поле, может быть пустым)
    description = models.TextField(null=True, blank=True)
    # Статус услуги, выбирается из STATUS_CHOICES, по умолчанию "Активный"
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    # URL-адрес изображения для услуги (может быть пустым)
    image_url = models.URLField(max_length=200, blank=True, null=True)
    # Цена услуги, положительное целое число, по умолчанию 0
    price = models.PositiveIntegerField(null=True, blank=True, default=0)

    # Метод для удобного отображения объекта в виде строки (название услуги)
    def __str__(self):
        return self.name

# Модель заказа в датацентре
class DatacenterOrder(models.Model):
    # Варианты статуса для заказа: черновик, удален, сформирован, завершен, отклонен
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удален'),
        ('formed', 'Сформирован'),
        ('completed', 'Завершен'),
        ('rejected', 'Отклонен'),
    ]

    # Статус заказа с выбором из STATUS_CHOICES, по умолчанию "Черновик"
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    # Дата создания заказа, по умолчанию текущее время
    creation_date = models.DateTimeField(default=timezone.now)
    # Дата формирования заказа (может быть пустой)
    formation_date = models.DateTimeField(null=True, blank=True)
    # Дата завершения заказа (может быть пустой)
    completion_date = models.DateTimeField(null=True, blank=True)
    # Связь с пользователем, который создал заказ (удаление пользователя приведет к удалению всех его заказов)
    creator = models.ForeignKey(User, related_name='orders_created', on_delete=models.CASCADE)
    # Связь с пользователем-модератором, который может редактировать или завершать заказ (при удалении модератора связь будет установлена в NULL)
    moderator = models.ForeignKey(User, related_name='orders_moderated', on_delete=models.SET_NULL, null=True, blank=True)

    # Адрес доставки, который может быть пустым или необязательным
    delivery_address = models.CharField(max_length=255, blank=True, null=True)  # Сделать необязательным
    # Время доставки (опционально)
    delivery_time = models.DateTimeField(null=True, blank=True)  # Оставить необязательным
    # Итоговая стоимость заказа, положительное целое число, по умолчанию 0
    total_price = models.PositiveIntegerField(null=True, blank=True)

    # Метод для расчета общей стоимости заказа
    def calculate_total_price(self):
        # Рассчитываем общую стоимость как сумму цен всех услуг, умноженных на количество каждой услуги
        self.total_price = sum(item.service.price * item.quantity for item in self.datacenterorderservice_set.all())
        # Для отладки выводим итоговую стоимость заказа
        print(f"Итоговая стоимость для заказа {self.id}: {self.total_price}")
        # Сохраняем обновленное значение поля total_price в базе данных
        self.save(update_fields=['total_price'])

    # Переопределяем метод save для дополнительной логики при сохранении объекта
    def save(self, *args, **kwargs):
        # Если переданы аргументы для обновления полей и статус является одним из обновляемых полей
        if 'update_fields' in kwargs and 'status' in kwargs['update_fields']:
            # Пересчитываем общую стоимость только при изменении статуса
            self.calculate_total_price()
        # Вызываем метод сохранения родительского класса
        super().save(*args, **kwargs)

    # Метод для представления объекта заказа в виде строки (например, "Заказ 1 от user123")
    def __str__(self):
        return f"Заказ {self.id} от {self.creator.username}"

# Промежуточная модель, связывающая заказы и услуги (многие ко многим)
class DatacenterOrderService(models.Model):
    # Связь с моделью заказа (удаление заказа удалит все связанные с ним услуги)
    order = models.ForeignKey(DatacenterOrder, on_delete=models.CASCADE)
    # Связь с моделью услуги (удаление услуги удалит запись об этой услуге в заказе)
    service = models.ForeignKey(DatacenterService, on_delete=models.CASCADE)
    
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)


    # Класс Meta для описания метаданных модели
    class Meta:
        # Составной уникальный ключ, гарантирующий, что одна услуга не может быть добавлена более одного раза к одному заказу
        unique_together = ('order', 'service')

    # Метод для представления объекта в виде строки (например, "Заказ 1 - Услуга Hosting")
    def __str__(self):
        return f"Заказ {self.order.id} - Услуга {self.service.name}"
    
