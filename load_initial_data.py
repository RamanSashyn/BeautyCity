import os
import json
import django

from pathlib import Path
from django.core.files import File

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "beautycity.settings")
django.setup()

from api.models import Salon, Service, Specialist, Category

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

        image_path = item.get("image", "").replace("/static/", "").lstrip("/")
        photo_file = STATIC_DIR / image_path

        if photo_file.exists():
            with open(photo_file, "rb") as f:
                salon.photo.save(photo_file.name, File(f), save=True)
        else:
            print(f"⚠ Нет файла изображения салона: {photo_file}")

        print(f'✔ {"Создан" if created else "Уже есть"} салон: {salon.name}')


def load_services_with_categories():
    path = DATA_DIR / "services_by_category.json"
    if not path.exists():
        print("⚠ Файл services_by_category.json не найден")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    services_with_photos = {}
    services_path = DATA_DIR / "services.json"
    if services_path.exists():
        with open(services_path, encoding="utf-8") as sf:
            for item in json.load(sf):
                services_with_photos[item["name"]] = item.get("image", "")

    for category_name, services in data.items():
        category, _ = Category.objects.get_or_create(name=category_name)

        for item in services:
            name = item["name"]
            price = item["price"]
            duration = 60

            service = Service.objects.filter(name=name).first()
            if not service:
                service = Service.objects.create(
                    name=name,
                    base_price=price,
                    description="",
                    duration_minutes=duration,
                    category=category,
                )
                created = True
            else:
                service.category = category
                service.base_price = price
                service.duration_minutes = duration
                created = False

            image_path = services_with_photos.get(name, "").replace("/static/", "").lstrip("/")
            if image_path:
                photo_file = STATIC_DIR / image_path
                if photo_file.exists():
                    with open(photo_file, "rb") as f:
                        service.photo.save(photo_file.name, File(f), save=True)
                else:
                    print(f"⚠ Нет файла изображения услуги: {photo_file}")

            service.save()
            print(f'✔ {"Создана" if created else "Обновлена"} услуга: {name} → {category_name}')


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
            print(f"⚠ Нет файла фото специалиста: {photo_file}")

        print(f'✔ {"Создан" if created else "Уже есть"} специалист: {specialist.name}')


def main():
    print("Импортируем салоны")
    load_salons()
    print("Импортируем услуги")
    load_services_with_categories()
    print("Импортируем мастеров")
    load_specialists()
    print("Все данные успешно загружены!")


if __name__ == "__main__":
    main()
