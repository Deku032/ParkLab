from django.shortcuts import render
from django.db.models import Count, Sum
from django.utils import timezone
from .models import ParkingSpot, ParkingSession
from datetime import timedelta


def dashboard(request):
    # Получаем все места
    parking_spots = ParkingSpot.objects.all().order_by('number')
    
    # Статистика для виджетов
    total_spots = parking_spots.count()
    occupied_spots = parking_spots.filter(is_occupied=True).count()
    free_spots = total_spots - occupied_spots
    
    # Выручка за сегодня
    today = timezone.now().date()
    today_revenue = ParkingSession.objects.filter(
        check_in__date=today, 
        status='completed'
    ).aggregate(total=Sum('cost'))['total'] or 0
    
    # Активные сессии
    active_sessions = ParkingSession.objects.filter(status='active')
    
    # Последние транзакции
    recent_transactions = ParkingSession.objects.filter(
        status='completed'
    ).order_by('-check_out')[:10]
    
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