from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-appointment/', views.add_appointment, name='add_appointment'),
    path('appointment/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),

    # API Endpoints
    path('api/calendar-data/', views.get_calendar_data, name='calendar_data'),
    path('api/team-schedule/', views.get_team_schedule, name='team_schedule'),
    path('api/services/<int:master_id>/', views.get_services_by_master, name='get_services_by_master'),

    # Управління вихідними та перервами
    path('days-off/add/', views.add_day_off, name='add_day_off'),
    path('days-off/delete/<int:day_off_id>/', views.delete_day_off, name='delete_day_off'),
    path('breaks/add/', views.add_break, name='add_break'),
    path('breaks/delete/<int:break_id>/', views.delete_break, name='delete_break'),
    path('master/toggle/<int:master_id>/', views.toggle_master_status, name='toggle_master_status'),

    # Керування салоном (Адмін-панель) з безпечними URL-префіксами
    path('salon-admin/master/add/', views.add_master, name='add_master'),
    path('salon-admin/master/delete/<int:master_id>/', views.delete_master, name='delete_master'),
    path('salon-admin/specialty/add/', views.add_specialty, name='add_specialty'),
    path('salon-admin/specialty/delete/<int:specialty_id>/', views.delete_specialty, name='delete_specialty'),
    path('salon-admin/service/add/', views.add_service, name='add_service'),
    path('salon-admin/service/delete/<int:service_id>/', views.delete_service, name='delete_service'),
]