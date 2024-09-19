from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class DatacenterService(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deleted', 'Deleted'),
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
        ('draft', 'Draft'),
        ('deleted', 'Deleted'),
        ('formed', 'Formed'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    creation_date = models.DateTimeField(auto_now_add=True)
    formation_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    creator = models.ForeignKey(User, related_name='orders_created', on_delete=models.CASCADE)
    moderator = models.ForeignKey(User, related_name='orders_moderated', on_delete=models.SET_NULL, null=True, blank=True)

    delivery_address = models.CharField(max_length=255, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    total_price = models.PositiveIntegerField(default=0)

    def calculate_total_price(self):
        self.total_price = sum(item.service.price * item.quantity for item in self.datacenterorderservice_set.all())

    def save(self, *args, **kwargs):
        if self.status == 'draft':
            if DatacenterOrder.objects.filter(creator=self.creator, status='draft').exclude(id=self.id).exists():
                raise ValidationError("У пользователя не может быть более одной заявки в статусе черновик.")
        
        if self.status == 'completed':
            self.calculate_total_price()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} by {self.creator.username}"

class DatacenterOrderService(models.Model):
    order = models.ForeignKey(DatacenterOrder, on_delete=models.CASCADE)
    service = models.ForeignKey(DatacenterService, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    main_status = models.BooleanField(default=False)

    class Meta:
        unique_together = ('order', 'service')

    def __str__(self):
        return f"Order {self.order.id} - Service {self.service.name}"