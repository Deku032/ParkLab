from django import forms
from .models import ParkingSpot, ParkingSession, Tariff

class EntryForm(forms.Form):
    """Форма для регистрации въезда"""
    car_plate = forms.CharField(
        label='Госномер автомобиля',
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'А123АА77'
        })
    )
    
    spot = forms.ModelChoiceField(
        label='Парковочное место',
        queryset=ParkingSpot.objects.none(),  # Будет установлен в __init__
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только свободные места
        occupied_spots = ParkingSession.objects.filter(
            status='active'
        ).values_list('spot_id', flat=True)
        free_spots = ParkingSpot.objects.exclude(id__in=occupied_spots)
        self.fields['spot'].queryset = free_spots

class ExitForm(forms.Form):
    """Форма для регистрации выезда (с подтверждением)"""
    confirm = forms.BooleanField(
        label='Подтвердить выезд',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )