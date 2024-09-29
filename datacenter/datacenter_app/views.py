from django.shortcuts import render, get_object_or_404, redirect
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import Http404
from django.db import connection
from django.db import models

# Вьюха для отображения списка оборудования
def equipment_list_view_datacenter(request):
    # Получаем максимальную цену из GET-запроса
    max_price_datacenter = request.GET.get('price_datacenter', '')
    
    # Фильтруем только активные услуги
    equipment_queryset = DatacenterService.objects.filter(status='active')
    current_order = None  # Инициализируем переменную для хранения текущего заказа
    
    # Проверяем, аутентифицирован ли пользователь
    if request.user.is_authenticated:
        # Получаем черновик заказа, если он существует
        current_order = DatacenterOrder.objects.filter(creator=request.user, status='draft').first()

    # Фильтруем оборудование по максимальной цене, если указана
    if max_price_datacenter:
        try:
            # Преобразуем значение цены в целое число
            max_price_value = int(max_price_datacenter)
            # Применяем фильтр по цене
            equipment_queryset = equipment_queryset.filter(price__lte=max_price_value)
        except ValueError:
            # Если значение не является числом, выводим ошибку в консоль
            print("Некорректное значение цены:", max_price_datacenter)

    # Подсчитываем общее количество услуг в текущем заказе
    total_quantity = DatacenterOrderService.objects.filter(order=current_order).aggregate(total_quantity=models.Sum('quantity'))['total_quantity'] or 0 if current_order else 0
    has_services_in_order = current_order is not None and total_quantity > 0

    # Возвращаем рендеринг шаблона с переданными данными
    return render(request, 'datacenter_app/equipment_list_view_datacenter.html', {
        'equipment_list_datacenter': equipment_queryset,
        'current_order_id_datacenter': current_order.id if current_order else None,
        'equipment_count_in_order_datacenter': total_quantity,
        'max_price_datacenter': max_price_datacenter,
        'has_services_in_order': has_services_in_order,
    })

# Вьюха для отображения деталей услуги
def equipment_detail_view_datacenter(request, equipment_id):
    # Получаем услугу по её ID или возвращаем 404
    equipment_datacenter = get_object_or_404(DatacenterService, id=equipment_id)
    
    # Преобразуем описание услуги в список характеристик, если описание существует
    characteristics_list_datacenter = equipment_datacenter.description.split(',') if equipment_datacenter.description else []

    # Возвращаем рендеринг шаблона с переданными данными
    return render(request, 'datacenter_app/equipment_detail_view_datacenter.html', {
        'equipment_datacenter': equipment_datacenter,
        'characteristics_list_datacenter': characteristics_list_datacenter,
    })


@login_required
def add_service_to_order_datacenter(request, service_id):
    # Получаем услугу по её ID или возвращаем 404, если услуга не найдена
    service = get_object_or_404(DatacenterService, id=service_id)

    # Получаем или создаем черновик заказа для текущего пользователя
    current_order, created_order = DatacenterOrder.objects.get_or_create(
        creator=request.user, 
        status='draft'
    )

    # Проверяем, есть ли услуга уже в текущем заказе
    order_service, created_service = DatacenterOrderService.objects.get_or_create(
        order=current_order,
        service=service,
        defaults={'quantity': 0}  # Инициализируем количество как 0, если услуги ещё нет
    )

    # Увеличиваем количество услуги на 1
    order_service.quantity += 1
    order_service.save()  # Сохраняем изменения в базе данных
    
    # Логируем добавление или обновление услуги в черновике заказа
    if created_service:
        print(f"Услуга {service.name} добавлена в черновик {current_order.id}.")
    else:
        print(f"Услуга {service.name} обновлена в черновике {current_order.id}. Количество: {order_service.quantity}")

    # Перенаправляем пользователя на список услуг после добавления
    return redirect('equipment_list_view_datacenter')

@login_required
def order_detail_view_datacenter(request, order_id_datacenter):
    # Пытаемся получить заказ по его ID или возвращаем 404
    selected_order_datacenter = get_object_or_404(DatacenterOrder, id=order_id_datacenter, creator=request.user)

    # Получаем все услуги, добавленные в заказ
    equipment_in_order_datacenter = DatacenterOrderService.objects.filter(order=selected_order_datacenter)

    # Проверяем статус заказа
    if selected_order_datacenter.status == 'deleted' or not equipment_in_order_datacenter.exists():
        # Возвращаем пустую корзину, если заказ удален или нет услуг
        return render(request, 'datacenter_app/order_detail_view_datacenter.html', {
            'order_datacenter': selected_order_datacenter,
            'equipment_in_order_datacenter': None,  # Указываем None для услуг
            'equipment_count_in_order_datacenter': 0,  # Указываем 0 для количества услуг
            'total_price_datacenter': 0,  # Указываем 0 для общей стоимости
            'is_empty_cart': True,  # Добавляем флаг для проверки пустой корзины
        })

    # Создаем список данных об услугах для отображения в шаблоне
    equipment_data = [
        {
            'equipment_datacenter': item.service,
            'quantity_datacenter': item.quantity,
            'total_price_datacenter': item.service.price * item.quantity
        }
        for item in equipment_in_order_datacenter
    ]

    # Подсчитываем общее количество услуг и общую стоимость с помощью ORM
    equipment_count_in_order_datacenter = equipment_in_order_datacenter.aggregate(total_quantity=models.Sum('quantity'))['total_quantity'] or 0
    total_price_datacenter = sum(item.service.price * item.quantity for item in equipment_in_order_datacenter)

    # Возвращаем рендеринг шаблона с переданными данными
    return render(request, 'datacenter_app/order_detail_view_datacenter.html', {
        'order_datacenter': selected_order_datacenter,
        'equipment_in_order_datacenter': equipment_data,
        'equipment_count_in_order_datacenter': equipment_count_in_order_datacenter,
        'total_price_datacenter': total_price_datacenter,
        'is_empty_cart': False,  # Указываем, что корзина не пустая
    })

@login_required
def update_order_status_datacenter(request, order_id_datacenter):
    # Обрабатываем только POST-запросы
    if request.method == 'POST':
        action = request.POST.get('action')  # Получаем действие (например, завершить или удалить заказ)
        # Получаем заказ по ID и проверяем, что он принадлежит текущему пользователю
        order = get_object_or_404(DatacenterOrder, id=order_id_datacenter, creator=request.user)

        # Открываем прямое соединение с базой данных для выполнения SQL-запросов
        with connection.cursor() as cursor:
            # Если действие - завершение заказа
            if action == 'complete':
                cursor.execute("""
                    UPDATE datacenter_app_datacenterorder
                    SET status = 'completed', completion_date = NOW(),
                    total_price = (SELECT SUM(quantity * service_id) FROM datacenter_app_datacenterorderservice WHERE order_id = %s)
                    WHERE id = %s
                """, [order_id_datacenter, order_id_datacenter])
                print(f"Заказ {order.id} завершен.")

            # Если действие - удаление заказа
            elif action == 'delete':
                cursor.execute("""
                    UPDATE datacenter_app_datacenterorder
                    SET status = 'deleted'
                    WHERE id = %s
                """, [order_id_datacenter])
                print(f"Заказ {order.id} удален.")

                # Здесь не создаем новый черновик, это будет сделано в add_service_to_order_datacenter

                # Перенаправляем на список услуг после удаления заказа
                return redirect('equipment_list_view_datacenter')

    # Если запрос не является POST, возвращаем 404
    raise Http404("Недопустимый метод запроса")