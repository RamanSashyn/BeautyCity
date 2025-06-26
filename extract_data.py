import json
from bs4 import BeautifulSoup
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

INDEX_HTML = TEMPLATES_DIR / "index.html"


def extract_services_from_index(html_path):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    services = []
    for card in soup.select(".services__block"):
        name_tag = card.select_one(".services__elems_title")
        price_tag = card.select_one(".services__elems_light")
        image_tag = card.select_one("img")

        if not name_tag or not price_tag:
            continue

        name = name_tag.get_text(strip=True)
        price = int(
            price_tag.get_text(strip=True)
            .replace("₽", "")
            .replace("руб", "")
            .replace(" ", "")
        )
        image = image_tag["src"] if image_tag else ""

        services.append({
            "name": name,
            "price": price,
            "image": image,
        })
    return services


def extract_salons_from_index(html_path):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    seen = set()
    salons = []

    for card in soup.select(".salons__block"):
        name_tag = card.select_one(".salons__elems_title")
        address_tag = card.select_one(".salons__elems_light")
        image_tag = card.select_one("img")

        if not name_tag or not address_tag:
            continue

        name = name_tag.get_text(strip=True)
        if name in seen:
            continue

        seen.add(name)
        salons.append({
            "name": name,
            "address": address_tag.get_text(strip=True),
            "image": image_tag["src"] if image_tag else "",
        })

    return salons


def save_json(data, filename):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f" Сохранено: {path}")


def main():
    services = extract_services_from_index(INDEX_HTML)
    salons = extract_salons_from_index(INDEX_HTML)

    save_json(services, "services.json")
    save_json(salons, "salons.json")


if __name__ == "__main__":
    main()
