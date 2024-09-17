from django.shortcuts import render, get_object_or_404
from datetime import datetime
# Пример данных
equipment_list = [
    {
        'id': 1,
        'name': 'Коммутатор BROCADE G610',
        'price': 815400,
        'image': 'http://127.0.0.1:9000/something/1.png',
        'characteristics': 'Поддержка до 24 портов, высокая производительность, возможность объединения в стеки.'
    },
    {
        'id': 2,
        'name': 'Сервер DELL R650 10SFF',
        'price': 515905,
        'image': 'http://127.0.0.1:9000/something/2.png',
        'characteristics': 'Процессоры Intel Xeon Scalable, до 1.5 ТБ оперативной памяти, поддержка NVMe.'
    },
    {
        'id': 3,
        'name': 'СХД DELL PowerVault MD1400 External SAS 12 Bays',
        'price': 124800,
        'image': 'http://127.0.0.1:9000/something/3.png',
        'characteristics': 'До 12 дисков, интерфейс SAS 12 Гбит/с, высокая отказоустойчивость.'
    },
    {
        'id': 4,
        'name': 'Конфигуратор Dell R250',
        'price': 166372,
        'image': 'http://127.0.0.1:9000/something/4.png',
        'characteristics': 'Поддержка до 10 ядер, до 2 ТБ памяти DDR4, компактный корпус.'
    },
    {
        'id': 5,
        'name': 'Серверный Настенный шкаф 15U',
        'price': 326590,
        'image': 'http://127.0.0.1:9000/something/5.png',
        'characteristics': '15 юнитов, высококачественная сталь, возможность установки на стену.'
    },
    {
        'id': 6,
        'name': 'Патч-корд iOpen ANP612B-BK-50M',
        'price': 5199,
        'image': 'http://127.0.0.1:9000/something/6.png',
        'characteristics': 'Длина 50 м, оболочка из ПВХ, защита от помех.'
    },
]



equipment_orders = [
    {'id': 1,
     'date': datetime(2024, 9, 12, 12, 12, 30),
     'address': 'Москва, ул. Мироновская, 25'
     },
    
    # другие заявки
]
    
# Пример данных по заказам с оборудованием и количеством
order_items = [
    {'order_id': 1, 'equipment_id': 1, 'quantity': 3},  # Заказ 1, Оборудование 1, Кол-во 3
    {'order_id': 1, 'equipment_id': 2, 'quantity': 1},  # Заказ 1, Оборудование 2, Кол-во 1
    {'order_id': 1, 'equipment_id': 3, 'quantity': 5},  # Заказ 1, Оборудование 3, Кол-во 5
    # другие строки
]

def equipment_list_view(request):
    max_price_query = request.GET.get('price', '')  # Запрос по максимальной цене

    filtered_equipment = equipment_list
    if max_price_query:
        try:
            max_price_value = int(max_price_query)
            filtered_equipment = [eq for eq in filtered_equipment if eq['price'] <= max_price_value]
        except ValueError:
            pass

    current_order_id = 1  # Пример ID текущего заказа

    # Фильтруем все записи, относящиеся к текущему заказу
    items_in_order = [item for item in order_items if item['order_id'] == current_order_id]
    
    # Подсчитываем общее количество всех предметов (включая дубликаты)
    total_quantity = sum(item['quantity'] for item in items_in_order)

    return render(request, 'services/equipment_list.html', {
        'equipment_list': filtered_equipment,
        'current_order_id': current_order_id,
        'equipment_count_in_order': total_quantity,
        'max_price_query': max_price_query,
    })

def equipment_detail_view(request, equipment_id):
    equipment = next((eq for eq in equipment_list if eq['id'] == equipment_id), None)

    if not equipment:
        return get_object_or_404(equipment)

    characteristics_list = equipment['characteristics'].split(',') if equipment.get('characteristics') else []

    return render(request, 'services/equipment_detail_view.html', {
        'equipment': equipment,
        'characteristics_list': characteristics_list,
    })
    
def order_detail_view(request, order_id):
    # Получаем заказ по его ID
    selected_order = next((order for order in equipment_orders if order['id'] == order_id), None)

    if selected_order:
        # Фильтруем все записи, относящиеся к текущему заказу
        items_in_order = [item for item in order_items if item['order_id'] == order_id]
        
        # Объединяем данные об оборудовании с количеством
        equipment_in_order = [
            {
                'equipment': next(eq for eq in equipment_list if eq['id'] == item['equipment_id']),
                'quantity': item['quantity'],
                'total_price': next(eq for eq in equipment_list if eq['id'] == item['equipment_id'])['price'] * item['quantity']
            }
            for item in items_in_order
        ]
        
        # Подсчитываем общее количество всех предметов (включая дубликаты)
        equipment_count_in_order = sum(item['quantity'] for item in items_in_order)
    else:
        equipment_in_order = []
        equipment_count_in_order = 0

    return render(request, 'services/order_detail_view.html', {
        'order': selected_order,
        'equipment_in_order': equipment_in_order,
        'equipment_count_in_order': equipment_count_in_order
    })