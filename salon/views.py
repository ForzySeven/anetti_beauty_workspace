import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
import random
from .models import Master, Appointment, Service, Specialty, DayOff, BreakTime, MASTER_COLORS_POOL


def get_services_by_master(request, master_id):
    """Отримання послуг тільки тих спеціальностей, якими володіє обраний майстер"""
    master = get_object_or_404(Master, id=master_id)
    services = Service.objects.filter(specialty__in=master.specialties.all()).distinct()
    data = [{"id": s.id, "name": f"{s.name} ({s.specialty.name})"} for s in services]
    return JsonResponse({"services": data})


def get_calendar_data(request):
    """Повертає записи, перерви, вихідні, дні з перервами та унікальні кольори майстрів на обрану дату"""
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    masters = Master.objects.filter(is_active=True)

    used_colors = set(m.color for m in masters if m.color)
    available_colors = [c for c in MASTER_COLORS_POOL if c not in used_colors]

    def generate_unique_color():
        while True:
            color = f"#{random.randint(50, 230):02x}{random.randint(50, 230):02x}{random.randint(50, 230):02x}"
            if color not in used_colors:
                return color

    master_color_map = {}
    for m in masters:
        if not m.color:
            if available_colors:
                m.color = available_colors.pop(0)
            else:
                m.color = generate_unique_color()
            m.save()
            used_colors.add(m.color)

        master_color_map[m.id] = {
            'id': m.id,
            'name': m.name,
            'color': m.color
        }

    # 1. Записи клієнтів
    appointments = Appointment.objects.filter(date=date_str).select_related('master', 'service')
    app_list = []
    for app in appointments:
        app_list.append({
            'type': 'appointment',
            'id': app.id,
            'client_name': app.client_name,
            'client_phone': app.client_phone or 'Не вказано',
            'master_id': app.master.id,
            'master_name': app.master.name,
            'service_name': app.service.name,
            'start_time': app.start_time.strftime('%H:%M') if hasattr(app.start_time, 'strftime') else str(app.start_time)[:5],
            'color': master_color_map.get(app.master.id, {}).get('color', '#e11d48')
        })

    # 2. Перерви майстрів
    breaks = BreakTime.objects.filter(date=date_str).select_related('master')
    break_list = []
    for b in breaks:
        break_list.append({
            'type': 'break',
            'id': b.id,
            'master_id': b.master.id,
            'master_name': b.master.name,
            'start_time': b.start_time.strftime('%H:%M') if hasattr(b.start_time, 'strftime') else str(b.start_time)[:5],
            'end_time': b.end_time.strftime('%H:%M') if hasattr(b.end_time, 'strftime') else str(b.end_time)[:5],
            'color': '#f97316'
        })

    # Унікальні дати поточного місяця з перервами
    month_prefix = date_str[:7]
    month_breaks = BreakTime.objects.filter(date__startswith=month_prefix).values_list('date', flat=True).distinct()
    days_with_breaks = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in month_breaks]

    # Вихідні дні майстрів у цьому місяці (з урахуванням фільтра конкретного майстра)
    master_filter_id = request.GET.get('master_id')
    days_off_qs = DayOff.objects.filter(date__startswith=month_prefix)
    if master_filter_id and master_filter_id != 'all':
        days_off_qs = days_off_qs.filter(master_id=master_filter_id)

    month_days_off = days_off_qs.values_list('date', flat=True).distinct()
    days_off_list = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in month_days_off]

    return JsonResponse({
        'masters': list(master_color_map.values()),
        'appointments': app_list,
        'breaks': break_list,
        'days_with_breaks': days_with_breaks,
        'days_off': days_off_list
    })


def get_team_schedule(request):
    """Повертає список майстрів та дати їхніх вихідних"""
    masters = list(Master.objects.filter(is_active=True).values('id', 'name', 'color'))

    days_off_qs = DayOff.objects.all().values('master_id', 'date')

    days_off_map = {}
    for do in days_off_qs:
        m_id = do['master_id']
        date_str = do['date'].strftime('%Y-%m-%d') if hasattr(do['date'], 'strftime') else str(do['date'])
        if m_id not in days_off_map:
            days_off_map[m_id] = []
        days_off_map[m_id].append(date_str)

    return JsonResponse({
        'masters': masters,
        'days_off_map': days_off_map
    })


def login_view(request):
    if request.method == "POST":
        master_id = request.POST.get("master_id")
        master = get_object_or_404(Master, id=master_id)
        request.session["master_id"] = master.id
        request.session["master_name"] = master.name
        return redirect("dashboard")

    masters = Master.objects.filter(is_active=True)
    return render(request, "salon/login.html", {"masters": masters})


def logout_view(request):
    request.session.flush()
    return redirect("login")


def dashboard_view(request):
    if "master_id" not in request.session:
        return redirect("login")

    current_master = Master.objects.get(id=request.session["master_id"])
    active_masters = Master.objects.filter(is_active=True)
    all_masters = Master.objects.all().prefetch_related('specialties')
    specialties = Specialty.objects.all()
    services = Service.objects.select_related('specialty').all()
    days_off = DayOff.objects.all().order_by("date")
    breaks = BreakTime.objects.all().order_by("date", "start_time")

    # Розрахунок діапазону минулого місяця
    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - datetime.timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)

    # Історія записів минулого місяця (посортовані від ранішої до пізнішої дати та часу)
    past_month_appointments = Appointment.objects.filter(
        date__gte=first_day_prev_month,
        date__lte=last_day_prev_month
    ).select_related('master', 'service').order_by("date", "start_time")

    context = {
        "current_master": current_master,
        "active_masters": active_masters,
        "all_masters": all_masters,
        "specialties": specialties,
        "services": services,
        "days_off": days_off,
        "breaks": breaks,
        "past_month_appointments": past_month_appointments,
    }
    return render(request, "salon/dashboard.html", context)


def add_appointment(request):
    if request.method == "POST" and "master_id" in request.session:
        current_master = Master.objects.get(id=request.session["master_id"])

        client_name = request.POST.get("client_name")
        client_phone = request.POST.get("client_phone")
        target_master_id = request.POST.get("master_id")
        service_id = request.POST.get("service_id")
        date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time") or start_time

        if not service_id:
            return redirect("dashboard")

        Appointment.objects.create(
            client_name=client_name,
            client_phone=client_phone,
            master_id=target_master_id,
            service_id=service_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            created_by=current_master
        )
    return redirect("dashboard")


def cancel_appointment(request, appointment_id):
    if "master_id" in request.session:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        appointment.delete()
    return redirect("dashboard")


def add_day_off(request):
    if request.method == "POST" and "master_id" in request.session:
        master_id = request.POST.get("master_id")
        date = request.POST.get("date")
        DayOff.objects.get_or_create(master_id=master_id, date=date)
    return redirect("dashboard")


def delete_day_off(request, day_off_id):
    if "master_id" in request.session:
        day_off = get_object_or_404(DayOff, id=day_off_id)
        day_off.delete()
    return redirect("dashboard")


def add_break(request):
    """Створення перерви ТІЛЬКИ для поточного авторизованого майстра"""
    if request.method == "POST" and "master_id" in request.session:
        current_master = Master.objects.get(id=request.session["master_id"])
        date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        if date and start_time and end_time:
            BreakTime.objects.create(
                master=current_master,
                date=date,
                start_time=start_time,
                end_time=end_time
            )
    return redirect("dashboard")


def delete_break(request, break_id):
    """Скасування/видалення перерви"""
    if "master_id" in request.session:
        break_item = get_object_or_404(BreakTime, id=break_id)
        break_item.delete()
    return redirect("dashboard")


def toggle_master_status(request, master_id):
    if "master_id" in request.session:
        master = get_object_or_404(Master, id=master_id)
        master.is_active = False
        master.save()
    return redirect("dashboard")


# --- АДМІН-ПАНЕЛЬ (КЕРУВАННЯ ПРАЦІВНИКАМИ, ПОСЛУГАМИ ТА СПЕЦІАЛЬНОСТЯМИ) ---

def add_master(request):
    if request.method == "POST":
        name = request.POST.get("name")
        specialty_ids = request.POST.getlist("specialties")
        if name:
            master = Master.objects.create(name=name, is_active=True)
            if specialty_ids:
                master.specialties.set(specialty_ids)
    return redirect("dashboard")

def delete_master(request, master_id):
    master = get_object_or_404(Master, id=master_id)
    master.delete()
    return redirect("dashboard")

def add_specialty(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            Specialty.objects.get_or_create(name=name)
    return redirect("dashboard")

def delete_specialty(request, specialty_id):
    specialty = get_object_or_404(Specialty, id=specialty_id)
    specialty.delete()
    return redirect("dashboard")

def add_service(request):
    if request.method == "POST":
        name = request.POST.get("name")
        specialty_id = request.POST.get("specialty_id")
        if name and specialty_id:
            Service.objects.create(name=name, specialty_id=specialty_id)
    return redirect("dashboard")

def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    service.delete()
    return redirect("dashboard")