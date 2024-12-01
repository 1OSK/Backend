
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


#	DatacenterService: создаётся новая запись.
#	CustomUser: проверяется, что пользователь аутентифицирован и является администратором.
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



#   •	DatacenterService: возвращается список товаров с фильтрацией по цене.
#	•	DatacenterOrder: для подсчёта количества услуг в черновом заказе текущего пользователя.
#	•	DatacenterOrderService: для работы с услугами в черновом заказе.
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


    logger.info(f"Черновик найден: ID {datacenter_draft_order_id}, Количество товаров: {datacenter_services_count}")

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



# •	DatacenterService: возвращает данные товара по ID.
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



#   •	DatacenterService: обновляется существующий товар.
#	•	CustomUser: проверяется, что пользователь аутентифицирован и является администратором.
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



#   •	DatacenterService: меняет статус товара на deleted.
#	•	CustomUser: проверяется, что пользователь аутентифицирован и является администратором.

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

#   •	DatacenterOrder: создаёт или обновляет черновой заказ для пользователя.
#	•	DatacenterService: добавляет услугу в черновик.
#	•	DatacenterOrderService: добавляет или обновляет количество услуг в черновом заказе.
#	•	CustomUser: проверяется, что пользователь аутентифицирован.
@swagger_auto_schema(
    method='post',
    responses={201: DatacenterOrderSerializer, 400: "Ошибка при добавлении в черновик"},
    operation_summary="Добавить товар в черновик заказа",
    operation_description="Метод для добавления услуги в черновик заказа. Проверяет наличие sessionid, "
                          "выбирает или создает черновик для текущего пользователя и добавляет выбранный товар в этот черновик."
)
@api_view(['POST'])
def add_to_draft(request, pk):
    """
    Добавляет услугу в черновик заказа. Если черновик еще не существует для пользователя,
    он создается. Если услуга уже есть в черновике, ее количество увеличивается на 1.
    
    **Шаги:**
    1. Проверка наличия sessionid в куки.
    2. Проверка сессии пользователя в Redis.
    3. Получение услуги по переданному ID (pk).
    4. Получение или создание черновика.
    5. Добавление услуги в черновик.
    6. Возвращение сериализованного черновика.
    """
    
    # Извлечение sessionid из куки
    session_id = (
        request.COOKIES.get('sessionid') 
    )

    if not session_id:
        logger.error("Session ID отсутствует в куки.")
        return Response(
            {"error": "sessionid не предоставлен."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Извлечение ID пользователя из Redis
    user_id = redis_client.get(session_id)
    
    if user_id is None:
        logger.warning(f"Неверный sessionid или сессия истекла. Session ID: {session_id}")
        return Response(
            {"error": "Неверный sessionid или сессия истекла."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Получение текущего пользователя
    try:
        user = get_object_or_404(CustomUser, id=user_id)
    except CustomUser.DoesNotExist:
        logger.error(f"Пользователь с ID {user_id} не найден.")
        return Response(
            {"error": "Пользователь не найден."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Получение услуги по переданному ID
    try:
        datacenter_service = get_object_or_404(DatacenterService, id=pk)
    except DatacenterService.DoesNotExist:
        logger.error(f"Услуга с ID {pk} не найдена.")
        return Response(
            {"error": "Услуга не найдена."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Получаем или создаем черновик для текущего пользователя
    datacenter_draft_order, created = DatacenterOrder.objects.get_or_create(
        creator=user,
        status='draft',
        defaults={'total_price': 0}  # Устанавливаем начальную цену
    )
    if created:
        logger.info(f"Создан новый черновик для пользователя {user_id}. ID заказа: {datacenter_draft_order.id}")
    else:
        logger.info(f"Черновик заказа уже существует для пользователя {user_id}. ID заказа: {datacenter_draft_order.id}")

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

    # Логируем добавление товара
    logger.info(f"Товар с ID {pk} добавлен в черновик заказа. Количество: {datacenter_order_service.quantity}.")

    # Сериализуем черновик
    serializer = DatacenterOrderSerializer(datacenter_draft_order)

    logger.info(f"Товар успешно добавлен в черновик заказа. ID черновика: {datacenter_draft_order.id}")

    return Response(
        {
            'message': 'Товар добавлен в черновик заказа',
            'draft_order': serializer.data
        },
        status=status.HTTP_201_CREATED
    )


#   •	DatacenterService: добавляет или обновляет URL изображения товара.
#	•	CustomUser: проверяется, что пользователь аутентифицирован и является администратором.
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



# DatacenterOrder
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
    # Логируем запрос
    logger.info('Получение списка заказов с параметрами: %s', request.GET)

    # Извлекаем session_id из куки
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        logger.warning('sessionid не предоставлен')
        return Response({'error': 'sessionid не предоставлен.'}, status=status.HTTP_400_BAD_REQUEST)

    # Логируем получение session_id
    logger.info('sessionid получен: %s', session_id)

    # Извлекаем ID пользователя из Redis
    user_id = redis_client.get(session_id)
    if user_id is None:
        logger.warning('Неверный sessionid или сессия истекла для sessionid: %s', session_id)
        return Response({'error': 'Неверный sessionid или сессия истекла.'}, status=status.HTTP_403_FORBIDDEN)

    # Логируем успешное извлечение user_id
    logger.info('user_id извлечен из Redis: %s', user_id)

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
        logger.info('Фильтруем заказы по пользователю с ID: %s', user.id)
        datacenter_orders = datacenter_orders.filter(creator_id=user.id)

    # Фильтрация по статусу
    if status_filter:
        logger.info('Фильтруем заказы по статусу: %s', status_filter)
        datacenter_orders = datacenter_orders.filter(status=status_filter)

    # Фильтрация по дате
    if start_date and end_date:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            logger.info('Фильтруем заказы по дате от %s до %s', start_date, end_date)
            datacenter_orders = datacenter_orders.filter(creation_date__range=[start_date, end_date])
        except ValueError:
            logger.error('Неверный формат даты: start_date=%s, end_date=%s', start_date, end_date)
            return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    # Сериализуем результат
    serializer = DatacenterOrderSerializer(datacenter_orders, many=True)

    # Логируем успешное завершение запроса
    logger.info('Запрос успешно выполнен, количество заказов: %d', len(serializer.data))

    return Response(serializer.data, status=status.HTTP_200_OK)

# DatacenterOrder
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

# DatacenterOrder
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

# DatacenterOrder
@swagger_auto_schema(
    method='put',
    responses={200: "Заказ подтверждён", 404: "Заказ не найден", 400: "Ошибка подтверждения"},
    operation_summary="Подтвердить заказ",
    operation_description="Подтверждает заказ по его ID."
)
@api_view(['PUT'])
@permission_classes([AllowAny])  # Внешняя проверка на уровне сессий
def submit_order(request, pk):
    logger.info(f"Запрос на подтверждение заказа с ID {pk} поступил.")

    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')
    logger.debug(f"Получен session_id: {session_id}")

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        logger.warning(f"Не авторизован. Session_id {session_id} не найден в Redis.")
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы подтвердить заказ.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')
    logger.debug(f"Получен user_id из Redis: {user_id}")

    # Получаем заказ по ID
    try:
        datacenter_order = get_object_or_404(DatacenterOrder, id=pk)
        logger.info(f"Заказ с ID {pk} найден в базе данных.")
    except DatacenterOrder.DoesNotExist:
        logger.error(f"Заказ с ID {pk} не найден.")
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

    # Проверка, является ли текущий пользователь создателем заказа
    if str(datacenter_order.creator_id) != user_id:
        logger.warning(f"Пользователь {user_id} не является создателем заказа с ID {pk}.")
        return Response({'error': 'У вас нет прав на подтверждение этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    if datacenter_order.status != 'draft':
        logger.warning(f"Заказ с ID {pk} уже не находится в статусе 'draft'.")
        return Response({'error': 'Заказ уже был отправлен или не может быть отправлен.'}, status=status.HTTP_400_BAD_REQUEST)

    delivery_address = datacenter_order.delivery_address
    delivery_time = datacenter_order.delivery_time

    if not delivery_address:
        logger.warning(f"Адрес доставки для заказа с ID {pk} не указан.")
        return Response({'error': 'Адрес доставки не указан в заявке.'}, status=status.HTTP_400_BAD_REQUEST)

    if not delivery_time:
        logger.warning(f"Время доставки для заказа с ID {pk} не указано.")
        return Response({'error': 'Время доставки не указано в заявке.'}, status=status.HTTP_400_BAD_REQUEST)

    # Рассчитываем полную стоимость заказа
    total_price = 0
    logger.info(f"Рассчитываем полную стоимость для заказа с ID {pk}.")
    for order_service in DatacenterOrderService.objects.filter(order=datacenter_order):
        item_total = order_service.quantity * order_service.service.price
        total_price += item_total
        logger.debug(f"Добавлена стоимость для товара: {order_service.service.name}, количество: {order_service.quantity}, цена: {order_service.service.price}, итог: {item_total}")

    logger.info(f"Общая стоимость заказа с ID {pk}: {total_price}")

    # Обновляем статус заказа, дату подтверждения и полную стоимость
    datacenter_order.status = 'formed'
    datacenter_order.formation_date = timezone.now()
    datacenter_order.total_price = total_price
    datacenter_order.save()

    # Серилизуем обновленный заказ
    serializer = DatacenterOrderSerializer(datacenter_order)
    logger.info(f"Заказ с ID {pk} успешно подтверждён.")

    return Response({'message': 'Заказ подтверждён успешно', 'datacenter_order': serializer.data}, status=status.HTTP_200_OK)




# DatacenterOrder
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


# DatacenterOrder
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

    # Проверяем, что заказ находится в статусе 'draft'
    if datacenter_order.status != 'draft':
        return Response({'error': 'Только заказ в статусе "Черновик" может быть обновлён.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверка, является ли текущий пользователь создателем заказа
    if str(datacenter_order.creator_id) != user_id:
        return Response({'error': 'У вас нет прав на обновление этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем данные из запроса и обновляем только необходимые поля
    delivery_address = request.data.get('delivery_address', None)
    delivery_time = request.data.get('delivery_time', None)

    if delivery_address is None:
        delivery_address = datacenter_order.delivery_address
    if delivery_time is None:
        delivery_time = datacenter_order.delivery_time

    # Логируем изменения, если они есть
    changes = {}
    if delivery_address != datacenter_order.delivery_address:
        changes['delivery_address'] = {
            'old': datacenter_order.delivery_address,
            'new': delivery_address
        }
    if delivery_time != datacenter_order.delivery_time:
        changes['delivery_time'] = {
            'old': datacenter_order.delivery_time,
            'new': delivery_time
        }

    # Если есть изменения, выводим их в лог
    if changes:
        logger.info(f"Изменения в заказе ID {pk}: {changes}")

    # Инициализируем сериализатор с частичным обновлением (partial=True)
    serializer = DatacenterOrderSerializer(
        datacenter_order,
        data={'delivery_address': delivery_address, 'delivery_time': delivery_time},
        partial=True  # Обновляем только те поля, которые были переданы
    )

    # Проверяем, валидны ли данные
    if serializer.is_valid():
        serializer.save()  # Сохраняем обновления
        return Response({'message': 'Заказ обновлён успешно', 'data': serializer.data}, status=status.HTTP_200_OK)

    # Возвращаем ошибки, если данные невалидны
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# DatacenterOrder, DatacenterService, DatacenterOrderService
@swagger_auto_schema(
    method='delete',
    operation_description="Удаление всего товара из заказа",
    responses={
        200: 'Товар удален из заказа',
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

    # Находим все записи об услуге в заказе
    datacenter_order_services = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter_service)

    if datacenter_order_services.exists():
        # Удаляем все записи о данной услуге
        datacenter_order_services.delete()
        return Response({'message': 'Товар полностью удален из заказа'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Товар не найден в заказе'}, status=status.HTTP_404_NOT_FOUND)
# DatacenterOrder, DatacenterService, DatacenterOrderService
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
    logger.debug(f"Получен session_id: {session_id}")  # Логируем session_id

    # Проверяем, есть ли session_id в Redis
    if not session_id or not session_storage.get(session_id):
        logger.warning(f"Неавторизованный доступ для session_id: {session_id}")
        return Response(
            {'error': 'Пожалуйста, авторизуйтесь, чтобы изменить количество товаров в заказе.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Получаем user_id из Redis
    user_id = session_storage.get(session_id).decode('utf-8')
    logger.debug(f"Получен user_id из Redis: {user_id}")

    try:
        user = get_object_or_404(User, id=user_id)  # Получаем пользователя по user_id
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя по user_id: {user_id}, ошибка: {e}")
        return Response({'error': 'Ошибка при получении пользователя.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.debug(f"Пользователь с ID {user.id} найден")

    # Получаем заказ по ID
    try:
        datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)
    except Exception as e:
        logger.error(f"Ошибка при получении заказа с ID: {datacenter_order_id}, ошибка: {e}")
        return Response({'error': 'Ошибка при получении заказа.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.debug(f"Заказ с ID {datacenter_order.id} найден")

    # Проверяем статус заказа
    if datacenter_order.status != 'draft':
        logger.warning(f"Попытка изменения заказа с неподобающим статусом: {datacenter_order.status}")
        return Response({'error': 'Заказ не может быть изменен, так как он не в статусе draft.'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, является ли пользователь создателем заказа
    if str(datacenter_order.creator_id) != str(user.id):
        logger.warning(f"Пользователь {user.id} пытается изменить заказ, который не был создан им.")
        return Response({'error': 'У вас нет прав на изменение количества товаров в этом заказе.'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем услугу из заказа
    try:
        datacenter_service = get_object_or_404(DatacenterService, id=datacenter_service_id)
    except Exception as e:
        logger.error(f"Ошибка при получении услуги с ID: {datacenter_service_id}, ошибка: {e}")
        return Response({'error': 'Ошибка при получении услуги.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.debug(f"Услуга с ID {datacenter_service.id} найдена")

    # Получаем запись о товаре в заказе
    datacenter_order_service = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter_service).first()
    if not datacenter_order_service:
        logger.warning(f"Товар с ID {datacenter_service.id} не найден в заказе с ID {datacenter_order.id}")
        return Response({'error': 'Товар не найден в заказе'}, status=status.HTTP_404_NOT_FOUND)

    # Обрабатываем изменение количества
    data = request.data
    new_quantity = data.get('quantity')

    if new_quantity is None:
        logger.warning(f"Не указано количество для товара с ID {datacenter_service.id} в заказе с ID {datacenter_order.id}")
        return Response({'error': 'Не указано количество'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        new_quantity = int(new_quantity)
        if new_quantity < 1:
            logger.warning(f"Некорректное количество товара: {new_quantity}. Оно должно быть положительным.")
            return Response({'error': 'Количество должно быть положительным'}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        logger.warning(f"Некорректное количество для товара с ID {datacenter_service.id}. Должно быть числовым значением.")
        return Response({'error': 'Некорректное количество'}, status=status.HTTP_400_BAD_REQUEST)

    # Обновляем количество товара
    datacenter_order_service.quantity = new_quantity
    datacenter_order_service.save()

    logger.info(f"Количество товара с ID {datacenter_service.id} в заказе {datacenter_order.id} обновлено на {new_quantity}")

    return Response({'message': 'Количество товаров обновлено в заказе'}, status=status.HTTP_200_OK)


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
                                                        'session_id': openapi.Schema(type=openapi.TYPE_STRING, description='Идентификатор сессии пользователя, сохранённый в Redis'),
                                                    })),
        401: 'Неверный email или пароль.',
        500: 'Ошибка создания сессии или сохранения в Redis.'
    },
    operation_summary="Вход пользователя",
    operation_description="Аутентификация пользователя по email и паролю. При успешной аутентификации создается сессия, которая сохраняется в Redis с уникальным идентификатором сессии."
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
        200: 'Успешный выход из системы.',
        400: 'Некорректный запрос. Отсутствует session_id в теле запроса.',
        401: 'Отсутствует идентификатор сессии или сессия не найдена.',
    },
    operation_summary="Выход пользователя",
    operation_description="Метод для выхода пользователя из системы. Удаляет session_id из Redis, завершает сессию и удаляет черновые заказы."
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Разрешаем доступ всем пользователям
def logout_user(request):
    """
    Разлогинивает пользователя.

    Этот метод удаляет идентификатор сессии пользователя из Redis и завершает текущую сессию.
    Также удаляет черновые заказы, если они есть, но только если пользователь является их создателем.
    session_id передается в теле запроса.
    """
    # Извлекаем session_id из тела запроса
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        # Логируем ошибку, когда session_id не передан
        logger.warning("Запрос на выход: отсутствует session_id.")
        return Response({'detail': 'Отсутствует идентификатор сессии.'}, status=status.HTTP_400_BAD_REQUEST)

    # Логируем информацию о получении session_id
    logger.info(f"Попытка выхода пользователя с session_id: {session_id}")

    # Проверяем, существует ли такая сессия в Redis
    if not redis_client.exists(session_id):
        # Логируем ошибку, если сессия не найдена
        logger.warning(f"Сессия с session_id {session_id} не найдена в Redis.")
        return Response({'detail': 'Не найдено сессии с указанным идентификатором.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Получаем user_id из Redis перед удалением сессии
    user_id = redis_client.get(session_id)  # Нет необходимости в decode()

    # Логируем информацию об успешном удалении сессии
    logger.info(f"Сессия с session_id {session_id} найдена. Удаляем из Redis.")

    # Удаляем идентификатор сессии из Redis
    redis_client.delete(session_id)

    # Логика удаления черновых заказов
    try:
        # Ищем черновые заказы этого пользователя
        draft_orders = DatacenterOrder.objects.filter(creator_id=user_id, status='draft')

        # Если черновые заказы найдены, удаляем их
        deleted_count = draft_orders.delete()[0]

        # Логируем информацию о количестве удалённых черновых заказов
        logger.info(f"Удалено {deleted_count} черновых заказов для пользователя с user_id {user_id}.")

        # Если черновых заказов не было, можно вернуть соответствующее сообщение
        if deleted_count == 0:
            logger.info(f"Нет черновых заказов для удаления у пользователя с user_id {user_id}.")
    except Exception as e:
        # Логируем ошибку, если произошла ошибка при удалении заказов
        logger.error(f"Ошибка при удалении черновых заказов: {e}")

    # Выход из системы
    logout(request)

    # Логируем успешный выход
    logger.info(f"Пользователь с session_id {session_id} успешно разлогинен.")

    # Возвращаем успешный ответ
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
    # Логирование начала обработки запроса
    logger.info("Processing user update request.")

    # Получаем session_id из куки
    session_id = request.COOKIES.get('sessionid')

    if not session_id:
        logger.warning("Session ID is missing in the request.")
        return Response({'detail': 'Отсутствует идентификатор сессии.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Получаем идентификатор пользователя из Redis по session_id
    user_id_from_session = redis_client.get(session_id)

    if user_id_from_session is None:
        logger.warning(f"Session {session_id} does not correspond to any user.")
        return Response({'detail': 'Недействительная сессия.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Декодируем идентификатор пользователя
    user_id_from_session = user_id_from_session.decode('utf-8') if isinstance(user_id_from_session, bytes) else user_id_from_session
    logger.info(f"Session {session_id} corresponds to user {user_id_from_session}.")

    try:
        user = User.objects.get(id=user_id_from_session)  # Получаем пользователя из сессии
        logger.info(f"User {user_id_from_session} found in the database.")
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id_from_session} not found in the database.")
        return Response({'detail': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

    # Проверяем, является ли пользователь тем, кто хочет обновить данные
    if str(user.id) != user_id_from_session:
        logger.warning(f"User {user_id_from_session} tried to update another user's information.")
        return Response({'detail': 'Вы можете обновить только свои собственные данные.'}, status=status.HTTP_403_FORBIDDEN)

    # Сохраняем старую почту и пароль для дальнейшего сравнения
    old_email = user.email
    old_password = user.password  # Старый пароль
    logger.info(f"User {user_id_from_session} is attempting to update email from {old_email}.")
    logger.info(f"Old password: {old_password}")  # Логирование старого пароля

    # Сериализация данных для обновления
    serializer = UserSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        # Проверяем, изменяется ли почта
        new_email = serializer.validated_data.get('email', old_email)
        if new_email != old_email:
            # Логируем изменение почты
            logger.info(f"User {user_id_from_session} is changing email from {old_email} to {new_email}.")

        # Проверяем, изменяется ли пароль
        new_password = serializer.validated_data.get('password', None)
        if new_password:
            # Логируем изменение пароля
            logger.info(f"User {user_id_from_session} changed their password.")
            logger.info(f"New password: {new_password}")  # Логирование нового пароля
        
        # Сохраняем обновленные данные пользователя
        serializer.save()
        logger.info(f"User {user_id_from_session} updated successfully.")
        return Response({'message': 'Информация о пользователе успешно обновлена'}, status=status.HTTP_200_OK)

    # Логируем ошибку валидации
    logger.error(f"Validation errors occurred during user update: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

