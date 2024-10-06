from datetime import datetime
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
import json
from rest_framework.exceptions import NotFound
import re
from .minio import add_pic 
from django.conf import settings
from minio import Minio
from rest_framework.response import Response
from rest_framework import status
from .singleton import Creator, Moderator
from django.contrib.auth import authenticate, login, logout
from datacenter.settings import DEFAULT_FILE_STORAGE
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import UserSerializer
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from .serializers import DatacenterServiceSerializer, DatacenterOrderSerializer, DatacenterOrderServiceSerializer

# 1. GET: Список услуг с черновиком заказа пользователя
class DatacenterServiceListView(APIView):
    def get(self, request):
        services = DatacenterService.objects.all()
        
        # Здесь проверяем, аутентифицирован ли пользователь
        draft_order_id = None
        if request.user.is_authenticated:
            draft_order = DatacenterOrder.objects.filter(creator=request.user, status='draft').first()
            draft_order_id = draft_order.id if draft_order else None

        services_list = DatacenterServiceSerializer(services, many=True).data

        response_data = {
            'services': services_list,
            'draft_order_id': draft_order_id
        }

        return JsonResponse(response_data)

# 2. GET: Получение информации об одной услуге
class DatacenterServiceDetailView(APIView):
    def get(self, request, service_id):
        service = get_object_or_404(DatacenterService.objects.exclude(status='удалена'), id=service_id)
        service_data = DatacenterServiceSerializer(service).data
        return JsonResponse(service_data)

# 3. POST: Создание новой услуги
class DatacenterServiceCreateView(APIView):
    def post(self, request):
        # Сериализация данных для создания новой услуги
        serializer = DatacenterServiceSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()  # Сохраняем услугу, если данные корректны
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 4. PUT: Обновление услуги
class DatacenterServiceUpdateView(APIView):
    def put(self, request, service_id):
        # Получаем услугу, исключая удаленные услуги
        service = get_object_or_404(DatacenterService.objects.exclude(status='удалена'), id=service_id)
        
        # Применяем данные запроса через сериализатор
        serializer = DatacenterServiceSerializer(service, data=request.data, partial=True)

        # Если данные валидны, сохраняем изменения
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'message': 'Service updated successfully'})
        
        # Возвращаем ошибки валидации, если они есть
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# 5. DELETE: Удаление услуги (включая изображение)
class DatacenterServiceDeleteView(APIView):
    def delete(self, request, service_id):

        service = get_object_or_404(DatacenterService.objects.exclude(status='удалена'), id=service_id)

        # Удаление изображения из MinIO
        if service.image_url:
            client = Minio(
                endpoint=settings.AWS_S3_ENDPOINT_URL,
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                secure=settings.MINIO_USE_SSL
            )
            try:
                client.remove_object('something', f"{service.id}.png")  # Предполагается, что имя объекта соответствует ID
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        service.status = 'удалена'
        service.save()

        return JsonResponse({'message': 'Service deleted successfully'})

# 6. POST: Добавление услуги в черновик заказа
class AddServiceToDraftOrderView(APIView):
    def post(self, request, service_id):
        # Получение сервиса или возврат 404, если он не найден
        service = get_object_or_404(DatacenterService.objects.exclude(status='удалена'), id=service_id)
        
        # Используйте стандартного пользователя или создайте нового
        default_user = User.objects.get(username='admin_datacenter')  # Замените 'standard_user' на имя вашего пользователя

        # Получаем или создаем черновик заказа для стандартного пользователя
        draft_order, created = DatacenterOrder.objects.get_or_create(creator=default_user, status='draft')

        # Получаем или создаем услугу в черновике
        order_service, created = DatacenterOrderService.objects.get_or_create(order=draft_order, service=service)

        if created:
            order_service.quantity = 1
        else:
            order_service.quantity += 1
            
        order_service.save()

        # Пересчитываем общую стоимость черновика
        draft_order.calculate_total_price()

        return JsonResponse({'message': 'Service added to draft order'})

# 7. POST: Добавление или замена изображения услуги
class AddImageToServiceView(APIView):
    def post(self, request, service_id):
        
        

        service = get_object_or_404(DatacenterService.objects.exclude(status='удалена'), id=service_id)

        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image provided'}, status=400)

        image = request.FILES['image']

        # Добавление изображения через minio.py
        response = add_pic(service, image)
        if response.status_code != 200:
            return response

        return JsonResponse({'message': 'Image added/updated successfully'})

# 8. GET: Список заявок с фильтрацией
class DatacenterOrderListView(APIView):
    def get(self, request):
        # Получаем параметры фильтрации из запроса
        status_filter = request.GET.get('status')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Начинаем с выборки всех заказов
        orders = DatacenterOrder.objects.all()  # Получаем все заказы

        # Применяем фильтрацию по статусу, если он указан
        if status_filter:
            orders = orders.filter(status=status_filter)  # Фильтруем по статусу

        # Применяем фильтрацию по дате, если указаны обе даты
        if start_date and end_date:
            try:
                # Преобразуем строки в объекты даты
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d')
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d')
                orders = orders.filter(creation_date__range=[start_date, end_date])  # Фильтруем по дате
            except ValueError:
                return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD.'}, status=400)

        # Сериализуем отфильтрованные заказы
        serializer = DatacenterOrderSerializer(orders, many=True)
        return Response({'orders': serializer.data})

# 9. GET: Получение информации о заявке
class DatacenterOrderDetailView(APIView):
    def get(self, request, order_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)

        # Проверка статуса заказа
        if order.status == 'deleted':
            raise NotFound({'error': 'Заказ не найден'})

        # Получение всех услуг, связанных с заказом через промежуточную модель
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

# 10. PUT: Обновление полей заявки
class UpdateOrderFieldsView(APIView):
    def put(self, request, order_id):
        # Получаем заказ или возвращаем 404, если он не найден
        order = get_object_or_404(DatacenterOrder, id=order_id)

        # Получаем параметры из URL
        status_param = request.query_params.get('status')
        delivery_address_param = request.query_params.get('delivery_address')
        delivery_time_param = request.query_params.get('delivery_time')

        # Обновляем поля заказа на основе переданных параметров
        if status_param is not None:
            order.status = status_param  # Обновляем статус, если он передан
        if delivery_address_param is not None:
            order.delivery_address = delivery_address_param  # Обновляем адрес доставки
        if delivery_time_param is not None:
            order.delivery_time = delivery_time_param  # Обновляем время доставки
        
        # Вычисляем общую стоимость, если статус изменился
        if status_param is not None:
            order.calculate_total_price()

        # Сохраняем изменения
        order.save()

        return Response({'message': 'Order updated successfully'}, status=status.HTTP_200_OK)

# 11. PUT: Отправка заявки
class SubmitOrderView(APIView):
    def put(self, request, order_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)

        # Установите создателя заказа как константу
        order.creator = order.creator  # Здесь можно задать создателя, если это требуется по логике
        
        

        # Проверьте обязательные поля, например, адрес доставки и время доставки
        if not order.delivery_address or not order.delivery_time:
            return Response({'error': 'Missing required fields'}, status=400)

        # Установите статус заказа как 'сформирован'
        order.status = 'formed'  # Убедитесь, что статус соответствует вашим требованиям
        order.save()  # Сохраните изменения в заказе
        return Response({'message': 'Order submitted successfully'}, status=200)

# 12. PUT: Завершение или отклонение заявки
class FinalizeOrRejectOrderView(APIView):
    def put(self, request, order_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)

        
       

        # Логирование текущего статуса
        print(f'Current status: {order.status}')

        data = request.data
        action = data.get('action')

        if action == 'completed':
            order.status = 'completed'
            order.completed_at = datetime.now()
            order.calculate_total_price()
        elif action == 'rejected':
            order.status = 'rejected'

        # Логирование статуса перед сохранением
        print(f'Updating status to: {order.status}')
        
        order.save()
        return Response({'message': f'Order {action}d successfully'})
# 13. DELETE: Удаление заявки
class DeleteOrderView(APIView):
    def delete(self, request, order_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)

        order.status = 'deleted'
        order.save()
        return Response({'message': 'Order deleted successfully'}, status=204)

# 14. DELETE: Удаление услуги из заявки
class DeleteServiceFromOrderView(APIView):
    def delete(self, request, order_id, service_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)

        if order.status == 'удалена':
            return Response({'error': 'Order is deleted, cannot remove services'}, status=400)

        service = get_object_or_404(DatacenterService, id=service_id)
        order_service = DatacenterOrderService.objects.filter(order=order, service=service).first()

        if order_service:
            order_service.delete()
            return Response({'message': 'Service removed from order'}, status=204)

        return Response({'error': 'Service not found in order'}, status=404)

# 15. PUT: Изменение количества/порядка/значения услуги в заявке
class UpdateServiceInOrderView(APIView):
    def put(self, request, order_id, service_id):
        order = get_object_or_404(DatacenterOrder, id=order_id)
        service = get_object_or_404(DatacenterService, id=service_id)

        order_service = DatacenterOrderService.objects.filter(order=order, service=service).first()

        if order_service:
            data = request.data
            new_quantity = data.get('quantity')

            if new_quantity is None:
                return Response({'error': 'No quantity provided'}, status=400)

            try:
                new_quantity = int(new_quantity)
                if new_quantity < 1:
                    return Response({'error': 'Quantity must be positive'}, status=400)
            except ValueError:
                return Response({'error': 'Invalid quantity'}, status=400)

            order_service.quantity = new_quantity
            order_service.save()
            return Response({'message': 'Service quantity updated in order'}, status=200)

        return Response({'error': 'Service not found in order'}, status=404)

# 16. POST: Регистрация пользователя
class RegisterUserDatacenter(APIView):
    def post(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response({'error': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email)
        return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)

# 17. PUT: Обновление информации о пользователе
class UpdateUserDatacenter(APIView):

    def put(self, request, user_id):
        user = get_object_or_404(User, id=user_id)  # Получаем пользователя по ID
        data = request.data

        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 18. POST: Вход пользователя
class LoginUserDatacenter(APIView):
    def post(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({'message': 'User logged in successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

# 19. POST: Выход пользователя
class LogoutUserDatacenter(APIView):

    def post(self, request):
        logout(request)
        return Response({'message': 'User logged out successfully'}, status=status.HTTP_200_OK)