from django.db import models
from django.contrib.auth.models import User

class ParkingSpot(models.Model):
    """Модель парковочного места"""
    number = models.CharField(max_length=10, unique=True)  # Уникальный номер: A-01, B-02
    zone = models.CharField(max_length=5, default='A')     # Зона парковки: A, B, C
    is_occupied = models.BooleanField(default=False)       # Статус занятости
    created_at = models.DateTimeField(auto_now_add=True)   # Дата создания записи
    
    def __str__(self):
        """Строковое представление объекта для админки"""
        return f"{self.number} ({'Занято' if self.is_occupied else 'Свободно'})"

class Tariff(models.Model):
    """Модель тарифа для расчета стоимости"""
    name = models.CharField(max_length=50)  # Название тарифа: "Стандартный", "Ночной"
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)  # Цена за час
    is_active = models.BooleanField(default=True)  # Активен ли тариф
    
    def __str__(self):
        return self.name

class ParkingSession(models.Model):
    """Модель сессии парковки (от въезда до выезда)"""
    
    # Варианты статусов сессии
    SESSION_STATUS = [
        ('active', 'Активна'),      # Машина на парковке
        ('completed', 'Завершена'), # Машина уехала, оплачено
        ('cancelled', 'Отменена'),  # Сессия отменена
    ]
    
    # Поля модели
    car_plate = models.CharField(max_length=15)  # Гос. номер: А123БВ77
    spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE)  # Связь с местом
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)     # Связь с тарифом
    check_in = models.DateTimeField(auto_now_add=True)    # Время въезда (автоматически)
    check_out = models.DateTimeField(null=True, blank=True)  # Время выезда (пока пустое)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Итоговая стоимость
    status = models.CharField(max_length=10, choices=SESSION_STATUS, default='active')  # Статус
    
    def calculate_cost(self):
        """Метод для расчета стоимости парковки с проверкой на None"""
        # ПРОВЕРЯЕМ, что оба времени установлены
        if self.check_out is None or self.check_in is None:
            return 0  # Если нет времени выезда или въезда - стоимость 0
        
        # ПРОВЕРЯЕМ, что check_out позже check_in
        if self.check_out <= self.check_in:
            return 0  # Если время выезда раньше въезда - стоимость 0
            
        # Вычисляем разницу во времени в часах
        time_difference = self.check_out - self.check_in
        hours = time_difference.total_seconds() / 3600
        
        # Стоимость = часы * цена за час, округляем до 2 знаков
        return round(float(hours) * float(self.tariff.price_per_hour), 2)
    
    def save(self, *args, **kwargs):
        """Переопределяем метод сохранения для авторасчета стоимости"""
        # ВСЕГДА пересчитываем стоимость при сохранении
        
        self.cost = self.calculate_cost()
        
        # Автоматически обновляем статус места
        if self.status == 'active':
            self.spot.is_occupied = True
        else:
            self.spot.is_occupied = False
        self.spot.save()
        
        # Вызываем оригинальный метод save
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.car_plate} - {self.spot.number}"