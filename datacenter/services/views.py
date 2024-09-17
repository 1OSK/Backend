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



equipment_requests = [
    {'id': 1,
     'date': datetime(2024, 9, 12, 12, 12, 30),
     'address': 'Москва, ул. Мироновская, 25'
     },
    
    # другие заявки
]
    
# Пример данных по заявкам с услугами и количеством
request_items = [
    {'request_id': 1, 'equipment_id': 1, 'quantity': 2},  # Заявка 1, Услуга 1, Кол-во 2
    {'request_id': 1, 'equipment_id': 2, 'quantity': 1},  # Заявка 1, Услуга 2, Кол-во 1
    {'request_id': 1, 'equipment_id': 3, 'quantity': 5},  # Заявка 1, Услуга 3, Кол-во 5
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

    request_id = 1  # Пример ID заявки

    # Фильтруем все записи, относящиеся к текущей заявке
    items_in_request = [item for item in request_items if item['request_id'] == request_id]
    
    # Подсчитываем общее количество всех предметов (включая дубликаты)
    total_quantity = sum(item['quantity'] for item in items_in_request)

    return render(request, 'services/equipment_list.html', {
        'equipment_list': filtered_equipment,
        'request_id': request_id,
        'equipment_count_in_request': total_quantity,  # Общее количество всех предметов
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
    
def request_detail_view(request, request_id):
    # Получаем заявку по её ID
    selected_request = next((req for req in equipment_requests if req['id'] == request_id), None)

    if selected_request:
        # Фильтруем все записи, относящиеся к текущей заявке
        items_in_request = [item for item in request_items if item['request_id'] == request_id]
        
        # Объединяем данные об оборудовании с количеством и вычисляем общую стоимость
        equipment_in_request = [
            {
                'equipment': next(eq for eq in equipment_list if eq['id'] == item['equipment_id']),
                'quantity': item['quantity'],
                'total_price': next(eq for eq in equipment_list if eq['id'] == item['equipment_id'])['price'] * item['quantity']
            }
            for item in items_in_request
        ]
        
        # Подсчитываем общее количество всех предметов (включая дубликаты)
        equipment_count_in_request = sum(item['quantity'] for item in items_in_request)
    else:
        equipment_in_request = []
        equipment_count_in_request = 0

    return render(request, 'services/request_detail_view.html', {
        'request': selected_request,
        'equipment_in_request': equipment_in_request,
        'equipment_count_in_request': equipment_count_in_request  # Общее количество всех предметов
    })