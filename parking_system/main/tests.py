from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from main.models import ParkingSpot, Tariff, ParkingSession
from django.utils import timezone
from django.urls import reverse
from main.forms import EntryForm, ExitForm
import json
import datetime

class ParkingModelTests(TestCase):
    def setUp(self):
        self.spot = ParkingSpot.objects.create(number="A-01", zone="A")
        self.tariff = Tariff.objects.create(
            name="Стандарт", 
            price_per_hour=100,
            is_active=True
        )
    
    def test_cannot_create_two_active_sessions(self):
        """Проверка уникальности активных сессий на месте"""
        # Первая активная сессия
        session1 = ParkingSession.objects.create(
            car_plate="А123АА77",
            spot=self.spot,
            tariff=self.tariff,
            status='active'
        )
        
        # Вторая должна вызвать ошибку
        session2 = ParkingSession(
            car_plate="В456ВВ77",
            spot=self.spot,
            tariff=self.tariff,
            status='active'
        )
        
        with self.assertRaises(ValidationError):
            session2.full_clean()
    
    def test_cost_calculation(self):
        """Проверка расчета стоимости"""
        session = ParkingSession.objects.create(
            car_plate="А123АА77",
            spot=self.spot,
            tariff=self.tariff,
            check_in=timezone.now(),
            check_out=timezone.now() + datetime.timedelta(hours=2)
        )
        
        expected_cost = 200  # 2 часа * 100 руб/час
        self.assertEqual(session.calculate_cost(), expected_cost)
    
    def test_spot_occupancy(self):
        """Проверка свойства занятости места"""
        self.assertFalse(self.spot.is_occupied())
        
        ParkingSession.objects.create(
            car_plate="А123АА77",
            spot=self.spot,
            tariff=self.tariff,
            status='active'
        )
        
        self.assertTrue(self.spot.is_occupied())

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.spot = ParkingSpot.objects.create(number="A-01", zone="A")
        self.tariff = Tariff.objects.create(name="Стандарт", price_per_hour=100)
        

    
    def test_register_entry_post(self):
        """Проверка регистрации въезда"""
        response = self.client.post(reverse('register_entry'), {
            'car_plate': 'А123АА77',
            'spot': self.spot.id
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(ParkingSession.objects.count(), 1)
    
    def test_api_endpoints(self):
        """Проверка API endpoints"""
        response = self.client.get('/api/free_spots/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('free_spots', data)

class FormTests(TestCase):
    def test_entry_form_with_occupied_spot(self):
        """Форма не должна позволять выбрать занятое место"""
        spot = ParkingSpot.objects.create(number="A-01")
        tariff = Tariff.objects.create(name="Стандарт", price_per_hour=100)
        
        # Создаем активную сессию
        ParkingSession.objects.create(
            car_plate="А123АА77",
            spot=spot,
            tariff=tariff,
            status='active'
        )
        
        form = EntryForm()
        # Место не должно быть в queryset
        self.assertNotIn(spot, form.fields['spot'].queryset)