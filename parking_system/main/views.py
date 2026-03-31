from django.shortcuts import render
from django.db.models import Count, Sum, Q, Exists, OuterRef
from django.utils import timezone
from .models import ParkingSpot, ParkingSession, Tariff
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import EntryForm, ExitForm
from django.db.models.functions import Round
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import ReservationForm
from .models import Reservation
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Payment




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
                return redirect('main')  
            try:
                
                ParkingSession.objects.create(
                    car_plate=car_plate,
                    spot=spot,
                    tariff=tariff,
                    status='active'  
                )
                
                messages.success(request, 
                    f'Автомобиль {car_plate} зарегистрирован на месте {spot.number}')
                return redirect('main')
                
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
                return redirect('main')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        form = ExitForm()
    
    
    return render(request, 'dashboard/exit.html', {
        'form': form,
        'session': session
    })


def quick_exit(request):
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        session = get_object_or_404(ParkingSession, id=session_id, status='active')
        # Устанавливаем время выезда сейчас
        session.check_out = timezone.now()
        # Рассчитываем стоимость
        session.cost = session.calculate_cost()
        session.save()
        return redirect('pay_session', session_id=session.id)
    else:
        active_sessions = ParkingSession.objects.filter(status='active')
        return render(request, 'dashboard/quick_exit.html', {'active_sessions': active_sessions})

def api_free_spots(request):
    free_spots = ParkingSpot.objects.filter(
        ~Exists(ParkingSession.objects.filter(spot=OuterRef('pk'), status='active'))
    ).values('id', 'number', 'zone')
    return JsonResponse({'free_spots': list(free_spots)})



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile')
    else:
        form = UserCreationForm()
    return render(request, 'dashboard/register.html', {'form': form})


# Проверка роли клиента (для бронирования)
def client_required(view_func):
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.profile.role == 'client':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Доступ только для клиентов")
        return redirect('main')
    return wrapped



def pay_session(request, session_id):
    session = get_object_or_404(ParkingSession, id=session_id, status='active')
    if request.method == 'POST':
        method = request.POST.get('payment_method', 'online')
        # Убедимся, что стоимость и время выезда установлены (на случай, если пришли без них)
        if not session.check_out:
            session.check_out = timezone.now()
        if session.cost == 0:
            session.cost = session.calculate_cost()
        session.save()
        payment = Payment.objects.create(
            session=session,
            amount=session.cost,
            method=method,
            status='paid'
        )
        session.status = 'completed'
        session.save()
        messages.success(request, f"Оплачено {payment.amount} руб. Чек №{payment.receipt_number}")
        return redirect('receipt', session_id=session.id)
    else:
        return render(request, 'dashboard/pay.html', {'session': session})

def receipt(request, session_id):
    """Отображение чека об оплате"""
    session = get_object_or_404(ParkingSession, id=session_id)
    payment = get_object_or_404(Payment, session=session)
    return render(request, 'dashboard/receipt.html', {'session': session, 'payment': payment})

@login_required
def profile(request):
    """Личный кабинет клиента"""
    reservations = Reservation.objects.filter(user=request.user).order_by('-start_time')
    active_sessions = ParkingSession.objects.filter(car_plate=request.user.username)  # если госномер совпадает с логином
    context = {
        'reservations': reservations,
        'active_sessions': active_sessions,
    }
    return render(request, 'dashboard/profile.html', context)

@login_required
@client_required
def create_reservation(request):
    """Создание бронирования"""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            try:
                reservation.full_clean()  # вызовет clean() модели
                reservation.save()
                messages.success(request, f"Место {reservation.spot.number} забронировано с {reservation.start_time} до {reservation.end_time}")
                return redirect('profile')
            except ValidationError as e:
                for msg in e.messages:
                    messages.error(request, msg)
    else:
        form = ReservationForm()
    return render(request, 'dashboard/reservation_form.html', {'form': form})

@login_required
def cancel_reservation(request, reservation_id):
    """Отмена бронирования"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    if reservation.status == 'active':
        reservation.status = 'cancelled'
        reservation.save()
        messages.success(request, "Бронирование отменено")
    else:
        messages.error(request, "Бронирование уже завершено или отменено")
    return redirect('profile')