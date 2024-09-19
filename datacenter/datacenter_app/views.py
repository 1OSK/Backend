from django.shortcuts import render, get_object_or_404, redirect
from .models import DatacenterService, DatacenterOrder, DatacenterOrderService
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import Http404

def equipment_list_view_datacenter(request):
    max_price_query = request.GET.get('price_datacenter', '')
    equipment_queryset = DatacenterService.objects.filter(status='active')
    current_order = DatacenterOrder.objects.filter(creator=request.user, status='draft').first() if request.user.is_authenticated else None

    if max_price_query:
        try:
            max_price_value = int(max_price_query)
            equipment_queryset = equipment_queryset.filter(price__lte=max_price_value)
        except ValueError:
            pass

    total_quantity = sum(item.quantity for item in DatacenterOrderService.objects.filter(order=current_order)) if current_order else 0

    return render(request, 'datacenter_app/equipment_list_view_datacenter.html', {
        'equipment_list_datacenter': equipment_queryset,
        'current_order_id_datacenter': current_order.id if current_order else None,
        'equipment_count_in_order_datacenter': total_quantity,
        'max_price_query': max_price_query,
    })

def equipment_detail_view_datacenter(request, equipment_id):
    equipment_datacenter = get_object_or_404(DatacenterService, id=equipment_id)
    characteristics_list_datacenter = equipment_datacenter.description.split(',') if equipment_datacenter.description else []

    return render(request, 'datacenter_app/equipment_detail_view_datacenter.html', {
        'equipment_datacenter': equipment_datacenter,
        'characteristics_list_datacenter': characteristics_list_datacenter,
    })

def order_detail_view_datacenter(request, order_id_datacenter):
    selected_order_datacenter = get_object_or_404(DatacenterOrder, id=order_id_datacenter)
    equipment_in_order_datacenter = DatacenterOrderService.objects.filter(order=selected_order_datacenter)
    
    equipment_count_in_order_datacenter = sum(item.quantity for item in equipment_in_order_datacenter)
    
    equipment_data = [
        {
            'equipment_datacenter': item.service,
            'quantity_datacenter': item.quantity,
            'total_price_datacenter': item.service.price * item.quantity
        }
        for item in equipment_in_order_datacenter
    ]

    return render(request, 'datacenter_app/order_detail_view_datacenter.html', {
        'order_datacenter': selected_order_datacenter,
        'equipment_in_order_datacenter': equipment_data,
        'equipment_count_in_order_datacenter': equipment_count_in_order_datacenter,
        'total_price_datacenter': selected_order_datacenter.total_price,
    })

@login_required
def add_service_to_order_datacenter(request, service_id):
    service = get_object_or_404(DatacenterService, id=service_id)
    current_order = DatacenterOrder.objects.filter(creator=request.user, status='draft').first()

    if not current_order:
        current_order = DatacenterOrder.objects.create(creator=request.user, status='draft')

    order_service, created = DatacenterOrderService.objects.get_or_create(
        order=current_order,
        service=service,
        defaults={'quantity': 1}
    )

    if not created:
        order_service.quantity += 1
        order_service.save()

    current_order.calculate_total_price()  # Пересчет итоговой цены
    current_order.save()

    return redirect('equipment_list_view_datacenter')

@login_required
def delete_order_datacenter(request, order_id_datacenter):
    if request.method == 'POST':
        order = get_object_or_404(DatacenterOrder, id=order_id_datacenter, creator=request.user)
        order.status = 'deleted'
        order.save()
        return redirect('equipment_list_view_datacenter')
    else:
        raise Http404("Invalid request method")

@login_required
def complete_order_datacenter(request, order_id_datacenter):
    order = get_object_or_404(DatacenterOrder, id=order_id_datacenter)
    if request.method == 'POST':
        order.status = 'completed'
        order.completion_date = timezone.now()
        order.save()  # Итоговая цена пересчитается автоматически
        return redirect('equipment_list_view_datacenter')