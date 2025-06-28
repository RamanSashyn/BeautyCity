from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import (
    Salon, Service, Specialist, Client,
    PromoCode, Appointment, WorkShift,
    Payment, ConsentLog, Category, TimeSlot
)

@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ('photo_preview', 'name', 'address', 'phone_number')
    search_fields = ('name', 'address')
    readonly_fields = ('photo_preview',)

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.photo.url)
        return "Нет фото"

    photo_preview.short_description = "Фото"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('photo_preview', 'name', 'category', 'base_price', 'duration_minutes')
    search_fields = ('name',)
    list_filter = ('category', 'duration_minutes')
    readonly_fields = ('photo_preview',)

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.photo.url)
        return "Нет фото"

    photo_preview.short_description = "Фото"


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    list_display = ('photo_preview', 'name', 'list_salons')
    list_filter = ('salons',)
    search_fields = ('name',)
    readonly_fields = ('photo_preview',)

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.photo.url)
        return "Нет фото"

    def list_salons(self, obj):
        return ", ".join([s.name for s in obj.salons.all()])
    list_salons.short_description = "Салоны"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone', 'name', 'gender', 'birthday')
    search_fields = ('phone', 'name')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'specialist', 'service', 'date_time_start', 'status')
    list_filter = ('status', 'date_time_start')
    search_fields = ('client__phone',)


@admin.register(WorkShift)
class WorkShiftAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'salon', 'date', 'start_time', 'end_time')
    list_filter = ('date', 'salon')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'amount', 'payment_status', 'payment_method')
    list_filter = ('payment_status', 'payment_method')


@admin.register(ConsentLog)
class ConsentLogAdmin(admin.ModelAdmin):
    list_display = ('client_phone', 'consent_given_at')
    search_fields = ('client_phone',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


class TimeSlotAdminForm(forms.ModelForm):
    class Meta:
        model = WorkShift
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'specialist' in self.data:
            try:
                specialist_id = int(self.data.get('specialist'))
                specialist = Specialist.objects.get(pk=specialist_id)
                self.fields['salon'].queryset = specialist.salons.all()
            except (ValueError, Specialist.DoesNotExist):
                pass

        elif self.instance.pk and self.instance.specialist:
            self.fields['salon'].queryset = self.instance.specialist.salons.all()


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    form = TimeSlotAdminForm
    list_display = ('date', 'time', 'specialist', 'salon', 'is_booked')
    list_filter = ('date', 'salon', 'specialist', 'is_booked')
    search_fields = ('specialist__name', 'salon__name')
    ordering = ('date', 'time')