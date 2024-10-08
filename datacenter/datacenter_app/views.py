
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
from .serializers import DatacenterServiceSerializer, DatacenterOrderSerializer, DatacenterOrderServiceSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action

class DatacenterServiceViewSet(viewsets.ModelViewSet):
    queryset = DatacenterService.objects.all()
    serializer_class = DatacenterServiceSerializer

    def get_current_user(self):
        """Получаем текущего пользователя (мокового пользователя)"""
        mock_user = get_mock_user()

        
        if not isinstance(mock_user, User):
            raise ValueError("Неверный пользователь")

        return mock_user

    def list(self, request):
        try:
            mock_user = self.get_current_user()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
        min_price = request.GET.get('datacenter_min_price')
        max_price = request.GET.get('datacenter_max_price')

        services = self.queryset

        
        if min_price:
            try:
                min_price = float(min_price)  
                services = services.filter(price__gte=min_price)
            except ValueError:
                return Response({"error": "Некорректное значение для минимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

        if max_price:
            try:
                max_price = float(max_price)  
                services = services.filter(price__lte=max_price)
            except ValueError:
                return Response({"error": "Некорректное значение для максимальной цены"}, status=status.HTTP_400_BAD_REQUEST)

        
        draft_order, created = DatacenterOrder.objects.get_or_create(
            creator=mock_user,
            status='draft'
        )

        
        draft_order_id = draft_order.id

        services_list = self.get_serializer(services, many=True).data

        response_data = {
            'services': services_list,
            'draft_order_id': draft_order_id
        }

        return Response(response_data)

    # 2. GET: Получение информации об одной услуге
    def retrieve(self, request, pk=None):
        service = get_object_or_404(self.queryset.exclude(status='удалена'), id=pk)
        service_data = self.get_serializer(service).data
        return Response(service_data)

    # 3. POST: Создание новой услуги с изображением
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_service = serializer.save()

        
        if 'image' in request.FILES:
            image = request.FILES['image']
            response = add_pic(new_service, image)
            if response.status_code != status.HTTP_200_OK:
                return response

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # 4. PUT: Обновление услуги с изображением
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # Получаем объект услуги для обновления

       
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_service = serializer.save()

        
        if 'image' in request.FILES:
            image = request.FILES['image']
            response = add_pic(updated_service, image)
            if isinstance(response, Response) and response.status_code != status.HTTP_200_OK:
                return response  

            
            if isinstance(response.data, dict) and "image_url" in response.data:
                updated_service.image_url = response.data["image_url"]
                updated_service.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    # 5. DELETE: Удаление услуги
    def destroy(self, request, pk=None):
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

    # 6. POST: Добавление услуги в черновик заказа
    @action(detail=True, methods=['post'], url_path='add-to-draft')
    def add_to_draft(self, request, pk=None):
        
        service = get_object_or_404(DatacenterService, id=pk)

        
        try:
            mock_user = self.get_current_user()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
        draft_order, created = DatacenterOrder.objects.get_or_create(
            creator=mock_user,
            status='draft'
        )

        
        order_service, created = DatacenterOrderService.objects.get_or_create(
            order=draft_order, 
            service=service
        )

        
        if created:
            order_service.quantity = 1
        else:
            order_service.quantity += 1
            
        order_service.save()

       
        draft_order.total_price = sum(order_service.quantity * order_service.service.price for order_service in draft_order.datacenterorderservice_set.all())
        draft_order.save()

        
        serializer = DatacenterOrderSerializer(draft_order)

        return Response(
            {'message': 'Услуга добавлена в черновик заказа', 'draft_order': serializer.data}, 
            status=status.HTTP_201_CREATED
        )

    # 7. POST: Добавление или замена изображения услуги
    @action(detail=True, methods=['post'], url_path='add-image')
    def add_image(self, request, pk=None):
        service = get_object_or_404(self.queryset.exclude(status='удалена'), id=pk)

        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=400)

        image = request.FILES['image']

        
        response = add_pic(service, image)
        if response.status_code != 200:
            return response

        return Response({'message': 'Image added/updated successfully'})

class DatacenterOrderViewSet(viewsets.ViewSet):

    # 8. GET: Список заявок с фильтрацией
    def list(self, request):
        
        moderator = get_mock_user()

        
        status_filter = request.GET.get('datacenter_status')
        start_date = request.GET.get('datacenter_start_date')
        end_date = request.GET.get('datacenter_end_date')

        
        orders = DatacenterOrder.objects.exclude(status='deleted')

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
    
   # 10. PUT: Обновление полей заявки
    def update(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

        serializer = DatacenterOrderSerializer(order, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Order updated successfully', 'order_id': order.id}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 11. PUT: Отправка заявки (отдельный маршрут)
    @action(detail=True, methods=['put'], url_path='submit')
    def submit_order(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

       
        creator = get_mock_user()  

        
        
        if order.delivery_address is None or order.delivery_time is None:
            return Response({'error': 'Необходимо указать адрес доставки и время.'}, status=status.HTTP_400_BAD_REQUEST)

       
        order.status = 'formed'
        order.save()

        return Response({'message': 'Order submitted successfully'}, status=status.HTTP_200_OK)

    # 12. PUT: Завершение или отклонение заявки
    @action(detail=True, methods=['put'], url_path='finalize')
    def finalize_order(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

        action = request.data.get('action')

        if not action:
            return Response({'error': 'Missing action parameter'}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем создателя и модератора из моковых пользователей
        moderator = get_mock_user()

        # Проверка, является ли текущий пользователь создателем или модератором
        if request.user.id not in [moderator.id]:
            return Response({'error': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

        if action == 'completed':
            order.status = 'completed'
            order.completion_date = timezone.now()  
        elif action == 'rejected':
            order.status = 'rejected'
            order.completion_date = timezone.now()  
        else:
            return Response({'error': 'Invalid action provided'}, status=status.HTTP_400_BAD_REQUEST)

        order.save()
        return Response({'message': f'Order {action}d successfully'}, status=status.HTTP_200_OK)

        # 13. DELETE: Удаление заявки
    def destroy(self, request, pk=None):
        order = get_object_or_404(DatacenterOrder, id=pk)

        
        order.status = 'deleted'  
        order.save()

        return Response({'message': 'Order deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class ServiceOrderViewSet(viewsets.ViewSet):
    # 14. DELETE: Удаление услуги из заявки
    def destroy(self, request, order_id, service_id):
        
        order = get_object_or_404(DatacenterOrder, id=order_id)

        
        if order.status == 'deleted':
            return Response({'error': 'Заказ удален, нельзя удалить услуги'}, status=status.HTTP_400_BAD_REQUEST)

        
        service = get_object_or_404(DatacenterService, id=service_id)

       
        order_service = DatacenterOrderService.objects.filter(order=order, service=service).first()

        
        if order_service:
            order_service.delete()
            return Response({'message': 'Услуга удалена из заказа'}, status=status.HTTP_204_NO_CONTENT)

        return Response({'error': 'Услуга не найдена в заказе'}, status=status.HTTP_404_NOT_FOUND)

    # 15. PUT: Изменение количества/порядка/значения услуги в заявке
    def update(self, request, order_id, service_id):
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


class UserViewSet(viewsets.ViewSet):
    # 16. POST: Регистрация пользователя
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response({'error': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)

       
        user = User.objects.create_user(username=username, password=password, email=email)
        return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)

    # 17. PUT: Обновление информации о пользователе
    @action(detail=True, methods=['put'], url_path='update')
    def update_user(self, request, pk=None):
        user = get_object_or_404(User, id=pk)  
        data = request.data

        
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        if 'password' in data:
            user.set_password(data['password'])
        user.save()

        return Response({'message': 'User updated successfully'}, status=status.HTTP_200_OK)

    # 18. POST: Вход пользователя
    @action(detail=False, methods=['post'], url_path='login')
    def login_user(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')

        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({'message': 'User logged in successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    # 19. POST: Выход пользователя
    @action(detail=False, methods=['post'], url_path='logout')
    def logout_user(self, request):
        logout(request)
        return Response({'message': 'User logged out successfully'}, status=status.HTTP_200_OK)