
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

def get_current_user():
    """Получаем текущего пользователя (мокового пользователя)"""
    mock_user = get_mock_user()

    if not isinstance(mock_user, User):
        raise ValueError("Неверный пользователь")

    return mock_user


def get_filtered_queryset(queryset):
    """Фильтруем queryset, исключая услуги со статусом 'удалена'"""
    return queryset.exclude(status='удалена')


class DatacenterServiceAPIView(APIView):
    queryset = DatacenterService.objects.all()
    serializer_class = DatacenterServiceSerializer

    def get(self, request, pk=None):
        if pk:
            datacenter_service = get_object_or_404(self.queryset, id=pk)  # Используем queryset напрямую
            datacenter_service_data = self.serializer_class(datacenter_service).data
            return Response(datacenter_service_data)
        else:
            return self.get_datacenter_service_list(request)

    def get_datacenter_service_list(self, request):
        try:
            mock_user = get_current_user()  # Используем внешнюю функцию
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        min_price = request.GET.get('datacenter_min_price')
        max_price = request.GET.get('datacenter_max_price')

        datacenter_services = get_filtered_queryset(self.queryset)  # Фильтруем queryset

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

        datacenter_services_list = self.serializer_class(datacenter_services, many=True).data

        response_data = {
            'datacenters': datacenter_services_list,
            'draft_order_id': datacenter_draft_order_id,
            'datacenters_count': datacenter_services_count
        }

        return Response(response_data)

    def put(self, request, pk):
        instance = get_object_or_404(self.queryset, pk=pk)

        if instance.status == 'deleted':
            return Response({'error': 'Невозможно обновить удаленную услугу.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_datacenter_service = serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        datacenter_service = get_object_or_404(self.queryset, id=pk)

        if datacenter_service.status == 'deleted':
            return Response({'error': 'Эта услуга уже была удалена.'}, status=status.HTTP_400_BAD_REQUEST)

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

        return Response({'message': 'Услуга успешно удалена'}, status=status.HTTP_200_OK)

    def post_add_to_draft(self, request, pk):
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
                'message': 'Услуга добавлена в черновик заказа',
                'draft_order': serializer.data,
                'datacenters_count': datacenter_services_count
            },
            status=status.HTTP_201_CREATED
        )

    def post(self, request, pk=None):
        if request.path.endswith('/add-image/'):
            return self.post_add_image(request, pk)
        elif request.path.endswith('/add-to-draft/'):
            return self.post_add_to_draft(request, pk)
        else:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_datacenter_service = serializer.save()
            response_data = self.serializer_class(new_datacenter_service).data
            return Response(response_data, status=status.HTTP_201_CREATED)

    def post_add_image(self, request, pk):
        datacenter_service = get_object_or_404(self.queryset, id=pk)

        if datacenter_service.status == 'deleted':
            return Response({'error': 'Нельзя добавлять изображение к удаленной услуге.'}, status=400)

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
        
class DatacenterOrderView(APIView):
    # Получение списка или конкретного заказа
    def get(self, request, pk=None):
        if pk is not None:
            return self.retrieve(request, pk)
        else:
            moderator = get_mock_user()
            status_filter = request.GET.get('datacenter_status')
            start_date = request.GET.get('datacenter_start_date')
            end_date = request.GET.get('datacenter_end_date')

            # Исключаем заявки со статусом 'deleted' и 'draft'
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
            return Response({'datacenter_orders': serializer.data})

    # Получение информации о заявке
    def retrieve(self, request, pk=None):
        datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

        if datacenter_order.status == 'deleted':
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DatacenterOrderSerializer(datacenter_order)
        return Response(serializer.data)

    # Обновление заявки
    def put(self, request, pk=None):
        if pk is not None:
            # Определяем действие на основе пути
            if request.path.endswith('/submit/'):
                return self.submit_datacenter_order(request, pk)
            elif request.path.endswith('/finalize/'):
                return self.finalize_datacenter_order(request, pk)
            elif request.path.endswith('/update/'):
                try:
                    datacenter_order = DatacenterOrder.objects.get(id=pk)
                except DatacenterOrder.DoesNotExist:
                    return Response({'error': 'Заявка не найдена.'}, status=status.HTTP_404_NOT_FOUND)

                if datacenter_order.status == 'deleted':
                    return Response({'error': 'Обновление удалённых заявок невозможно.'}, status=status.HTTP_400_BAD_REQUEST)

                serializer = DatacenterOrderSerializer(datacenter_order, data=request.data, partial=True)

                if serializer.is_valid():
                    serializer.save()
                    return Response({'message': 'Заказ обновлён успешно', 'datacenter_order_id': datacenter_order.id}, status=status.HTTP_200_OK)

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'error': 'Неизвестное действие'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': 'ID заявки не указан'}, status=status.HTTP_400_BAD_REQUEST)

    # Отправка заявки
    def submit_datacenter_order(self, request, pk=None):
        datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

        if datacenter_order.status != 'draft':
            return Response({'error': 'Заказ уже был отправлен или не в состоянии для отправки.'}, status=status.HTTP_400_BAD_REQUEST)

        delivery_address = datacenter_order.delivery_address
        delivery_time = datacenter_order.delivery_time

        if not delivery_address:
            return Response({'error': 'Адрес доставки не указан в заявке.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not delivery_time:
            return Response({'error': 'Время доставки не указано в заявке.'}, status=status.HTTP_400_BAD_REQUEST)

        datacenter_order.status = 'formed'
        datacenter_order.formation_date = timezone.now()

        try:
            datacenter_order.save()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DatacenterOrderSerializer(datacenter_order)
        return Response({'message': 'Заказ успешно отправлен', 'datacenter_order': serializer.data}, status=status.HTTP_200_OK)

    # Завершение или отклонение заявки
    def finalize_datacenter_order(self, request, pk=None):
        datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

        if datacenter_order.status == 'deleted':
            return Response({'error': 'Заявка удалена и не может быть завершена или отклонена.'}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get('action')

        if not action:
            return Response({'error': 'Параметр action не указан.'}, status=status.HTTP_400_BAD_REQUEST)

        moderator = get_mock_user()

        if request.user.id not in [moderator.id]:
            return Response({'error': 'У вас нет прав для выполнения этого действия.'}, status=status.HTTP_403_FORBIDDEN)

        if action == 'completed':
            datacenter_order.status = 'completed'
            datacenter_order.completion_date = timezone.now()
        elif action == 'rejected':
            datacenter_order.status = 'rejected'
            datacenter_order.completion_date = timezone.now()
        else:
            return Response({'error': 'Некорректное значение параметра action.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            datacenter_order.save()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'Заявка успешно {action}.'}, status=status.HTTP_200_OK)

    # Удаление заявки
    def delete(self, request, pk=None):
        datacenter_order = get_object_or_404(DatacenterOrder, id=pk)

        if datacenter_order.status == 'deleted':
            return Response({'error': 'Заявка уже удалена и не может быть удалена повторно.'}, status=status.HTTP_400_BAD_REQUEST)

        datacenter_order.status = 'deleted'
        
        try:
            datacenter_order.save()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Заявка успешно удалена.'}, status=status.HTTP_204_NO_CONTENT)

class DatacenterServiceOrderView(APIView):
    # 14. DELETE: Удаление услуги из заявки
    def delete(self, request, datacenter_order_id, datacenter_service_id):
        # Получаем заказ по ID, если не найден, возвращаем 404
        datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)

        # Проверяем, был ли заказ удален
        if datacenter_order.status == 'deleted':
            return Response({'error': 'Заказ удален, нельзя удалить услуги'}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем услугу по ID, если не найден, возвращаем 404
        datacenter = get_object_or_404(DatacenterService, id=datacenter_service_id)

        # Находим связь между заказом и услугой
        datacenter_order_service = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter).first()

        # Проверяем, существует ли связь между заказом и услугой
        if datacenter_order_service:
            if datacenter_order_service.quantity > 1:
                # Уменьшаем количество услуги на 1
                datacenter_order_service.quantity -= 1
                datacenter_order_service.save()
                return Response({'message': 'Количество услуги уменьшено на 1'}, status=status.HTTP_200_OK)
            else:
                # Удаляем связь, если количество равно 1
                datacenter_order_service.delete()
                return Response({'message': 'Услуга удалена из заказа'}, status=status.HTTP_204_NO_CONTENT)

        # Если услуга не найдена в заказе
        return Response({'error': 'Услуга не найдена в заказе'}, status=status.HTTP_404_NOT_FOUND)

    # 15. PUT: Изменение количества/порядка/значения услуги в заявке
    def put(self, request, datacenter_order_id, datacenter_service_id):
        datacenter_order = get_object_or_404(DatacenterOrder, id=datacenter_order_id)
        datacenter = get_object_or_404(DatacenterService, id=datacenter_service_id)

        datacenter_order_service = DatacenterOrderService.objects.filter(order=datacenter_order, service=datacenter).first()

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
            return Response({'message': 'Количество услуги обновлено в заказе'}, status=status.HTTP_200_OK)

        return Response({'error': 'Услуга не найдена в заказе'}, status=status.HTTP_404_NOT_FOUND)

class UserView(viewsets.ViewSet):
    # 16. POST: Регистрация пользователя
    def register(self, request):
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

    # 17. PUT: Обновление информации о пользователе
    def update_user(self, request, pk=None):
        user = get_object_or_404(User, id=pk)
        data = request.data

        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        if 'password' in data:
            user.set_password(data['password'])
        user.save()

        return Response({'message': 'Информация о пользователе успешно обновлена'}, status=status.HTTP_200_OK)

    # 18. POST: Вход пользователя
    def login_user(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({'message': 'Пользователь успешно вошел в систему'}, status=status.HTTP_200_OK)
        return Response({'error': 'Неверное имя пользователя или пароль'}, status=status.HTTP_401_UNAUTHORIZED)

    # 19. POST: Выход пользователя
    def logout_user(self, request):
        logout(request)
        return Response({'message': 'Пользователь успешно вышел из системы'}, status=status.HTTP_200_OK)
    