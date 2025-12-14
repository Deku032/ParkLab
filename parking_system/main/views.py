from django.shortcuts import render
from django.db.models import Count, Sum, Q, Exists, OuterRef
from django.utils import timezone
from .models import ParkingSpot, ParkingSession
from datetime import timedelta


def dashboard(request):
    # Оптимизированный запрос с аннотацией занятости
    parking_spots = ParkingSpot.objects.annotate(
        # Добавляем поле occupied_annotation в каждый объект
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