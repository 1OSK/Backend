from django.contrib import admin
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService

class DatacenterOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'status', 'total_price', 'creation_date')
    list_filter = ('status',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'status' in form.changed_data:
            obj.calculate_total_price()  # Пересчитываем общую стоимость при изменении статуса

admin.site.register(DatacenterService)
admin.site.register(DatacenterOrder, DatacenterOrderAdmin)
admin.site.register(DatacenterOrderService)