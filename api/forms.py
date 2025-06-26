from django import forms
from .models import Appointment, Client, Service, Specialist, Salon
from django.utils import timezone


class BookingForm(forms.Form):
    name = forms.CharField(label="Имя", max_length=150)
    phone = forms.CharField(label="Телефон", max_length=30)
    salon = forms.ModelChoiceField(queryset=Salon.objects.all(), label="Салон")
    service = forms.ModelChoiceField(queryset=Service.objects.all(), label="Услуга")
    specialist = forms.ModelChoiceField(queryset=Specialist.objects.all(), label="Специалист", required=False)
    date = forms.DateField(label="Дата", widget=forms.SelectDateWidget())
    time = forms.TimeField(label="Время")

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self):
        client, _ = Client.objects.get_or_create(phone=self.cleaned_data["phone"], defaults={
            "name": self.cleaned_data["name"]
        })
        dt_start = timezone.make_aware(
            timezone.datetime.combine(self.cleaned_data["date"], self.cleaned_data["time"])
        )
        dt_end = dt_start + timezone.timedelta(minutes=self.cleaned_data["service"].duration_minutes)

        appointment = Appointment.objects.create(
            client=client,
            specialist=self.cleaned_data["specialist"],
            service=self.cleaned_data["service"],
            salon=self.cleaned_data["salon"],
            date_time_start=dt_start,
            date_time_end=dt_end,
            status="booked",
            source="web",
        )
        return appointment
