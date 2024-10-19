
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

class DatacenterServiceAPIView(APIView):
    queryset = DatacenterService.objects.all()
    serializer_class = DatacenterServiceSerializer
    def get_current_user(self):
        """Получаем текущего пользователя (мокового пользователя)"""
        mock_user = get_mock_user()
        
        if not isinstance(mock_user, User):
            raise ValueError("Неверный пользователь")

        return mock_user
    def get_queryset(self):
            return self.queryset.exclude(status='удалена')

    def get(self, request, pk=None):
            if pk:
                return self.get_service_detail(request, pk)
            else:
                return self.get_service_list(request)

    def get_service_detail(self, request, pk):
            # Получаем конкретную услугу по ID
            service = get_object_or_404(self.get_queryset(), id=pk)
            service_data = self.serializer_class(service).data
            return Response(service_data)

    def get_service_list(self, request):
        try:
            mock_user = self.get_current_user()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        min_price = request.GET.get('datacenter_min_price')
        max_price = request.GET.get('datacenter_max_price')

        services = self.get_queryset()  # Получаем все доступные услуги

        # Фильтрация по минимальной цене
        if min_price:
            try:
                min_price = float(min_price)
                services = services.filter(price__gte=min_price)
            except ValueError:
                return Response({"error": "Некорректное значение для минимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

        # Фильтрация по максимальной цене
        if max_price:
            try:
                max_price = float(max_price)
                services = services.filter(price__lte=max_price)
            except ValueError:
                return Response({"error": "Некорректное значение для максимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

        # Поиск черновика заказа
        draft_order = DatacenterOrder.objects.filter(creator=mock_user, status='draft').first()

        if draft_order:
            # Если черновик существует, подсчитываем общее количество услуг в нем
            services_count = sum(order_service.quantity for order_service in draft_order.datacenterorderservice_set.all())
            draft_order_id = draft_order.id
        else:
            services_count = 0  # Если черновика нет, количество услуг 0
            draft_order_id = None  # Устанавливаем id в None, если черновик не найден

        services_list = self.serializer_class(services, many=True).data

        response_data = {
            'services': services_list,
            'draft_order_id': draft_order_id,
            'services_count': services_count  # Возвращаем общее количество услуг в черновике
        }

        return Response(response_data)



    # 3. PUT: Обновление услуги без изображения
    def put(self, request, pk):
        partial = request.method == 'PATCH'
        instance = get_object_or_404(self.queryset, pk=pk)
        
        serializer = self.serializer_class(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_service = serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    # 4. DELETE: Удаление услуги
    def delete(self, request, pk):
        service = get_object_or_404(self.queryset.exclude(status='удалена'), id=pk)

        if service.image_url:
            client = Minio(
                endpoint=settings.AWS_S3_ENDPOINT_URL,
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                secure=settings.MINIO_USE_SSL
            )
            try:
                client.remove_object('something', f"{service.id}.png")  
            except Exception as e:
                return Response({'error': str(e)}, status=400)

        service.status = 'удалена'
        service.save()

        return Response({'message': 'Service deleted successfully'})


    def post_add_to_draft(self, request, pk):
        service = get_object_or_404(DatacenterService, id=pk)

        try:
            mock_user = self.get_current_user()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Создаем черновик заказа, если его нет
        draft_order, created = DatacenterOrder.objects.get_or_create(
            creator=mock_user,
            status='draft'
        )

        # Получаем или создаем связь между заказом и услугой
        order_service, created = DatacenterOrderService.objects.get_or_create(
            order=draft_order, 
            service=service,
            defaults={'quantity': 0}  # Убедитесь, что количество начинает с 0
        )

        # Если связь была создана, устанавливаем quantity в 1, иначе увеличиваем на 1
        if created:
            order_service.quantity = 1
        else:
            order_service.quantity += 1

        # Сохраняем изменения
        print(f"Количество услуг перед сохранением: {order_service.quantity}")
        order_service.save()
        print(f"Количество услуг после сохранения: {order_service.quantity}")

        # Обновляем общую стоимость черновика
        draft_order.total_price = sum(
            order_service.quantity * order_service.service.price
            for order_service in draft_order.datacenterorderservice_set.all()
        )
        draft_order.save()

        # Подсчет общего количества услуг в черновике
        services_count = sum(service.quantity for service in draft_order.datacenterorderservice_set.all())

        # Сериализация черновика заказа для ответа
        serializer = DatacenterOrderSerializer(draft_order)

        return Response(
            {
                'message': 'Услуга добавлена в черновик заказа',
                'draft_order': serializer.data,
                'services_count': services_count  # Возвращаем общее количество услуг в черновике
            },
            status=status.HTTP_201_CREATED
        )
    
    def post(self, request, pk=None):
        # Проверяем, если запрос идет на добавление изображения
        if request.path.endswith('/add-image/'):
            return self.post_add_image(request, pk)

        # Проверяем, если запрос идет на добавление услуги в черновик заказа
        elif request.path.endswith('/add-to-draft/'):
            return self.post_add_to_draft(request, pk)

        else:
            # Логика для создания новой услуги
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_service = serializer.save()

            # Сериализуем и возвращаем данные новой услуги
            response_data = self.serializer_class(new_service).data  # Сериализуем новую услугу
            return Response(response_data, status=status.HTTP_201_CREATED)

    def post_add_image(self, request, pk):
        # Получаем услугу по ID
        service = get_object_or_404(self.queryset.exclude(status='удалена'), id=pk)

        # Проверка наличия изображения в запросе
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=400)

        image = request.FILES['image']

        # Загрузка изображения с использованием Minio
        result = add_pic(service, image)

        # Проверка на успешность загрузки
        if 'error' in result:
            return Response({'error': result['error']}, status=400)  # Возвращаем ошибку

        # Обновляем поле image_url после успешной загрузки
        service.image_url = result['image_url']  # Получаем URL изображения
        service.save()  # Сохраняем изменения в базе данных

        # Создаем экземпляр сериализатора для обновленного сервиса
        serializer = DatacenterServiceImageSerializer(service)

        return Response({
            'message': 'Image added/updated successfully',
            'service': serializer.data  # Используем сериализованные данные
        }, status=200)
        
class DatacenterOrderView(APIView):

    def get(self, request, pk=None):
        if pk is not None:
            return self.retrieve(request, pk)
        else:
            return self.list(request)

    # 8. GET: Список заявок с фильтрацией
    def list(self, request):
        moderator = get_mock_user()
        status_filter = request.GET.get('datacenter_status')
        start_date = request.GET.get('datacenter_start_date')
        end_date = request.GET.get('datacenter_end_date')

        # Исключаем заявки со статусом 'deleted' и 'draft'
        orders = DatacenterOrder.objects.exclude(status__in=['deleted', 'draft'])

        if status_filter:
            orders = orders.filter(status=status_filter)

        if start_date and end_date:
            try:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d')
                orders = orders.filter(creation_date__range=[start_date, end_date])
            except ValueError:
                return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DatacenterOrderSerializer(orders, many=True)
        return Response({'orders': serializer.data})

    # 9. GET: Получение информации о заявке
    def retrieve(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

        if order.status == 'deleted':
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        services = order.datacenterorderservice_set.all()
        service_serializer = DatacenterOrderServiceSerializer(services, many=True)

        response = {
            'order_id': order.id,
            'status': order.status,
            'creation_date': order.creation_date,
            'formation_date': order.formation_date,
            'completion_date': order.completion_date,
            'delivery_address': order.delivery_address,
            'delivery_time': order.delivery_time,
            'total_price': order.total_price,
            'services': service_serializer.data,
        }

        return Response(response)

    def put(self, request, pk=None):
        if pk is not None:
            # Определяем действие на основе пути
            if request.path.endswith('/submit/'):
                return self.submit_order(request, pk)
            elif request.path.endswith('/finalize/'):
                return self.finalize_order(request, pk)
            elif request.path.endswith('/update/'):
                return self.update(request, pk)
            else:
                return Response({'error': 'Неизвестное действие'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'error': 'ID заявки не указан'}, status=status.HTTP_400_BAD_REQUEST)

    # 10. PUT: Обновление полей заявки
    def update(self, request, pk=None):
        try:
            order = DatacenterOrder.objects.get(id=pk)
        except DatacenterOrder.DoesNotExist:
            return Response({'error': 'Заявка не найдена.'}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, является ли заявка удалённой
        if order.status == 'deleted':
            return Response({'error': 'Обновление удалённых заявок невозможно.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DatacenterOrderSerializer(order, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Заказ обновлён успешно', 'order_id': order.id}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 11. PUT: Отправка заявки (отдельный маршрут)
    def submit_order(self, request, pk=None):
        print(f"Отправка заказа с ID: {pk}")
        order = get_object_or_404(DatacenterOrder, id=pk)

        # Проверка статуса заказа
        if order.status != 'draft':
            return Response({'error': 'Заказ уже был отправлен или не в состоянии для отправки.'}, status=status.HTTP_400_BAD_REQUEST)

        # Извлекаем адрес и время доставки из полей заявки
        delivery_address = order.delivery_address
        delivery_time = order.delivery_time

        # Проверяем, что адрес и время доставки указаны
        if not delivery_address:
            return Response({'error': 'Адрес доставки не указан в заявке.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not delivery_time:
            return Response({'error': 'Время доставки не указано в заявке.'}, status=status.HTTP_400_BAD_REQUEST)

        print(f"Текущий статус перед изменением: {order.status}")

        # Изменяем статус на 'formed' и устанавливаем дату формирования
        order.status = 'formed'
        order.formation_date = timezone.now()  # Устанавливаем дату формирования

        try:
            order.save()  # Сохраняем изменения
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Сериализуем обновленный объект заказа
        serializer = DatacenterOrderSerializer(order)
        print(f"Новый статус после изменения: {order.status}")

        return Response({'message': 'Заказ успешно отправлен', 'order': serializer.data}, status=status.HTTP_200_OK)

    # 12. PUT: Завершение или отклонение заявки
    def finalize_order(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

        # Проверяем, удалена ли заявка
        if order.status == 'deleted':
            return Response({'error': 'Заявка удалена и не может быть завершена или отклонена.'}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get('action')

        if not action:
            return Response({'error': 'Параметр action не указан.'}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем создателя и модератора из моковых пользователей
        moderator = get_mock_user()

        # Проверка, является ли текущий пользователь создателем или модератором
        if request.user.id not in [moderator.id]:
            return Response({'error': 'У вас нет прав для выполнения этого действия.'}, status=status.HTTP_403_FORBIDDEN)

        if action == 'completed':
            order.status = 'completed'
            order.completion_date = timezone.now()
        elif action == 'rejected':
            order.status = 'rejected'
            order.completion_date = timezone.now()
        else:
            return Response({'error': 'Некорректное значение параметра action.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order.save()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'Заявка успешно {action}.'}, status=status.HTTP_200_OK)

    # 13. DELETE: Удаление заявки
    def delete(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

        # Проверяем, удалена ли заявка
        if order.status == 'deleted':
            return Response({'error': 'Заявка уже удалена и не может быть удалена повторно.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'deleted'
        
        try:
            order.save()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Заявка успешно удалена.'}, status=status.HTTP_204_NO_CONTENT)  

class ServiceOrderView(APIView):
# 14. DELETE: Удаление услуги из заявки
    def delete(self, request, order_id, service_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)

        if order.status == 'deleted':
            return Response({'error': 'Заказ удален, нельзя удалить услуги'}, status=status.HTTP_400_BAD_REQUEST)

        service = get_object_or_404(DatacenterService, id=service_id)

        order_service = DatacenterOrderService.objects.filter(order=order, service=service).first()

        if order_service:
            if order_service.quantity > 1:
                # Уменьшаем количество услуги на 1
                order_service.quantity -= 1
                order_service.save()
                return Response({'message': 'Количество услуги уменьшено на 1'}, status=status.HTTP_200_OK)
            else:
                # Удаляем запись, если количество равно 1
                order_service.delete()
                return Response({'message': 'Услуга удалена из заказа'}, status=status.HTTP_204_NO_CONTENT)

        return Response({'error': 'Услуга не найдена в заказе'}, status=status.HTTP_404_NOT_FOUND)

    # 15. PUT: Изменение количества/порядка/значения услуги в заявке
    def put(self, request, order_id, service_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)
        service = get_object_or_404(DatacenterService, id=service_id)

        order_service = DatacenterOrderService.objects.filter(order=order, service=service).first()

        if order_service:
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

            order_service.quantity = new_quantity
            order_service.save()
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
    
