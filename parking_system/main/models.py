from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models as django_models


class ParkingSpot(models.Model):
    """Парковочное место"""
    number = models.CharField(max_length=10, unique=True, verbose_name="Номер места")
    zone = models.CharField(max_length=5, default='A', verbose_name="Зона")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"Место {self.number}"
    
    def is_occupied(self):
        """Проверка, занято ли место"""
        return self.sessions.filter(status='active').exists()
    is_occupied.boolean = True
    is_occupied.short_description = "Занято"

class Tariff(models.Model):
    """Тариф"""
    name = models.CharField(max_length=50, verbose_name="Название")
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Цена за час")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    def __str__(self):
        return self.name

class ParkingSession(models.Model):
    """Сессия парковки (въезд-выезд)"""
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    
    # Основные поля
    car_plate = models.CharField(max_length=15, verbose_name="Госномер")
    spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, 
                           related_name='sessions', verbose_name="Парковочное место")
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE, verbose_name="Тариф")
    
    # Время
    check_in = models.DateTimeField(auto_now_add=True, verbose_name="Время въезда")
    check_out = models.DateTimeField(null=True, blank=True, verbose_name="Время выезда")
    
    # Статус и стоимость
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                            default='active', verbose_name="Статус")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, 
                             verbose_name="Стоимость")
    
    class Meta:
        """Ограничения базы данных"""
        constraints = [
            models.UniqueConstraint(
                fields=['spot'],
                condition=models.Q(status='active'),
                name='unique_active_session_per_spot'
            )
        ]
        
        indexes = [
            models.Index(fields=['status', 'spot']),
            models.Index(fields=['check_in']),
        ]
    
    def clean(self):
        """Валидация перед сохранением"""
        errors = {}
        
        # 1. Если создаем новую активную сессию, проверяем что место свободно
        if self.status == 'active' and not self.pk:
            active_on_spot = ParkingSession.objects.filter(
                spot=self.spot, 
                status='active'
            ).exists()
            
            if active_on_spot:
                errors['spot'] = f'Место {self.spot.number} уже занято другой машиной!'
        
        # 2. Проверка времени - только если оба поля заполнены
        if self.check_out and self.check_in:
            if self.check_out <= self.check_in:
                errors['check_out'] = 'Время выезда должно быть позже времени въезда'
        
        # 3. Если указано время выезда, статус должен быть завершен
        if self.check_out and self.status == 'active':
            errors['status'] = 'Активная сессия не может иметь время выезда'
        
        if errors:
            raise ValidationError(errors)
    
    def calculate_cost(self):
        """Расчет стоимости парковки"""
        # Проверяем, что оба времени установлены
        if not self.check_out or not self.check_in:
            return 0
        
        # Проверяем тип данных (должны быть datetime)
        if not isinstance(self.check_out, type(self.check_in)):
            return 0
        
        # Разница во времени в часах
        try:
            duration = self.check_out - self.check_in
            hours = duration.total_seconds() / 3600
            
            # Округляем до 2 знаков
            total = float(hours) * float(self.tariff.price_per_hour)
            return round(total, 2)
        except (TypeError, AttributeError):
            return 0
    
    def complete(self, check_out_time=None):
        """Завершить сессию"""
        if self.status != 'active':
            raise ValidationError('Можно завершить только активную сессию')
        
        self.check_out = check_out_time or timezone.now()
        self.status = 'completed'
        self.cost = self.calculate_cost()
        self.save()
    
    def save(self, *args, **kwargs):
        """Сохранение с валидацией"""
        # Обновляем стоимость только если есть время выезда
        if self.check_out:
            self.cost = self.calculate_cost()
        
        # Выполняем валидацию
        self.full_clean()
        
        # Сохраняем
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.car_plate} на {self.spot.number} ({self.status})"
    
