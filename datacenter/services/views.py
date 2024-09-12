from django.shortcuts import render, get_object_or_404
from datetime import datetime
# Пример данных
services = [
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



requests = [
    {'id': 1, 'date': datetime(2024, 9, 12, 12, 12, 30), 'address': 'Москва, ул. Мироновская, 25'},
    # другие заявки
]
    
# Привязка ID заявки к услугам
request_services_map = {
    1: [1, 2, 3],
    # другие привязки
}
def service_list(request):
    price_query = request.GET.get('price', '')  # Запрос по максимальной цене

    filtered_services = services
    if price_query:
        try:
            price_value = int(price_query)
            filtered_services = [s for s in filtered_services if s['price'] <= price_value]
        except ValueError:
            pass

    request_id = 1  # Пример ID заявки
    request_services_count = len(request_services_map.get(request_id, []))

    return render(request, 'services/service_list.html', {
        'services': filtered_services,
        'request_id': request_id,
        'request_services_count': request_services_count,
        'price_query': price_query,
    })

    
def service_detail(request, service_id):
    service = next((s for s in services if s['id'] == service_id), None)
    
    if not service:
        return get_object_or_404(service)

    characteristics_list = service['characteristics'].split(',') if service.get('characteristics') else []

    return render(request, 'services/service_detail.html', {
        'service': service,
        'characteristics_list': characteristics_list,
    })

def request_detail(request, request_id):
    user_request = next((r for r in requests if r['id'] == request_id), None)
    
    if user_request:
        request_service_ids = request_services_map.get(request_id, [])
        request_services = [s for s in services if s['id'] in request_service_ids]
        request_services_count = len(request_services)
    else:
        request_services = []
        request_services_count = 0

    return render(request, 'services/request_detail.html', {
        'request': user_request,
        'services': request_services,
        'request_services_count': request_services_count
    })