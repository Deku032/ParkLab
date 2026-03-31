from django import forms
from .models import ParkingSpot, ParkingSession, Tariff, Reservation
from django.utils import timezone

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



class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['spot', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только свободные места (без активных сессий и броней в будущем)
        # Но для простоты оставим все места, валидация будет в clean
        self.fields['spot'].queryset = ParkingSpot.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        spot = cleaned_data.get('spot')
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        
        if start and end and start >= end:
            raise forms.ValidationError("Время начала должно быть раньше времени окончания")
        
        # Дополнительные проверки пересечений можно оставить в модели, но форма тоже может их делать
        return cleaned_data