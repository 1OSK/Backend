
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
import re
from .minio import add_pic 
from django.conf import settings
from minio import Minio
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from .singleton import get_mock_user
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from .serializers import DatacenterServiceSerializer, DatacenterOrderSerializer, DatacenterOrderServiceSerializer, DatacenterServiceImageSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema



def get_current_user():
    """Получаем текущего пользователя (мокового пользователя)"""
    mock_user = get_mock_user()

    if not isinstance(mock_user, User):
        raise ValueError("Неверный пользователь")

    return mock_user


def get_filtered_queryset(queryset):
    """Фильтруем queryset, исключая товары со статусом 'deleted'"""
    return queryset.exclude(status='deleted')

@swagger_auto_schema(
    method='post',
    request_body=DatacenterServiceSerializer,
    responses={201: DatacenterServiceSerializer},
    operation_summary="Создать новый товар",
    operation_description="Создает новый товар в базе данных."
)
@api_view(['POST'])
def create_datacenter_service(request):
    serializer = DatacenterServiceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_datacenter_service = serializer.save()
    response_data = DatacenterServiceSerializer(new_datacenter_service).data
    return Response(response_data, status=status.HTTP_201_CREATED)

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'datacenter_min_price',
            openapi.IN_QUERY,
            description="Минимальная цена для фильтрации",
            type=openapi.TYPE_NUMBER,
            required=False,
        ),
        openapi.Parameter(
            'datacenter_max_price',
            openapi.IN_QUERY,
            description="Максимальная цена для фильтрации",
            type=openapi.TYPE_NUMBER,
            required=False,
        ),
    ],
    responses={
        200: DatacenterServiceSerializer(many=True),
        400: openapi.Response(
            description="Ошибка в параметрах запроса",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Описание ошибки")
                }
            )
        )
    },
    operation_summary="Получить список товаров",
    operation_description="Возвращает список товаров с фильтрацией по цене."
)
@api_view(['GET'])
def get_datacenter_service_list(request):
    try:
        mock_user = get_current_user()  # Используем внешнюю функцию
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    min_price = request.GET.get('datacenter_min_price')
    max_price = request.GET.get('datacenter_max_price')

    datacenter_services = get_filtered_queryset(DatacenterService.objects.all())  # Фильтруем queryset

    if min_price:
        try:
            min_price = float(min_price)
            datacenter_services = datacenter_services.filter(price__gte=min_price)
        except ValueError:
            return Response({"error": "Некорректное значение для минимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

    if max_price:
        try:
            max_price = float(max_price)
            datacenter_services = datacenter_services.filter(price__lte=max_price)
        except ValueError:
            return Response({"error": "Некорректное значение для максимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

    datacenter_draft_order = DatacenterOrder.objects.filter(creator=mock_user, status='draft').first()

    if datacenter_draft_order:
        datacenter_services_count = sum(datacenter_order_service.quantity for datacenter_order_service in datacenter_draft_order.datacenterorderservice_set.all())
        datacenter_draft_order_id = datacenter_draft_order.id
    else:
        datacenter_services_count = 0
        datacenter_draft_order_id = None

    datacenter_services_list = DatacenterServiceSerializer(datacenter_services, many=True).data

    response_data = {
        'datacenters': datacenter_services_list,
        'draft_order_id': datacenter_draft_order_id,
        'datacenters_count': datacenter_services_count
    }

    return Response(response_data)

@swagger_auto_schema(
    method='get',
    responses={200: DatacenterServiceSerializer},
    operation_summary="Получить товар по ID",
)
@api_view(['GET'])
def get_datacenter_service(request, pk):
    datacenter_service = get_object_or_404(DatacenterService.objects.all(), id=pk)
    datacenter_service_data = DatacenterServiceSerializer(datacenter_service).data
    return Response(datacenter_service_data)

@swagger_auto_schema(
    method='put',
    request_body=DatacenterServiceSerializer,
    responses={200: DatacenterServiceSerializer, 400: "Ошибка при обновлении"},
    operation_summary="Обновить товар",
)
@api_view(['PUT'])
def update_datacenter_service(request, pk):
    instance = get_object_or_404(DatacenterService.objects.all(), pk=pk)

    if instance.status == 'deleted':
        return Response({'error': 'Невозможно обновить удаленный товар.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DatacenterServiceSerializer(instance, data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        updated_datacenter_service = serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    responses={200: "Товар успешно удален", 400: "Ошибка при удалении"},
    operation_summary="Удалить товар",
)
@api_view(['DELETE'])
def delete_datacenter_service(request, pk):
    datacenter_service = get_object_or_404(DatacenterService.objects.all(), id=pk)

    if datacenter_service.status == 'deleted':
        return Response({'error': 'Этот товар уже был удален.'}, status=status.HTTP_400_BAD_REQUEST)

    if datacenter_service.image_url:
        client = Minio(
            endpoint=settings.AWS_S3_ENDPOINT_URL,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            secure=settings.MINIO_USE_SSL
        )
        try:
            client.remove_object('something', f"{datacenter_service.id}.png")
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    datacenter_service.status = 'deleted'
    datacenter_service.save()

    return Response({'message': 'Товар успешно удален'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    responses={201: DatacenterOrderSerializer, 400: "Ошибка при добавлении в черновик"},
    operation_summary="Добавить товар в черновик заказа",
)
@api_view(['POST'])
def add_to_draft(request, pk):
    datacenter_service = get_object_or_404(DatacenterService, id=pk)

    try:
        mock_user = get_current_user()  # Используем внешнюю функцию
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    datacenter_draft_order, created = DatacenterOrder.objects.get_or_create(
        creator=mock_user,
        status='draft'
    )

    datacenter_order_service, created = DatacenterOrderService.objects.get_or_create(
        order=datacenter_draft_order,
        service=datacenter_service,
        defaults={'quantity': 0}
    )

    if created:
        datacenter_order_service.quantity = 1
    else:
        datacenter_order_service.quantity += 1

    datacenter_order_service.save()

    datacenter_draft_order.total_price = sum(
        datacenter_order_service.quantity * datacenter_order_service.service.price
        for datacenter_order_service in datacenter_draft_order.datacenterorderservice_set.all()
    )
    datacenter_draft_order.save()

    datacenter_services_count = sum(datacenter_order_service.quantity for datacenter_order_service in datacenter_draft_order.datacenterorderservice_set.all())

    serializer = DatacenterOrderSerializer(datacenter_draft_order)

    return Response(
        {
            'message': 'Товар добавлен в черновик заказа',
            'draft_order': serializer.data,
            'datacenters_count': datacenter_services_count
        },
        status=status.HTTP_201_CREATED
    )


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'image': openapi.Schema(type=openapi.TYPE_FILE, description='Изображение для добавления')
        }
    ),
    responses={200: DatacenterServiceImageSerializer, 400: "Ошибка при добавлении изображения"},
    operation_summary="Добавить изображение к товару",
)
@api_view(['POST'])
def add_image(request, pk):
    datacenter_service = get_object_or_404(DatacenterService.objects.all(), id=pk)

    if datacenter_service.status == 'deleted':
        return Response({'error': 'Нельзя добавлять изображение к удаленному товару.'}, status=400)

    if 'image' not in request.FILES:
        return Response({'error': 'Изображение не предоставлено'}, status=400)

    image = request.FILES['image']
    result = add_pic(datacenter_service, image)

    if 'error' in result:
        return Response({'error': result['error']}, status=400)

    datacenter_service.image_url = result['image_url']
    datacenter_service.save()

    serializer = DatacenterServiceImageSerializer(datacenter_service)

    return Response({
        'message': 'Изображение успешно добавлено или обновлено',
        'service': serializer.data
    }, status=200)



 # 1. GET /orders/ - Получение списка заказов
@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('datacenter_status', openapi.IN_QUERY, description="Фильтр по статусу заказа", type=openapi.TYPE_STRING),
        openapi.Parameter('datacenter_start_date', openapi.IN_QUERY, description="Начальная дата", type=openapi.TYPE_STRING),
        openapi.Parameter('datacenter_end_date', openapi.IN_QUERY, description="Конечная дата", type=openapi.TYPE_STRING)
    ],
    responses={200: DatacenterOrderSerializer(many=True), 400: "Ошибка в запросе"},
    operation_summary="Получить список заказов",
    operation_description="Возвращает список заказов с фильтрацией по статусу и дате создания."
)
@api_view(['GET'])
def list_orders(request):
    status_filter = request.GET.get('datacenter_status')
    start_date = request.GET.get('datacenter_start_date')
    end_date = request.GET.get('datacenter_end_date')

    datacenter_orders = DatacenterOrder.objects.exclude(status__in=['deleted', 'draft'])

    if status_filter:
        datacenter_orders = datacenter_orders.filter(status=status_filter)

    if start_date and end_date:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            datacenter_orders = datacenter_orders.filter(creation_date__range=[start_date, end_date])
        except ValueError:
            return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DatacenterOrderSerializer(datacenter_orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 2. GET /orders/{id}/ - Получение конкретной заявки
@swagger_auto_schema(
    method='get',
    responses={200: DatacenterOrderSerializer(), 404: "Заказ не найден"},
    operation_summary="Получить заказ",
    operation_description="Возвращает информацию о конкретном заказе по его ID."
)
@api_view(['GET'])
def retrieve_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DatacenterOrderSerializer(datacenter_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 3. DELETE /orders/{id}/ - Удаление заявки
@swagger_auto_schema(
    method='delete',
    responses={204: "Заказ удалён", 404: "Заказ не найден", 400: "Невозможно удалить"},
    operation_summary="Удалить заказ",
    operation_description="Помечает заказ как удалённый."
)
@api_view(['DELETE'])
def delete_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ уже удалён.'}, status=status.HTTP_400_BAD_REQUEST)

    datacenter_order.status = 'deleted'
    datacenter_order.save()

    return Response({'message': 'Заказ успешно удалён.'}, status=status.HTTP_204_NO_CONTENT)


# 4. PUT /orders/{id}/submit/ - Подтверждение заявки
@swagger_auto_schema(
    method='put',
    responses={200: "Заказ подтверждён", 404: "Заказ не найден", 400: "Ошибка подтверждения"},
    operation_summary="Подтвердить заказ",
    operation_description="Подтверждает заказ по его ID."
)
@api_view(['PUT'])
def submit_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status != 'draft':
        return Response({'error': 'Заказ уже был отправлен или не может быть отправлен.'}, status=status.HTTP_400_BAD_REQUEST)

    delivery_address = datacenter_order.delivery_address
    delivery_time = datacenter_order.delivery_time

    if not delivery_address:
        return Response({'error': 'Адрес доставки не указан в заявке.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not delivery_time:
        return Response({'error': 'Время доставки не указано в заявке.'}, status=status.HTTP_400_BAD_REQUEST)

    datacenter_order.status = 'formed'
    datacenter_order.formation_date = timezone.now()
    datacenter_order.save()

    serializer = DatacenterOrderSerializer(datacenter_order)
    return Response({'message': 'Заказ подтверждён успешно', 'datacenter_order': serializer.data}, status=status.HTTP_200_OK)


# 5. PUT /orders/{id}/finalize/ - Завершение или отклонение заявки
@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'action': openapi.Schema(type=openapi.TYPE_STRING, description="Действие: completed или rejected")
        },
        required=['action']
    ),
    responses={200: "Заявка завершена", 400: "Ошибка завершения", 403: "Нет прав"},
    operation_summary="Завершить или отклонить заказ",
    operation_description="Завершает или отклоняет заказ по его ID."
)
@api_view(['PUT'])
def finalize_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ удален и не может быть завершен.'}, status=status.HTTP_400_BAD_REQUEST)

    action = request.data.get('action')

    if not action or action not in ['completed', 'rejected']:
        return Response({'error': 'Некорректное действие.'}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'completed':
        datacenter_order.status = 'completed'
        datacenter_order.completion_date = timezone.now()
    elif action == 'rejected':
        datacenter_order.status = 'rejected'
        datacenter_order.completion_date = timezone.now()

    datacenter_order.save()
    return Response({'message': f'Заявка успешно {action}.'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    request_body=DatacenterOrderSerializer,
    responses={
        200: "Заказ обновлен",
        404: "Заказ не найден",
        400: "Ошибка обновления"
    },
    operation_summary="Изменить заказ",
    operation_description="Обновляет данные заказа по его ID."
)
@api_view(['PUT'])
def update_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Обновление удалённых заказов невозможно.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DatacenterOrderSerializer(datacenter_order, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Заказ обновлён успешно', 'data': serializer.data}, status=status.HTTP_200_OK)

    # Отладочная информация
    print(serializer.errors)  # Печатаем ошибки в консоль
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# DELETE: Удаление услуги из заказа
@swagger_auto_schema(
    method='delete',
    operation_description="Удаление товара из заказа",
    responses={
        200: 'Количество товаров уменьшено на 1',
        204: 'Товар удален из заказа',
        400: 'Заказ удален, нельзя удалить товары',
        404: 'Товар не найден в заказе',
    }
)
@api_view(['DELETE'])
def delete_service_from_order(request, datacenter_order_id, datacenter_service_id):
    datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ удален, нельзя удалить товар'}, status=status.HTTP_400_BAD_REQUEST)

    datacenter_service = get_object_or_404(DatacenterService, id=datacenter_service_id)

    datacenter_order_service = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter_service).first()

    if datacenter_order_service:
        if datacenter_order_service.quantity > 1:
            datacenter_order_service.quantity -= 1
            datacenter_order_service.save()
            return Response({'message': 'Количество товаров уменьшено на 1'}, status=status.HTTP_200_OK)
        else:
            datacenter_order_service.delete()
            return Response({'message': 'Товар удален из заказа'}, status=status.HTTP_204_NO_CONTENT)

    return Response({'error': 'Товар не найден в заказе'}, status=status.HTTP_404_NOT_FOUND)


# PUT: Изменение количества услуги в заказе
@swagger_auto_schema(
    method='put',
    operation_description="Изменение количества товаров в заказе",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Новое количество товаров')
        },
        required=['quantity']
    ),
    responses={
        200: 'Количество товаров обновлено в заказе',
        400: 'Некорректное количество или другое сообщение об ошибке',
        404: 'Товар не найден в заказе',
    }
)
@api_view(['PUT'])
def update_service_quantity_in_order(request, datacenter_order_id, datacenter_service_id):
    datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)
    datacenter_service = get_object_or_404(DatacenterService, id=datacenter_service_id)

    datacenter_order_service = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter_service).first()

    if datacenter_order_service:
        data = request.data
        new_quantity = data.get('quantity')

        if new_quantity is None:
            return Response({'error': 'Не указано количество'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_quantity = int(new_quantity)
            if new_quantity < 1:
                return Response({'error': 'Количество должно быть положительным'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Некорректное количество'}, status=status.HTTP_400_BAD_REQUEST)

        datacenter_order_service.quantity = new_quantity
        datacenter_order_service.save()
        return Response({'message': 'Количество товаров обновлено в заказе'}, status=status.HTTP_200_OK)

    return Response({'error': 'Товар не найден в заказе'}, status=status.HTTP_404_NOT_FOUND)

# POST: Регистрация пользователя
@swagger_auto_schema(
    method='post',
    operation_description="Регистрация пользователя",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email адрес'),
        },
        required=['username', 'password', 'email'],
    ),
    responses={
        201: openapi.Response(description='Пользователь успешно зарегистрирован'),
        400: openapi.Response(description='Ошибка валидации'),
    },
)
@api_view(['POST'])
def register_user(request):
    data = request.data
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Пользователь с таким именем уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return Response({'error': 'Неверный формат email'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password, email=email)
    return Response({'message': 'Пользователь успешно зарегистрирован'}, status=status.HTTP_201_CREATED)

# PUT: Обновление информации о пользователе
@swagger_auto_schema(
    method='put',
    operation_description="Обновление информации о пользователе",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email адрес'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль'),
        },
        required=[],
    ),
    responses={
        200: openapi.Response(description='Информация о пользователе успешно обновлена'),
        404: openapi.Response(description='Пользователь не найден'),
    },
)
@api_view(['PUT'])
def update_user(request, pk):
    user = get_object_or_404(User, id=pk)
    data = request.data

    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    if 'password' in data:
        user.set_password(data['password'])
    user.save()

    return Response({'message': 'Информация о пользователе успешно обновлена'}, status=status.HTTP_200_OK)

# POST: Вход пользователя
@swagger_auto_schema(
    method='post',
    operation_description="Вход пользователя",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль'),
        },
        required=['username', 'password'],
    ),
    responses={
        200: openapi.Response(description='Пользователь успешно вошел в систему'),
        401: openapi.Response(description='Неверное имя пользователя или пароль'),
    },
)
@api_view(['POST'])
def login_user(request):
    data = request.data
    username = data.get('username')
    password = data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({'message': 'Пользователь успешно вошел в систему'}, status=status.HTTP_200_OK)
    return Response({'error': 'Неверное имя пользователя или пароль'}, status=status.HTTP_401_UNAUTHORIZED)

# POST: Выход пользователя
@swagger_auto_schema(
    method='post',
    operation_description="Выход пользователя",
    responses={
        200: openapi.Response(description='Пользователь успешно вышел из системы'),
    },
)
@api_view(['POST'])
def logout_user(request):
    logout(request)
    return Response({'message': 'Пользователь успешно вышел из системы'}, status=status.HTTP_200_OK)