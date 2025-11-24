from django.contrib import admin
from .models import ParkingSpot, Tariff, ParkingSession


@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = ["number","zone","is_occupied","created_at"]
    list_filter = ["zone","is_occupied"]
    list_editable = ["is_occupied"]
    search_fields = ["number"]

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ["name","price_per_hour","is_active"]
    list_editable = ["price_per_hour", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]

@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_display = ["car_plate", "spot","tariff","check_in","check_out","cost","status"]
    list_filter = ["spot", "tariff","status"]
    search_fields = ["car_plate"]
    list_editable = ["status"]

    readonly_fields = ["check_in", "cost"]
    
    # Настройки для формы создания
    def get_readonly_fields(self, request, obj=None):
        # При создании объекта check_in тоже только для чтения
        if obj:  # obj is None when creating
            return self.readonly_fields
        return self.readonly_fields + ['check_in']