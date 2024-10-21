
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
import logging
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from .serializers import DatacenterServiceSerializer, DatacenterOrderSerializer, DatacenterOrderServiceSerializer, DatacenterServiceImageSerializer, LoginSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from .models import CustomUser
from .serializers import UserSerializer
from rest_framework.decorators import authentication_classes
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from .permissions import IsManagerOrAdmin, IsAdmin, IsManager, IsAuthenticatedAndManagerOrOwnOrders
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
def get_current_user(request):
    """Получаем текущего пользователя"""
    
    # Проверяем, аутентифицирован ли пользователь
    if isinstance(request.user, AnonymousUser):
        raise AuthenticationFailed("Пользователь не аутентифицирован")

    # Получаем модель пользователя через get_user_model
    CustomUser = get_user_model()

    # Проверяем, что текущий пользователь является экземпляром кастомной модели
    if not isinstance(request.user, CustomUser):
        raise ValueError("Неверный пользователь")

    return request.user


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
@permission_classes([IsAdmin])
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
@permission_classes([AllowAny])
def get_datacenter_service_list(request):
    # Проверяем, аутентифицирован ли пользователь
    user = request.user if request.user.is_authenticated else None

    # Получаем параметры фильтрации
    min_price = request.GET.get('datacenter_min_price')
    max_price = request.GET.get('datacenter_max_price')

    # Получаем и фильтруем queryset
    datacenter_services = get_filtered_queryset(DatacenterService.objects.all())  # Фильтруем queryset

    # Фильтрация по минимальной цене
    if min_price:
        try:
            min_price = float(min_price)
            datacenter_services = datacenter_services.filter(price__gte=min_price)
        except ValueError:
            return Response({"error": "Некорректное значение для минимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

    # Фильтрация по максимальной цене
    if max_price:
        try:
            max_price = float(max_price)
            datacenter_services = datacenter_services.filter(price__lte=max_price)
        except ValueError:
            return Response({"error": "Некорректное значение для максимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

    # Инициализируем переменные для черновика
    datacenter_draft_order_id = None
    datacenter_services_count = 0

    # Если пользователь аутентифицирован, проверяем наличие черновика
    if user:
        datacenter_draft_order = DatacenterOrder.objects.filter(creator=user, status='draft').first()
        if datacenter_draft_order:
            datacenter_services_count = sum(
                datacenter_order_service.quantity for datacenter_order_service in datacenter_draft_order.datacenterorderservice_set.all()
            )
            datacenter_draft_order_id = datacenter_draft_order.id

    # Сериализуем список услуг датацентра
    datacenter_services_list = DatacenterServiceSerializer(datacenter_services, many=True).data

    # Формируем ответ
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
@permission_classes([AllowAny])  # Разрешаем доступ любому пользователю
def get_datacenter_service(request, pk):
    # Получаем товар или возвращаем 404, если его нет
    datacenter_service = get_object_or_404(DatacenterService.objects.all(), id=pk)
    
    # Сериализуем данные
    datacenter_service_data = DatacenterServiceSerializer(datacenter_service).data
    
    # Возвращаем ответ
    return Response(datacenter_service_data)

@swagger_auto_schema(
    method='put',
    request_body=DatacenterServiceSerializer,
    responses={200: DatacenterServiceSerializer, 400: "Ошибка при обновлении"},
    operation_summary="Обновить товар",
)
@api_view(['PUT'])
@permission_classes([IsAdmin])
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
@permission_classes([IsAdmin])
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
@permission_classes([AllowAny])
def add_to_draft(request, pk):
    datacenter_service = get_object_or_404(DatacenterService, id=pk)

    # Проверяем, авторизован ли пользователь
    if not request.user.is_authenticated:
        return Response(
            {"error": "Пожалуйста, авторизуйтесь, чтобы добавить товар в корзину."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    mock_user = request.user  # Получаем текущего пользователя

    # Создаем или получаем черновик для данного пользователя
    datacenter_draft_order, created = DatacenterOrder.objects.get_or_create(
        creator=mock_user,
        status='draft'
    )

    # Создаем или обновляем услугу в черновике
    datacenter_order_service, created = DatacenterOrderService.objects.get_or_create(
        order=datacenter_draft_order,
        service=datacenter_service,
        defaults={'quantity': 0}
    )

    if created:
        # Если создаем новую запись, устанавливаем количество на 1
        datacenter_order_service.quantity = 1
    else:
        # Если запись уже существует, увеличиваем количество на 1
        datacenter_order_service.quantity += 1

    datacenter_order_service.save()

    # Обновляем общую стоимость черновика
    datacenter_draft_order.total_price = sum(
        datacenter_order_service.quantity * datacenter_order_service.service.price
        for datacenter_order_service in datacenter_draft_order.datacenterorderservice_set.all()
    )
    datacenter_draft_order.save()

    # Подсчитываем количество услуг в черновике
    datacenter_services_count = sum(datacenter_order_service.quantity for datacenter_order_service in datacenter_draft_order.datacenterorderservice_set.all())

    # Сериализуем черновик
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
@permission_classes([IsAdmin])
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
@permission_classes([IsAuthenticatedAndManagerOrOwnOrders])  # Проверка прав доступа
def list_orders(request):
    status_filter = request.GET.get('datacenter_status')
    start_date = request.GET.get('datacenter_start_date')
    end_date = request.GET.get('datacenter_end_date')

    # Начинаем с всех заказов, исключая удаленные и черновики
    datacenter_orders = DatacenterOrder.objects.exclude(status__in=['deleted', 'draft'])

    # Если пользователь не менеджер, фильтруем заказы по пользователю
    if not request.user.is_staff and not request.user.is_superuser:
        datacenter_orders = datacenter_orders.filter(creator=request.user)

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

@swagger_auto_schema(
    method='get',
    responses={200: DatacenterOrderSerializer(), 404: "Заказ не найден"},
    operation_summary="Получить заказ",
    operation_description="Возвращает информацию о конкретном заказе по его ID."
)
@api_view(['GET'])
@permission_classes([IsAuthenticatedAndManagerOrOwnOrders])  # Проверка прав доступа
def retrieve_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

    # Проверка прав доступа
    if request.user.is_staff or request.user.is_superuser:
        # Менеджер или администратор может видеть любой заказ
        serializer = DatacenterOrderSerializer(datacenter_order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # Если пользователь не менеджер, проверяем, принадлежит ли заказ пользователю
    if datacenter_order.creator != request.user:
        return Response({'error': 'У вас нет прав на просмотр этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = DatacenterOrderSerializer(datacenter_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='delete',
    responses={204: "Заказ удалён", 404: "Заказ не найден", 400: "Невозможно удалить"},
    operation_summary="Удалить заказ",
    operation_description="Помечает заказ как удалённый."
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticatedAndManagerOrOwnOrders])  # Проверка прав доступа
def delete_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ уже удалён.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверка прав доступа
    if request.user.is_staff or request.user.is_superuser:
        # Менеджер или администратор может удалить заказ
        datacenter_order.status = 'deleted'
        datacenter_order.save()
        return Response({'message': 'Заказ успешно удалён.'}, status=status.HTTP_204_NO_CONTENT)

    # Проверяем, принадлежит ли заказ пользователю
    if datacenter_order.creator != request.user:
        return Response({'error': 'У вас нет прав на удаление этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    # Если это пользователь-владелец заказа, то удаляем его
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
@permission_classes([IsAuthenticated])  # Проверка на аутентификацию
def submit_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status != 'draft':
        return Response({'error': 'Заказ уже был отправлен или не может быть отправлен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверка, является ли текущий пользователь создателем заказа
    if datacenter_order.creator != request.user:
        return Response({'error': 'У вас нет прав на подтверждение этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    delivery_address = datacenter_order.delivery_address
    delivery_time = datacenter_order.delivery_time

    if not delivery_address:
        return Response({'error': 'Адрес доставки не указан в заявке.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not delivery_time:
        return Response({'error': 'Время доставки не указано в заявке.'}, status=status.HTTP_400_BAD_REQUEST)

    # Изменяем статус заказа на 'formed'
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
@permission_classes([IsManager]) 
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
@permission_classes([IsAuthenticatedAndManagerOrOwnOrders])  # Проверка прав доступа
def update_order(request, pk):
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Обновление удалённых заказов невозможно.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем права доступа
    if request.user.is_staff or request.user.is_superuser:
        # Менеджер или администратор может обновить заказ
        serializer = DatacenterOrderSerializer(datacenter_order, data=request.data, partial=True)
    elif datacenter_order.creator == request.user:
        # Владелец заказа может обновить только свой заказ
        serializer = DatacenterOrderSerializer(datacenter_order, data=request.data, partial=True)
    else:
        return Response({'error': 'У вас нет прав на обновление этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Заказ обновлён успешно', 'data': serializer.data}, status=status.HTTP_200_OK)

    # Отладочная информация
    print(serializer.errors)  # Печатаем ошибки в консоль
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
@permission_classes([IsAuthenticatedAndManagerOrOwnOrders])  # Проверка прав доступа
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
@permission_classes([IsAuthenticatedAndManagerOrOwnOrders])  # Проверка прав доступа
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



logger = logging.getLogger(__name__)

User = get_user_model()

'''@api_view(['GET'])
@permission_classes([IsManagerOrAdmin])  # Доступ только для менеджеров и администраторов
def list_users(request):
    users = User.objects.all()  # Получаем всех пользователей
    serializer = UserSerializer(users, many=True)  # Сериализуем пользователей
    return Response(serializer.data, status=status.HTTP_200_OK)'''


@swagger_auto_schema(
    method='post',
    request_body=UserSerializer,
    responses={
        201: openapi.Response('Пользователь успешно зарегистрирован', 
                              schema=openapi.Schema(type=openapi.TYPE_OBJECT, 
                                                    properties={
                                                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
                                                        'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Является ли пользователь менеджером'),
                                                        'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Является ли пользователь администратором'),
                                                    })),
        400: 'Ошибка валидации данных'
    },
    operation_summary="Регистрация пользователя",
    operation_description="Создает нового пользователя с указанными данными."
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Для регистрации без аутентификации
def create_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                "email": user.email,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль пользователя'),
        },
        required=['email', 'password']
    ),
    responses={
        200: openapi.Response('Успешный вход', 
                              schema=openapi.Schema(type=openapi.TYPE_OBJECT, 
                                                    properties={'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя')})),
        401: 'Неверный email или пароль.'
    },
    operation_summary="Вход пользователя",
    operation_description="Аутентификация пользователя по email и паролю."
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Для входа без ограничений
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')

    logger.info(f"Attempting login with email: {email}")  # Логирование
    user = authenticate(request, email=email, password=password)
    if user is not None:
        logger.info(f"Login successful for email: {email}")  # Логирование успешного входа
        return Response({'email': user.email}, status=status.HTTP_200_OK)
    
    logger.warning(f"Login failed for email: {email}")  # Логирование
    return Response({'detail': 'Invalid email/password.'}, status=status.HTTP_401_UNAUTHORIZED)



@swagger_auto_schema(
    method='post',
    responses={
        200: 'Успешный выход из системы'
    },
    operation_summary="Выход пользователя",
    operation_description="Разлогинивает пользователя."
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Доступ только для менеджеров и администраторов
def logout_user(request):
    logout(request)
    return Response({'status': 'Success'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    request_body=UserSerializer,
    responses={
        200: 'Информация о пользователе успешно обновлена',
        404: 'Пользователь не найден.',
        400: 'Ошибка валидации данных'
    },
    operation_summary="Обновление информации о пользователе",
    operation_description="Частично обновляет данные пользователя по его ID."
)
@api_view(['PUT'])
@permission_classes([IsManagerOrAdmin])  # Доступ только для менеджеров и администраторов
def update_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)  # Получаем пользователя по ID
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user, data=request.data, partial=True)  # Частичное обновление
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Информация о пользователе успешно обновлена'}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)