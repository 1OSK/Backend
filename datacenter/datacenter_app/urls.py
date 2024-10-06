from django.urls import path
from datacenter_app.views import *
from rest_framework.authtoken.views import obtain_auth_token
urlpatterns = [
    # Главная страница списка услуг
    path('', DatacenterServiceListView.as_view(), name='home'),
    
    # 1. GET: Список услуг с черновиком заказа пользователя
    path('services/', DatacenterServiceListView.as_view(), name='service_list_datacenter'),

    # 2. GET: Получение информации об одной услуге
    path('services/<int:service_id>/', DatacenterServiceDetailView.as_view(), name='service_detail_datacenter'),

    # 3. POST: Создание новой услуги
    path('services/create/', DatacenterServiceCreateView.as_view(), name='service_create_datacenter'),

    # 4. PUT: Обновление услуги
    path('services/<int:service_id>/update/', DatacenterServiceUpdateView.as_view(), name='service_update_datacenter'),

    # 5. DELETE: Удаление услуги (включая изображение)
    path('services/<int:service_id>/delete/', DatacenterServiceDeleteView.as_view(), name='service_delete_datacenter'),

    # 6. POST: Добавление услуги в черновик заказа
    path('services/<int:service_id>/add-to-draft/', AddServiceToDraftOrderView.as_view(), name='add_service_to_draft'),

    # 7. POST: Добавление или замена изображения услуги
    path('services/<int:service_id>/add-image/', AddImageToServiceView.as_view(), name='add_image_to_service'),
     # GET список заявок
     
    # 8. GET: Список заявок с фильтрацией
    path('orders/', DatacenterOrderListView.as_view(), name='order_list'),

    # 9. GET: Получение информации о заявке
    path('orders/<int:order_id>/', DatacenterOrderDetailView.as_view(), name='order_detail'),

    # 10. PUT: Обновление полей заявки
    path('orders/<int:order_id>/update/', UpdateOrderFieldsView.as_view(), name='update_order_fields'),

    # 11. PUT: Сформировать заявку (создатель)
    path('orders/<int:order_id>/submit/', SubmitOrderView.as_view(), name='submit_order'),

    # 12. PUT: Завершение или отклонение заявки (модератор)
    path('orders/<int:order_id>/finalize/', FinalizeOrRejectOrderView.as_view(), name='finalize_or_reject_order'),

    # 13. DELETE: Удаление заявки
    path('orders/<int:order_id>/delete/', DeleteOrderView.as_view(), name='delete_order'),
    
    # 14. DELETE: Удаление услуги из заявки
    path('orders/<int:order_id>/services/<int:service_id>/delete/', DeleteServiceFromOrderView.as_view(), name='delete_service_from_order'),

    # 15. PUT: Изменение количества/порядка/значения услуги в заявке
    path('orders/<int:order_id>/services/<int:service_id>/update/', UpdateServiceInOrderView.as_view(), name='update_service_in_order'),
    
    # 16. POST: Регистрация пользователя
    path('register/', RegisterUserDatacenter.as_view(), name='register_user'),
    
    # 17. PUT: Обновление профиля пользователя
    path('profile/update/<int:user_id>/', UpdateUserDatacenter.as_view(), name='update_user'),
    
    # 18. POST: Аутентификация пользователя
    path('login/', LoginUserDatacenter.as_view(), name='login_user'),  
    
    # 19. POST: Деавторизация пользователя
    path('logout/', LogoutUserDatacenter.as_view(), name='logout_user'),
]