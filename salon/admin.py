from django.contrib import admin
from .models import Specialty, Service, Master, DayOff, BreakTime, Appointment

admin.site.register(Specialty)
admin.site.register(Service)
admin.site.register(Master)
admin.site.register(DayOff)
admin.site.register(BreakTime)
admin.site.register(Appointment)