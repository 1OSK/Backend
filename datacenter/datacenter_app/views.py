from django.shortcuts import render, get_object_or_404, redirect
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import Http404
from django.db import connection

def equipment_list_view_datacenter(request):
    max_price_datacenter = request.GET.get('price_datacenter', '')
    equipment_queryset = DatacenterService.objects.filter(status='active')
    current_order = None  # Инициализируем current_order

    if request.user.is_authenticated:
        current_order = DatacenterOrder.objects.filter(creator=request.user, status='draft').first()

        if current_order is None:
            current_order = DatacenterOrder.objects.create(creator=request.user, status='draft')
            print("Создан новый черновик:", current_order.id)

        # Автоматически добавляем услуги в черновик
        for service in equipment_queryset:
            add_service_to_order_datacenter(request, service.id)

    if max_price_datacenter:
        try:
            max_price_value = int(max_price_datacenter)
            equipment_queryset = equipment_queryset.filter(price__lte=max_price_value)
        except ValueError:
            pass

    total_quantity = sum(item.quantity for item in DatacenterOrderService.objects.filter(order=current_order)) if current_order else 0

    # Проверяем, есть ли услуги в черновике
    has_services_in_order = current_order is not None and total_quantity > 0

    return render(request, 'datacenter_app/equipment_list_view_datacenter.html', {
        'equipment_list_datacenter': equipment_queryset,
        'current_order_id_datacenter': current_order.id if current_order else None,
        'equipment_count_in_order_datacenter': total_quantity,
        'max_price_datacenter': max_price_datacenter,
        'has_services_in_order': has_services_in_order,
    })

def equipment_detail_view_datacenter(request, equipment_id):
    equipment_datacenter = get_object_or_404(DatacenterService, id=equipment_id)
    characteristics_list_datacenter = equipment_datacenter.description.split(',') if equipment_datacenter.description else []

    return render(request, 'datacenter_app/equipment_detail_view_datacenter.html', {
        'equipment_datacenter': equipment_datacenter,
        'characteristics_list_datacenter': characteristics_list_datacenter,
    })

@login_required
def add_service_to_order_datacenter(request, service_id):
    service = get_object_or_404(DatacenterService, id=service_id)

    # Проверяем, есть ли уже черновик у пользователя
    current_order = DatacenterOrder.objects.filter(creator=request.user, status='draft').first()

    # Если черновика нет, создаем новый
    if current_order is None:
        current_order = DatacenterOrder.objects.create(creator=request.user, status='draft')
        print("Создан новый черновик:", current_order.id)  # Для отладки

    # Проверяем, пустой ли текущий заказ
    order_services_count = DatacenterOrderService.objects.filter(order=current_order).count()

    if order_services_count == 0:
        # Добавляем услугу в текущий заказ
        order_service, created = DatacenterOrderService.objects.get_or_create(
            order=current_order,
            service=service,
            defaults={'quantity': 1}
        )

        if created:
            print(f"Услуга {service.name} добавлена в черновик {current_order.id}.")
        else:
            order_service.quantity += 1
            order_service.save()
            print(f"Услуга {service.name} обновлена в черновике {current_order.id}.")

    else:
        print(f"Услуга {service.name} не добавлена, так как черновик {current_order.id} не пуст.")

    return redirect('equipment_list_view_datacenter')

@login_required
def order_detail_view_datacenter(request, order_id_datacenter):
    selected_order_datacenter = get_object_or_404(DatacenterOrder, id=order_id_datacenter, creator=request.user, status__in=['draft', 'formed', 'completed'])
    
    equipment_in_order_datacenter = DatacenterOrderService.objects.filter(order=selected_order_datacenter)
    
    equipment_count_in_order_datacenter = sum(item.quantity for item in equipment_in_order_datacenter)
    
    equipment_data = [
        {
            'equipment_datacenter': item.service,
            'quantity_datacenter': item.quantity,
            'total_price_datacenter': item.service.price * item.quantity
        }
        for item in equipment_in_order_datacenter
    ]

    return render(request, 'datacenter_app/order_detail_view_datacenter.html', {
        'order_datacenter': selected_order_datacenter,
        'equipment_in_order_datacenter': equipment_data,
        'equipment_count_in_order_datacenter': equipment_count_in_order_datacenter,
        'total_price_datacenter': selected_order_datacenter.total_price,
    })

@login_required
def update_order_status_datacenter(request, order_id_datacenter):
    if request.method == 'POST':
        action = request.POST.get('action')
        order = get_object_or_404(DatacenterOrder, id=order_id_datacenter, creator=request.user)

        with connection.cursor() as cursor:
            if action == 'complete':
                # Подсчитываем итоговую стоимость
                cursor.execute("""
                    UPDATE datacenter_app_datacenterorder
                    SET status = 'completed', completion_date = NOW(),
                    total_price = (SELECT SUM(quantity * service_id) FROM datacenter_app_datacenterorderservice WHERE order_id = %s)
                    WHERE id = %s
                """, [order_id_datacenter, order_id_datacenter])
                print(f"Заказ {order.id} завершен.")

            elif action == 'delete':
                cursor.execute("""
                    UPDATE datacenter_app_datacenterorder
                    SET status = 'deleted'
                    WHERE id = %s
                """, [order_id_datacenter])
                print(f"Заказ {order.id} удален.")
                
                # Создаем новый черновик с total_price по умолчанию и текущей датой
                cursor.execute("""
                    INSERT INTO datacenter_app_datacenterorder (creator_id, status, total_price, creation_date)
                    VALUES (%s, 'draft', 0, NOW())
                    RETURNING id
                """, [request.user.id])
                new_order_id = cursor.fetchone()[0]
                print(f"Создан новый черновик: {new_order_id}")
                return redirect('equipment_list_view_datacenter')  # Перенаправляем на список услуг

    raise Http404("Недопустимый метод запроса")