from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models as django_models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver



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
            self.status == "completed"
        
        if errors:
            raise ValidationError(errors)
    
    def calculate_cost(self):
    
        # Проверяем, что оба времени установлены
        if not self.check_out or not self.check_in:
            return 0
    
    # Разница во времени в часах
        duration = self.check_out - self.check_in
        hours = duration.total_seconds() / 3600
    
    # Расчет стоимости с преобразованием в Decimal с 2 знаками
        from decimal import Decimal, ROUND_HALF_UP
    
    # Умножаем часы на цену
        total = Decimal(str(hours)) * self.tariff.price_per_hour
    
    # Округляем до 2 знаков после запятой
        total_rounded = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
        return total_rounded
    
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
    

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('operator', 'Оператор'),
        ('client', 'Клиент'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', verbose_name="Клиент")
    spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='reservations', verbose_name="Парковочное место")
    start_time = models.DateTimeField(verbose_name="Начало бронирования")
    end_time = models.DateTimeField(verbose_name="Конец бронирования")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['spot', 'start_time', 'end_time'],
                condition=models.Q(status='active'),
                name='unique_active_reservation_per_spot_time'
            )
        ]
    
    def __str__(self):
        return f"Бронь {self.spot.number} для {self.user.username} с {self.start_time} до {self.end_time}"
    def clean(self):
    # Проверка, что время начала раньше окончания
        if self.start_time >= self.end_time:
            raise ValidationError("Время начала должно быть раньше времени окончания")
    
        # Проверка пересечения с активными сессиями парковки
        overlapping_sessions = ParkingSession.objects.filter(
            spot=self.spot,
            status='active',
            check_in__lt=self.end_time,
            check_out__gt=self.start_time
        ).exists()
        if overlapping_sessions:
            raise ValidationError("На это место уже есть активная парковочная сессия в указанный период")
    
        # Проверка пересечения с другими активными бронями
        overlapping_reservations = Reservation.objects.filter(
            spot=self.spot,
            status='active',
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(id=self.id).exists()
        if overlapping_reservations:
            raise ValidationError("На это время уже есть активная бронь")
    

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Наличные'),
        ('card', 'Банковская карта'),
        ('online', 'Онлайн'),
    ]
    session = models.OneToOneField(
        'ParkingSession', 
        on_delete=models.CASCADE, 
        related_name='payment'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Ожидает'), ('paid', 'Оплачено')], 
        default='paid'   # при имитации сразу paid
    )
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='online')
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Генерация номера чека: PARK-ГГГГММДДЧЧММСС-IDсессии
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.receipt_number = f"PARK-{timestamp}-{self.session.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Чек {self.receipt_number} на сумму {self.amount} руб."

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создаёт профиль при создании нового пользователя"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохраняет профиль при сохранении пользователя"""
    instance.profile.save()
