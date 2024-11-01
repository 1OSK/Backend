
from sqlite3 import IntegrityError
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
from .serializers import DatacenterServiceSerializer, DatacenterOrderSerializer, DatacenterOrderServiceSerializer, DatacenterServiceImageSerializer, LoginSerializer, RegisterSerializer
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

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import redis
from django.contrib.auth import authenticate, login


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .redis import redis_client 



from rest_framework.exceptions import AuthenticationFailed



from rest_framework.exceptions import AuthenticationFailed
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import DatacenterOrder
from .serializers import DatacenterOrderSerializer
from django.utils import timezone







session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

redis_client = redis.StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)




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
  # Проверяем, что пользователь аутентифицирован
def create_datacenter_service(request):
    # Извлечение sessionid из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        return Response({'error': 'sessionid не предоставлен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Извлечение ID пользователя из Redis
    user_id = redis_client.get(session_id)

    if user_id is None:
        return Response({'error': 'Неверный sessionid или сессия истекла.'}, status=status.HTTP_403_FORBIDDEN)

    # Получение текущего пользователя
    user = get_object_or_404(CustomUser, id=user_id)

    # Проверяем, является ли пользователь администратором
    if not user.is_staff:
        return Response({'error': 'Доступ запрещен. Необходимы права администратора.'}, status=status.HTTP_403_FORBIDDEN)

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
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')  # Изменено на 'sessionid'

    # Инициализируем переменные для черновика
    datacenter_draft_order_id = None
    datacenter_services_count = 0

    # Проверяем, есть ли session_id в хранилище Redis и извлекаем user_id
    if session_id:
        user_id = redis_client.get(session_id)

        if user_id:
            # Удаляем вызов decode, так как user_id уже является строкой
            user_id = user_id  # Просто присваиваем user_id как есть

            # Если пользователь аутентифицирован (по наличию записи в Redis)
            # Ищем черновой заказ для этого пользователя
            datacenter_draft_order = DatacenterOrder.objects.filter(creator_id=user_id, status='draft').first()

            if datacenter_draft_order:
                datacenter_services_count = sum(
                    service.quantity for service in datacenter_draft_order.datacenterorderservice_set.all()
                )
                datacenter_draft_order_id = datacenter_draft_order.id

    # Получаем параметры фильтрации
    min_price = request.GET.get('datacenter_min_price')
    max_price = request.GET.get('datacenter_max_price')

    # Получаем и фильтруем queryset
    datacenter_services = DatacenterService.objects.all()

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

    # Сериализуем список услуг датацентра
    datacenter_services_list = DatacenterServiceSerializer(datacenter_services, many=True).data

    # Формируем ответ
    response_data = {
        'datacenters': datacenter_services_list,
        'draft_order_id': datacenter_draft_order_id,
        'datacenters_count': datacenter_services_count
    }

    return Response(response_data, status=status.HTTP_200_OK)

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
@permission_classes([AllowAny])  # Ставим AllowAny, так как проверка прав будет вручную
def update_datacenter_service(request, pk):
    # Извлекаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        return Response({'error': 'sessionid не предоставлен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Извлекаем ID пользователя из Redis
    user_id = redis_client.get(session_id)
    if user_id is None:
        return Response({'error': 'Неверный sessionid или сессия истекла.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем пользователя по user_id
    user = get_object_or_404(CustomUser, id=user_id)

    # Проверяем, является ли пользователь администратором
    if not user.is_staff:
        return Response({'error': 'Доступ запрещен. Необходимы права администратора.'}, status=status.HTTP_403_FORBIDDEN)

    # Проверяем, что товар с таким pk существует и его статус не "удален"
    instance = get_object_or_404(DatacenterService.objects.all(), pk=pk)
    if instance.status == 'deleted':
        return Response({'error': 'Невозможно обновить удаленный товар.'}, status=status.HTTP_400_BAD_REQUEST)

    # Обновляем товар с новыми данными
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
@permission_classes([AllowAny])  # Проверка прав будет выполняться вручную
def delete_datacenter_service(request, pk):
    # Извлекаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        return Response({'error': 'sessionid не предоставлен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Извлекаем ID пользователя из Redis
    user_id = redis_client.get(session_id)
    if user_id is None:
        return Response({'error': 'Неверный sessionid или сессия истекла.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем пользователя по user_id
    user = get_object_or_404(CustomUser, id=user_id)

    # Проверяем, является ли пользователь администратором
    if not user.is_staff:
        return Response({'error': 'Доступ запрещен. Необходимы права администратора.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем товар по его ID
    datacenter_service = get_object_or_404(DatacenterService.objects.all(), id=pk)

    # Проверяем, не был ли товар уже удален
    if datacenter_service.status == 'deleted':
        return Response({'error': 'Этот товар уже был удален.'}, status=status.HTTP_400_BAD_REQUEST)

    # Если у товара есть изображение, удаляем его из хранилища Minio
    if datacenter_service.image_url:
        client = Minio(
            endpoint=settings.AWS_S3_ENDPOINT_URL.replace('http://', '').replace('https://', ''),  # Удаляем 'http://' или 'https://'
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            secure=settings.MINIO_USE_SSL
        )
        try:
            client.remove_object(settings.AWS_STORAGE_BUCKET_NAME, f"{datacenter_service.id}.png")
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Обновляем статус товара на "deleted"
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
    # Извлечение sessionid из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        return Response(
            {"error": "sessionid не предоставлен."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Извлечение ID пользователя из Redis
    user_id = redis_client.get(session_id)
    
    if user_id is None:
        return Response(
            {"error": "Неверный sessionid или сессия истекла."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Получение текущего пользователя
    user = get_object_or_404(CustomUser, id=user_id)

    # Получение услуги по переданному ID
    datacenter_service = get_object_or_404(DatacenterService, id=pk)

    # Получаем или создаем черновик для текущего пользователя
    datacenter_draft_order, created = DatacenterOrder.objects.get_or_create(
        creator=user,
        status='draft',
        defaults={'total_price': 0}  # Устанавливаем начальную цену
    )

    # Создаем или обновляем услугу в черновике
    datacenter_order_service, created = DatacenterOrderService.objects.get_or_create(
        order=datacenter_draft_order,
        service=datacenter_service,
        defaults={'quantity': 0}
    )

    # Обновляем количество товара
    if created:
        datacenter_order_service.quantity = 1  # Устанавливаем количество на 1
    else:
        datacenter_order_service.quantity += 1  # Увеличиваем количество на 1

    datacenter_order_service.save()

    # Обновляем общую стоимость черновика
    datacenter_draft_order.total_price = sum(
        service.quantity * service.service.price
        for service in datacenter_draft_order.datacenterorderservice_set.all()
    )
    datacenter_draft_order.save()

    # Сериализуем черновик
    serializer = DatacenterOrderSerializer(datacenter_draft_order)

    return Response(
        {
            'message': 'Товар добавлен в черновик заказа',
            'draft_order': serializer.data
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
@permission_classes([AllowAny])  # Проверка прав выполняется вручную
def add_image(request, pk):
    # Извлечение session_id из куки
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        return Response({'error': 'sessionid не предоставлен.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Получение user_id из Redis
        user_id = redis_client.get(session_id)
        if user_id is None:
            return Response({'error': 'Неверный sessionid или сессия истекла.'}, status=status.HTTP_403_FORBIDDEN)

        # Получение пользователя
        user = get_object_or_404(CustomUser, id=user_id)

        # Проверка, является ли пользователь администратором
        if not user.is_staff:
            return Response({'error': 'Доступ запрещен. Необходимы права администратора.'}, status=status.HTTP_403_FORBIDDEN)

        # Получение товара
        datacenter_service = get_object_or_404(DatacenterService.objects.all(), id=pk)

        # Проверка статуса товара
        if datacenter_service.status == 'deleted':
            return Response({'error': 'Нельзя добавлять изображение к удаленному товару.'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка наличия изображения в запросе
        if 'image' not in request.FILES:
            return Response({'error': 'Изображение не предоставлено'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка формата изображения
        image = request.FILES['image']
        if not image.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            return Response({'error': 'Неподдерживаемый формат изображения. Поддерживаются PNG и JPG.'}, status=status.HTTP_400_BAD_REQUEST)

        # Загрузка изображения
        result = add_pic(datacenter_service, image)
        if 'error' in result:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        # Сохранение URL изображения в записи товара
        datacenter_service.image_url = result['image_url']
        datacenter_service.save()

        # Сериализация данных
        serializer = DatacenterServiceImageSerializer(datacenter_service)

        return Response({
            'message': 'Изображение успешно добавлено или обновлено',
            'service': serializer.data
        }, status=status.HTTP_200_OK)

    except redis.exceptions.ConnectionError:
        return Response({'error': 'Ошибка подключения к Redis'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        # Логирование ошибки для отладки
        print(f"Ошибка при добавлении изображения: {str(e)}")
        return Response({'error': 'Произошла внутренняя ошибка сервера.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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
    # Извлекаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        return Response({'error': 'sessionid не предоставлен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Извлекаем ID пользователя из Redis
    user_id = redis_client.get(session_id)
    if user_id is None:
        return Response({'error': 'Неверный sessionid или сессия истекла.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем пользователя по user_id
    user = get_object_or_404(CustomUser, id=user_id)

    # Фильтры
    status_filter = request.GET.get('datacenter_status')
    start_date = request.GET.get('datacenter_start_date')
    end_date = request.GET.get('datacenter_end_date')

    # Начинаем с всех заказов, исключая удаленные и черновики
    datacenter_orders = DatacenterOrder.objects.exclude(status__in=['deleted', 'draft'])

    # Если пользователь не менеджер или администратор, фильтруем заказы по пользователю
    if not user.is_staff and not user.is_superuser:
        datacenter_orders = datacenter_orders.filter(creator_id=user.id)

    # Фильтрация по статусу
    if status_filter:
        datacenter_orders = datacenter_orders.filter(status=status_filter)

    # Фильтрация по дате
    if start_date and end_date:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            datacenter_orders = datacenter_orders.filter(creation_date__range=[start_date, end_date])
        except ValueError:
            return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    # Сериализуем результат
    serializer = DatacenterOrderSerializer(datacenter_orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)




@swagger_auto_schema(
    method='get',
    responses={200: DatacenterOrderSerializer(), 404: "Заказ не найден"},
    operation_summary="Получить заказ",
    operation_description="Возвращает информацию о конкретном заказе по его ID."
)
@api_view(['GET'])
@permission_classes([AllowAny])  # Внешний доступ проверяется через сессии и права
def retrieve_order(request, pk):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')  # Обратите внимание на правильное имя куки

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы просматривать заказы.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    # Проверяем статус заказа
    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

    # Проверка прав доступа
    if request.user.is_staff or request.user.is_superuser:
        # Менеджер или администратор может видеть любой заказ
        serializer = DatacenterOrderSerializer(datacenter_order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Если пользователь не менеджер, проверяем, принадлежит ли заказ пользователю
    if str(datacenter_order.creator_id) != user_id:
        return Response({'error': 'У вас нет прав на просмотр этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    # Сериализуем заказ и возвращаем данные
    serializer = DatacenterOrderSerializer(datacenter_order)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='delete',
    responses={204: "Заказ удалён", 404: "Заказ не найден", 400: "Невозможно удалить"},
    operation_summary="Удалить заказ",
    operation_description="Помечает заказ как удалённый."
)
@api_view(['DELETE'])
@permission_classes([AllowAny])  # Позволяем доступ, но проверяем права в функции
def delete_order(request, pk):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы удалять заказы.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    # Проверяем статус заказа
    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ уже удалён.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверка прав доступа: только создатель заказа может его удалить
    if str(datacenter_order.creator_id) != user_id:
        return Response({'error': 'У вас нет прав на удаление этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    # Если это пользователь-владелец заказа, помечаем его как удалённый
    datacenter_order.status = 'deleted'
    datacenter_order.save()

    return Response({'message': 'Заказ успешно удалён.'}, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='put',
    responses={200: "Заказ подтверждён", 404: "Заказ не найден", 400: "Ошибка подтверждения"},
    operation_summary="Подтвердить заказ",
    operation_description="Подтверждает заказ по его ID."
)
@api_view(['PUT'])
@permission_classes([AllowAny])  # Внешняя проверка на уровне сессий
def submit_order(request, pk):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы подтвердить заказ.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    # Проверка, является ли текущий пользователь создателем заказа
    if str(datacenter_order.creator_id) != user_id:
        return Response({'error': 'У вас нет прав на подтверждение этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    if datacenter_order.status != 'draft':
        return Response({'error': 'Заказ уже был отправлен или не может быть отправлен.'}, status=status.HTTP_400_BAD_REQUEST)

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
@permission_classes([AllowAny])  # Внешняя проверка на уровне сессий
def finalize_order(request, pk):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы завершить или отклонить заказ.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')

    # Получаем текущего пользователя
    user = get_object_or_404(User, id=user_id)

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    if datacenter_order.status == 'deleted':
        return Response({'error': 'Заказ удален и не может быть завершен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Получаем действие из тела запроса
    action = request.data.get('action')

    if not action or action not in ['completed', 'rejected']:
        return Response({'error': 'Некорректное действие.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, является ли пользователь суперпользователем
    if not user.is_superuser:
        return Response({'error': 'У вас нет прав для выполнения этого действия.'}, status=status.HTTP_403_FORBIDDEN)

    # Обработка завершения или отклонения заявки
    if action == 'completed':
        datacenter_order.status = 'completed'
        datacenter_order.completion_date = timezone.now()
    elif action == 'rejected':
        datacenter_order.status = 'rejected'
        datacenter_order.completion_date = timezone.now()

    # Устанавливаем модератора как текущего пользователя
    datacenter_order.moderator = user  # Присваиваем экземпляр пользователя

    try:
        datacenter_order.save()  # Сохраняем изменения
    except IntegrityError as e:
        return Response({'error': 'Ошибка сохранения заказа: {}'.format(str(e))}, status=status.HTTP_400_BAD_REQUEST)

    # Сериализуем и возвращаем данные о заказе
    serializer = DatacenterOrderSerializer(datacenter_order)
    return Response(serializer.data, status=status.HTTP_200_OK)

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
@permission_classes([AllowAny])  # Внешняя проверка на уровне сессий
def update_order(request, pk):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы обновить заказ.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

    # Проверяем, что заказ не удалён
    if datacenter_order.status == 'deleted':
        return Response({'error': 'Обновление удалённых заказов невозможно.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверка, является ли текущий пользователь создателем заказа
    if str(datacenter_order.creator_id) != user_id:
        return Response({'error': 'У вас нет прав на обновление этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    # Инициализируем сериализатор с частичным обновлением (partial=True)
    serializer = DatacenterOrderSerializer(datacenter_order, data=request.data, partial=True)

    # Проверяем, валидны ли данные
    if serializer.is_valid():
        serializer.save()  # Сохраняем обновления
        return Response({'message': 'Заказ обновлён успешно', 'data': serializer.data}, status=status.HTTP_200_OK)

    # Возвращаем ошибки, если данные невалидны
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    operation_description="Удаление товара из заказа",
    responses={
        200: 'Количество товаров уменьшено на 1',
        204: 'Товар удален из заказа',
        400: 'Заказ удален или не может быть изменен',
        404: 'Товар не найден в заказе',
    }
)
@api_view(['DELETE'])
@permission_classes([AllowAny])  # Проверка на уровне сессий
def delete_service_from_order(request, datacenter_order_id, datacenter_service_id):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы удалить товар из заказа.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')
    user = get_object_or_404(User, id=user_id)  # Получаем пользователя по user_id

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)

    # Проверяем статус заказа
    if datacenter_order.status != 'draft':
        return Response({'error': 'Заказ не может быть изменен, так как он не в статусе draft.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, является ли пользователь создателем заказа
    if str(datacenter_order.creator_id) != str(user.id):
        return Response({'error': 'У вас нет прав на удаление товара из этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем услугу из заказа
    datacenter_service = get_object_or_404(DatacenterService, id=datacenter_service_id)

    # Находим соответствующую услугу в заказе
    datacenter_order_service = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter_service).first()

    if datacenter_order_service:
        if datacenter_order_service.quantity > 1:
            # Уменьшаем количество товара
            datacenter_order_service.quantity -= 1
            datacenter_order_service.save()
            return Response({'message': 'Количество товаров уменьшено на 1'}, status=status.HTTP_200_OK)
        else:
            # Удаляем товар, если количество 1
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
@permission_classes([AllowAny])  # Проверка на уровне сессий
def update_service_quantity_in_order(request, datacenter_order_id, datacenter_service_id):
    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы изменить количество товаров в заказе.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')
    user = get_object_or_404(User, id=user_id)  # Получаем пользователя по user_id

    # Получаем заказ по ID
    datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)

    # Проверяем статус заказа
    if datacenter_order.status != 'draft':
        return Response({'error': 'Заказ не может быть изменен, так как он не в статусе draft.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, является ли пользователь создателем заказа
    if str(datacenter_order.creator_id) != str(user.id):
        return Response({'error': 'У вас нет прав на изменение количества товаров в этом заказе.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем услугу из заказа
    datacenter_service = get_object_or_404(DatacenterService, id=datacenter_service_id)

    # Получаем запись о товаре в заказе
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

        # Обновляем количество товара
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
    request_body=RegisterSerializer,
    responses={
        201: openapi.Response('Пользователь успешно зарегистрирован', 
                              schema=openapi.Schema(type=openapi.TYPE_OBJECT, 
                                                    properties={
                                                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
                                                    })),
        400: 'Ошибка валидации данных'
    },
    operation_summary="Регистрация пользователя",
    operation_description="Создает нового пользователя с указанными данными."
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Для регистрации без аутентификации
def create_user(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                "email": user.email,
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



logger = logging.getLogger(__name__)

# Подключение к экземпляру Redis
session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

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
                                                    properties={
                                                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
                                                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access токен'),
                                                        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh токен'),
                                                    })),
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

    # Логирование попытки входа
    logger.info(f"Попытка входа пользователя с email: {email}")

    user = authenticate(request, email=email, password=password)
    
    if user is not None:
        # Вход пользователя
        login(request, user)

        # Генерация уникального идентификатора сессии
        session_id = request.session.session_key
        
        if session_id:  # Проверяем, что session_id не None
            # Сохранение ID пользователя в Redis с ключом session_id
            redis_client.set(session_id, user.id, ex=3600)  # Сохраняем ID пользователя с TTL 1 час
            
            logger.info(f"Сессия сохранена в Redis для пользователя с email: {email}, session_id: {session_id}")

            return Response({'session_id': session_id}, status=status.HTTP_200_OK)
        else:
            logger.error("Не удалось получить session_id.")
            return Response({'detail': 'Ошибка создания сессии.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.warning(f"Неверная попытка входа для email: {email}")
    return Response({'detail': 'Неверный email или пароль.'}, status=status.HTTP_401_UNAUTHORIZED)


@swagger_auto_schema(
    method='post',
    responses={
        200: 'Успешный выход из системы',
        401: 'Отсутствует идентификатор сессии.'
    },
    operation_summary="Выход пользователя",
    operation_description="Разлогинивает пользователя."
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Доступ только для аутентифицированных пользователей
def logout_user(request):
    # Извлекаем sessionid из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        return Response({'detail': 'Отсутствует идентификатор сессии.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Удаляем идентификатор пользователя из Redis
    redis_client.delete(session_id)

    # Выход из системы
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
    operation_description="Частично обновляет данные пользователя."
)
@api_view(['PUT'])
def update_user(request):
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        logger.warning("Session ID is missing.")
        return Response({'detail': 'Отсутствует идентификатор сессии.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Получаем идентификатор пользователя из Redis по session_id
    user_id_from_session = redis_client.get(session_id)

    if user_id_from_session is None:
        logger.warning("Invalid session.")
        return Response({'detail': 'Недействительная сессия.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Декодируем идентификатор пользователя
    user_id_from_session = user_id_from_session.decode('utf-8') if isinstance(user_id_from_session, bytes) else user_id_from_session

    try:
        user = User.objects.get(id=user_id_from_session)  # Получаем пользователя из сессии
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id_from_session} not found.")
        return Response({'detail': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

    # Проверяем, является ли пользователь тем, кто хочет обновить данные
    if str(user.id) != user_id_from_session:
        logger.warning(f"User {user_id_from_session} tried to update another user's information.")
        return Response({'detail': 'Вы можете обновить только свои собственные данные.'}, status=status.HTTP_403_FORBIDDEN)

    # Сохраняем старую почту для дальнейшего сравнения
    old_email = user.email
    
    serializer = UserSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        # Проверяем, изменяется ли почта
        new_email = serializer.validated_data.get('email', old_email)
        if new_email != old_email:
            # Здесь можно добавить логику для обработки изменения почты, если это необходимо
            # Например, отправка подтверждения на новую почту
            logger.info(f"User {user_id_from_session} is changing email from {old_email} to {new_email}.")
        
        serializer.save()
        logger.info(f"User with ID {user_id_from_session} updated successfully.")
        return Response({'message': 'Информация о пользователе успешно обновлена'}, status=status.HTTP_200_OK)

    logger.error(f"Validation errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

