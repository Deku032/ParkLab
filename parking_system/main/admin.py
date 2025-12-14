from django.contrib import admin
from django.utils.html import format_html
from .models import ParkingSpot, Tariff, ParkingSession

# 1. Админка для парковочных мест
@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'created_at', 'display_occupied']
    list_filter = ['zone']
    search_fields = ['number']
    readonly_fields = ['created_at']
    
    def display_occupied(self, obj):
        """Простое отображение занятости"""
        if obj.is_occupied():
            return format_html('<span style="color: red;">● Занято</span>')
        return format_html('<span style="color: green;">○ Свободно</span>')
    display_occupied.short_description = 'Статус'

# 2. Админка для тарифов (максимально простая)
@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_per_hour', 'is_active']
    list_editable = ['price_per_hour', 'is_active']
    list_filter = ['is_active']

# 3. Админка для сессий парковки
@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_display = ['car_plate', 'spot', 'tariff', 'check_in', 'check_out', 'cost', 'status']
    list_filter = ['status', 'spot__zone']
    search_fields = ['car_plate']
    
    # Поля только для чтения
    readonly_fields = ['check_in', 'cost']
    
    # Динамические поля только для чтения
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'active':
            return self.readonly_fields + ['spot']
        return self.readonly_fields
    
    # Форма создания: показываем только свободные места
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "spot":
            # Только при создании новой сессии
            if not request.resolver_match.kwargs.get('object_id'):
                # Находим занятые места
                occupied_spots = ParkingSession.objects.filter(
                    status='active'
                ).values_list('spot_id', flat=True)
                # Показываем все места, кроме занятых
                kwargs["queryset"] = ParkingSpot.objects.exclude(
                    id__in=occupied_spots
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)