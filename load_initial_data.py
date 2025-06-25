import os
import json
import django

from pathlib import Path
from django.core.files import File

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "beautycity.settings")
django.setup()

from api.models import Salon, Service, Specialist


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"


def load_salons():
    with open(DATA_DIR / "salons.json", encoding="utf-8") as f:
        salons = json.load(f)

    for item in salons:
        salon, created = Salon.objects.get_or_create(
            name=item["name"],
            defaults={
                "address": item["address"],
                "phone_number": "+7 (000) 000-00-00"
            }
        )
        print(f'✔ {"Создан" if created else "Уже есть"} салон: {salon.name}')


def load_services():
    with open(DATA_DIR / "services.json", encoding="utf-8") as f:
        services = json.load(f)

    for item in services:
        name = item["name"]
        price = item["price"]
        image_path = item.get("image", "").lstrip("/")
        duration = 60

        service, created = Service.objects.get_or_create(
            name=name,
            defaults={
                "base_price": price,
                "description": "",
                "duration_minutes": duration,
            }
        )
        print(f'✔ {"Создана" if created else "Уже есть"} услуга: {name}')


def load_specialists():
    with open(DATA_DIR / "masters.json", encoding="utf-8") as f:
        masters = json.load(f)

    for item in masters:
        salon_name = item.get("salon")
        salon = Salon.objects.filter(name=salon_name).first()
        if not salon:
            print(f"⚠ Пропущен {item['name']}: салон '{salon_name}' не найден")
            continue

        specialist, created = Specialist.objects.get_or_create(
            name=item["name"],
            defaults={
                "salon": salon,
                "bio": item.get("role", ""),
            }
        )

        photo_path = item.get("photo", "").replace("/static/", "").lstrip("/")
        photo_file = BASE_DIR / photo_path

        if photo_file.exists():
            with open(photo_file, "rb") as f:
                specialist.photo.save(photo_file.name, File(f), save=True)
        else:
            print(f"⚠ Нет файла фото: {photo_file}")

        print(f'✔ {"Создан" if created else "Уже есть"} специалист: {specialist.name}')


def main():
    print("Импортируем салоны")
    load_salons()
    print("Импортируем услуги")
    load_services()
    print("Импортируем мастеров")
    load_specialists()
    print("Все данные успешно загружены!")


if __name__ == "__main__":
    main()
