from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.dashboard, name='main'),
    path('entry/', views.register_entry, name='register_entry'),
    path('exit/', views.quick_exit, name='quick_exit'),
    path('exit/<int:session_id>/', views.register_exit, name='register_exit_detail'),
    path('api/free_spots/', views.api_free_spots, name='api_free_spots'),
    path('profile/', views.profile, name='profile'),
    path('reservation/create/', views.create_reservation, name='create_reservation'),
    path('reservation/cancel/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('login/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='main'), name='logout'),
    path('register/', views.register, name='register'),
    path('session/<int:session_id>/pay/', views.pay_session, name='pay_session'),
    path('session/<int:session_id>/receipt/', views.receipt, name='receipt'),

]