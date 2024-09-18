from django.shortcuts import render, get_object_or_404
from datetime import datetime
# Пример данных
equipment_list_datacenter = [
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


# Объединенные данные по заказам с оборудованием
orders_datacenter = [
    {
        'id': 1,
        'date': datetime(2024, 9, 12, 12, 12),
        'address': 'Москва, ул. Мироновская, 25',
        'items': [
            {'equipment_id': 1, 'quantity': 3},
            {'equipment_id': 2, 'quantity': 1},
            {'equipment_id': 3, 'quantity': 5},
        ]
    },
    # другие заявки...
]
def equipment_list_view_datacenter(request):
    max_price_query = request.GET.get('price_datacenter', '')  # Запрос по максимальной цене

    filtered_equipment_datacenter = equipment_list_datacenter
    if max_price_query:
        try:
            max_price_value = int(max_price_query)
            filtered_equipment_datacenter = [eq for eq in filtered_equipment_datacenter if eq['price'] <= max_price_value]
        except ValueError:
            pass

    current_order_id_datacenter = 1  # Пример ID текущего заказа

    current_order_datacenter = next((order for order in orders_datacenter if order['id'] == current_order_id_datacenter), None)
    if current_order_datacenter:
        total_quantity_datacenter = sum(item['quantity'] for item in current_order_datacenter['items'])
    else:
        total_quantity_datacenter = 0

    return render(request, 'datacenter_app/equipment_list_view_datacenter.html', {
        'equipment_list_datacenter': filtered_equipment_datacenter,
        'current_order_id_datacenter': current_order_id_datacenter,
        'equipment_count_in_order_datacenter': total_quantity_datacenter,
        'max_price_query': max_price_query,
    })

def equipment_detail_view_datacenter(request, equipment_id):
    equipment_datacenter = next((eq for eq in equipment_list_datacenter if eq['id'] == equipment_id), None)

    if not equipment_datacenter:
        raise Http404("Equipment not found")

    characteristics_list_datacenter = equipment_datacenter['characteristics'].split(',') if equipment_datacenter.get('characteristics') else []

    return render(request, 'datacenter_app/equipment_detail_view_datacenter.html', {
        'equipment_datacenter': equipment_datacenter,
        'characteristics_list_datacenter': characteristics_list_datacenter,
    })

def order_detail_view_datacenter(request, order_id_datacenter):
    selected_order_datacenter = next((order for order in orders_datacenter if order['id'] == order_id_datacenter), None)

    if selected_order_datacenter:
        equipment_in_order_datacenter = [
            {
                'equipment_datacenter': next(eq for eq in equipment_list_datacenter if eq['id'] == item['equipment_id']),
                'quantity_datacenter': item['quantity'],
                'total_price_datacenter': next(eq for eq in equipment_list_datacenter if eq['id'] == item['equipment_id'])['price'] * item['quantity']
            }
            for item in selected_order_datacenter['items']
        ]
        equipment_count_in_order_datacenter = sum(item['quantity'] for item in selected_order_datacenter['items'])
    else:
        equipment_in_order_datacenter = []
        equipment_count_in_order_datacenter = 0

    return render(request, 'datacenter_app/order_detail_view_datacenter.html', {
        'order_datacenter': selected_order_datacenter,
        'equipment_in_order_datacenter': equipment_in_order_datacenter,
        'equipment_count_in_order_datacenter': equipment_count_in_order_datacenter
    })