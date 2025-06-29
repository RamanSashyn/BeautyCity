from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.db import models
import requests
from django.conf import settings


class Salon(models.Model):
    name         = models.CharField('Название',      max_length=150)
    address      = models.CharField('Адрес',         max_length=150)
    phone_number = models.CharField('Номер телефона', max_length=30)
    photo        = models.ImageField('Фото салона',   upload_to='salons/', blank=True, null=True)

    lat = models.FloatField('Широта', null=True, blank=True)
    lon = models.FloatField('Долгота', null=True, blank=True)

    class Meta:
        verbose_name = 'Салон'
        verbose_name_plural = 'Салоны'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.address:
            url = 'https://geocode-maps.yandex.ru/1.x'
            params = {
                'format': 'json',
                'apikey': settings.YANDEX_GEOCODE_KEY,
                'geocode': self.address
            }
            try:
                resp = requests.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                pos = data['response']['GeoObjectCollection']\
                          ['featureMember'][0]['GeoObject']['Point']['pos']
                lon_str, lat_str = pos.split()
                self.lon = float(lon_str)
                self.lat = float(lat_str)
            except Exception:
                self.lat = None
                self.lon = None

        super().save(*args, **kwargs)

class Category(models.Model):
    name = models.CharField('Категория', max_length=100)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField('Название услуги', max_length=100)
    description = models.TextField('Описание', blank=True)
    base_price = models.DecimalField('Базовая цена', max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField('Длительность (мин)')
    photo = models.ImageField('Фото услуги', upload_to='services/', blank=True, null=True)
    category = models.ForeignKey(Category, verbose_name="Категория", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Процедура'
        verbose_name_plural = 'Процедуры'

    def __str__(self):
        return self.name


class Specialist(models.Model):
    name = models.CharField('Имя', max_length=150)
    photo = models.ImageField('Фото', upload_to='specialists/', blank=True, null=True)
    bio = models.TextField('Специальность', max_length=700, blank=True)
    salons = models.ManyToManyField(Salon, verbose_name='Салоны', blank=True)
    services = models.ManyToManyField(Service, verbose_name='Услуги', blank=True)
    experience_years = models.PositiveIntegerField('Стаж (лет)', default=0)
    experience_months = models.PositiveIntegerField('Стаж (мес.)', default=0)
    reviews_count = models.PositiveIntegerField('Количество отзывов', default=0)

    class Meta:
        verbose_name = 'Специалист'
        verbose_name_plural = 'Специалисты'

    def __str__(self):
        return self.name


class Client(models.Model):
    name = models.CharField('Имя', max_length=150, blank=True)
    phone = models.CharField('Телефон', max_length=30, unique=True)
    birthday = models.DateField('День рождения', blank=True, null=True)
    gender = models.CharField('Пол', max_length=10, choices=[('male', 'Мужской'), ('female', 'Женский')], blank=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return f'Клиент №{self.id} ({self.phone})'


class PromoCode(models.Model):
    code = models.CharField('Промокод', max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField('Скидка (%)')
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    target_audience = models.CharField('Целевая аудитория', max_length=100, blank=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'

    def __str__(self):
        return self.code


class TimeSlot(models.Model):
    date = models.DateField('Дата')
    time = models.TimeField('Время')
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    is_booked = models.BooleanField('Занято', default=False)

    class Meta:
        unique_together = ('date', 'time', 'specialist', 'salon')
        ordering = ['date', 'time']
        verbose_name = 'Слот времени'
        verbose_name_plural = 'Слоты времени'

    def __str__(self):
        return f'{self.date} {self.time} ({self.specialist})'


class Appointment(models.Model):
    client = models.ForeignKey(Client, verbose_name='Клиент', on_delete=models.CASCADE)
    specialist = models.ForeignKey(Specialist, verbose_name='Специалист', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, verbose_name='Услуга', on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, verbose_name='Салон', on_delete=models.CASCADE)
    date_time_start = models.DateTimeField('Дата и время начала')
    date_time_end = models.DateTimeField('Дата и время окончания')
    status = models.CharField('Статус', max_length=20, choices=[
        ('booked', 'Записан'),
        ('cancelled', 'Отменён'),
        ('completed', 'Завершён'),
    ])
    source = models.CharField('Источник', max_length=30, blank=True)
    promo_code_used = models.ForeignKey(PromoCode, verbose_name='Использованный промокод', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return f'{self.client} - {self.service} - {self.date_time_start}'

    def clean(self):
        if TimeSlot.objects.filter(
            specialist=self.specialist,
            salon=self.salon,
            date=self.date_time_start.date(),
            time=self.date_time_start.time(),
            is_booked=True
        ).exists():
            raise ValidationError("Выбранное время уже занято.")

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating:
            start = self.date_time_start
            end = self.date_time_end

            TimeSlot.objects.filter(
                specialist=self.specialist,
                salon=self.salon,
                date=start.date(),
                time__gte=start.time(),
                time__lt=end.time()
            ).update(is_booked=True)


class WorkShift(models.Model):
    specialist = models.ForeignKey(Specialist, verbose_name='Специалист', on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, verbose_name='Салон', on_delete=models.CASCADE)
    date = models.DateField('Дата')
    start_time = models.TimeField('Начало')
    end_time = models.TimeField('Окончание')

    class Meta:
        verbose_name = 'Расписание'
        verbose_name_plural = 'Расписания'

    def __str__(self):
        return f'{self.specialist} - {self.date}'

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating:
            self.generate_time_slots()

    def generate_time_slots(self, interval_minutes=30):
        existing = TimeSlot.objects.filter(
            specialist=self.specialist,
            salon=self.salon,
            date=self.date
        )
        if existing.exists():
            return

        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        current = start_dt
        while current < end_dt:
            TimeSlot.objects.get_or_create(
                date=self.date,
                time=current.time(),
                specialist=self.specialist,
                salon=self.salon
            )
            current += timedelta(minutes=interval_minutes)


class Payment(models.Model):
    appointment = models.OneToOneField(Appointment, verbose_name='Запись', on_delete=models.CASCADE)
    amount = models.DecimalField('Сумма', max_digits=8, decimal_places=2)
    payment_status = models.CharField('Статус оплаты', max_length=30, choices=[
        ('pending', 'Ожидает'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка'),
    ])
    payment_method = models.CharField('Метод оплаты', max_length=50)

    class Meta:
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплаты'

    def __str__(self):
        return f'Оплата {self.amount} ({self.payment_status})'


class ConsentLog(models.Model):
    client_phone = models.CharField('Телефон клиента', max_length=30)
    consent_given_at = models.DateTimeField('Время согласия', auto_now_add=True)
    consent_pdf_file = models.FileField('Файл согласия (PDF)', upload_to='consents/')

    def __str__(self):
        return self.client_phone
