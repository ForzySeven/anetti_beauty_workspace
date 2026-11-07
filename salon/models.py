from django.db import models
import random

MASTER_COLORS_POOL = [
    '#3aeb34', '#8b5cf6', '#06b6d4', '#10b981',
    '#e35b00', '#e3df00', '#3b82f6', '#84cc16', '#d946ef', '#14b8a6'
]

class Specialty(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва спеціальності")

    class Meta:
        verbose_name = "Спеціальність"
        verbose_name_plural = "Спеціальності"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва послуги")
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name="services", verbose_name="Спеціальність")

    class Meta:
        verbose_name = "Послуга"
        verbose_name_plural = "Послуги"

    def __str__(self):
        return f"{self.name} ({self.specialty.name})"


class Master(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ім'я майстра")
    specialties = models.ManyToManyField(Specialty, related_name="masters", verbose_name="Спеціальності")
    is_active = models.BooleanField(default=True, verbose_name="Працює (Активний)")
    color = models.CharField(max_length=7, blank=True, verbose_name="Колір у календарі")

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = random.choice(MASTER_COLORS_POOL)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Майстер"
        verbose_name_plural = "Майстри"

    def __str__(self):
        return self.name


class DayOff(models.Model):
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="days_off", verbose_name="Майстер")
    date = models.DateField(verbose_name="Дата вихідного")

    class Meta:
        verbose_name = "Вихідний"
        verbose_name_plural = "Вихідні днів"

    def __str__(self):
        return f"{self.master.name} [Вихідний: {self.date}]"


class BreakTime(models.Model):
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="breaks", verbose_name="Майстер")
    date = models.DateField(verbose_name="Дата перерви")
    start_time = models.TimeField(verbose_name="Початок перерви")
    end_time = models.TimeField(verbose_name="Кінець перерви")

    class Meta:
        verbose_name = "Перерва"
        verbose_name_plural = "Перерви"

    def __str__(self):
        return f"{self.master.name} перерва {self.start_time}-{self.end_time} ({self.date})"


class Appointment(models.Model):
    client_name = models.CharField(max_length=100, verbose_name="Ім'я клієнта")
    client_phone = models.CharField(max_length=100, blank=True, null=True, verbose_name="Контакти / Телефон")
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="appointments", verbose_name="Майстер")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="Послуга")
    date = models.DateField(verbose_name="Дата запису")
    start_time = models.TimeField(verbose_name="Час початку")
    end_time = models.TimeField(verbose_name="Час завершення")
    created_by = models.ForeignKey(Master, on_delete=models.SET_NULL, null=True, related_name="created_appointments", verbose_name="Створив майстер")

    class Meta:
        verbose_name = "Запис"
        verbose_name_plural = "Записи"

    def __str__(self):
        return f"{self.client_name} -> {self.master.name} ({self.date} {self.start_time}-{self.end_time})"