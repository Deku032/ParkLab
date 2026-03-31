from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='main'),
    path('entry/', views.register_entry, name='register_entry'),
    path('exit/', views.quick_exit, name='quick_exit'),
    path('exit/<int:session_id>/', views.register_exit, name='register_exit_detail'),
    path('api/free_spots/', views.api_free_spots, name='api_free_spots'),

]