from django.shortcuts import render
from django.db.models import Count, Sum, Q, Exists, OuterRef
from django.utils import timezone
from .models import ParkingSpot, ParkingSession, Tariff
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import EntryForm, ExitForm


def dashboard(request):
    
    parking_spots = ParkingSpot.objects.annotate(
        
        occupied_annotation=Exists(
            ParkingSession.objects.filter(
                spot=OuterRef('pk'),  # pk текущего ParkingSpot
                status='active'
            )
        )
    ).order_by('number')
    
    # Статистика для виджетов
    total_spots = parking_spots.count()
    
    # Считаем занятые места по аннотации
    occupied_spots = parking_spots.filter(occupied_annotation=True).count()
    free_spots = total_spots - occupied_spots
    
    # Выручка за сегодня
    today = timezone.now().date()
    today_revenue = ParkingSession.objects.filter(
        check_in__date=today, 
        status='completed'
    ).aggregate(total=Sum('cost'))['total'] or 0
    
    # Активные сессии с оптимизацией
    active_sessions = ParkingSession.objects.filter(
        status='active'
    ).select_related('spot', 'tariff')  # Загружаем связанные объекты за один запрос
    
    # Последние транзакции
    recent_transactions = ParkingSession.objects.filter(
        status='completed'
    ).select_related('spot', 'tariff').order_by('-check_out')[:10]
    
    context = {
        'parking_spots': parking_spots,
        'total_spots': total_spots,
        'occupied_spots': occupied_spots,
        'free_spots': free_spots,
        'today_revenue': today_revenue,
        'active_sessions': active_sessions,
        'recent_transactions': recent_transactions,
        'occupancy_rate': round((occupied_spots / total_spots * 100), 2) if total_spots > 0 else 0,
    }
    
    return render(request, 'dashboard/index.html', context)

def register_entry(request):
    """
    Обработчик регистрации въезда автомобиля.
    request - объект HTTP-запроса от пользователя.
    """
    if request.method == 'POST':  # Если форма была отправлена
        form = EntryForm(request.POST)  # Создаем форму с данными из POST-запроса
        
        if form.is_valid():  # Проверяем валидность формы
            
            car_plate = form.cleaned_data['car_plate']  
            spot = form.cleaned_data['spot']  
            
            
            tariff = Tariff.objects.filter(is_active=True).first()
            
            if not tariff:  
                messages.error(request, 'Нет активного тарифа!')
                return redirect('dashboard')  
            try:
                
                ParkingSession.objects.create(
                    car_plate=car_plate,
                    spot=spot,
                    tariff=tariff,
                    status='active'  
                )
                
                messages.success(request, 
                    f'Автомобиль {car_plate} зарегистрирован на месте {spot.number}')
                return redirect('dashboard')
                
            except Exception as e:  
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        # Если GET-запрос - создаем пустую форму
        form = EntryForm()
    
    
    return render(request, 'dashboard/entry.html', {'form': form})

def register_exit(request, session_id):
    """
    Обработчик регистрации выезда по ID сессии.
    session_id - идентификатор сессии из URL.
    """
    
    session = get_object_or_404(ParkingSession, id=session_id)
    
    if request.method == 'POST':
        form = ExitForm(request.POST)
        if form.is_valid() and form.cleaned_data['confirm']:
            
            try:
                
                session.complete()
                messages.success(request, 
                    f'Автомобиль {session.car_plate} выехал. Стоимость: {session.cost} ₽')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        form = ExitForm()
    
    
    return render(request, 'dashboard/exit.html', {
        'form': form,
        'session': session
    })

def quick_exit(request):
    
    
    active_sessions = ParkingSession.objects.filter(status='active')
    
    if request.method == 'POST':
        
        session_id = request.POST.get('session_id')
        
        session = get_object_or_404(ParkingSession, id=session_id)
        
        try:
            session.complete()
            messages.success(request, 
                f'Автомобиль {session.car_plate} выехал. Стоимость: {session.cost} ₽')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    
    return render(request, 'dashboard/quick_exit.html', {
        'active_sessions': active_sessions
    })