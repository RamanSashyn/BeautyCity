import json
from bs4 import BeautifulSoup
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SERVICE_HTML = TEMPLATES_DIR / "service.html"


def extract_services_by_category(html_path):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    result = {}
    category_headers = soup.select(".service__services .accordion")
    panels = soup.select(".service__services .panel")

    for header, panel in zip(category_headers, panels):
        category_name = header.get_text(strip=True)
        services = []

        for item in panel.select(".accordion__block_item"):
            name_tag = item.select_one(".accordion__block_item_intro")
            price_tag = item.select_one(".accordion__block_item_address")
            if not name_tag or not price_tag:
                continue

            name = name_tag.get_text(strip=True)
            price = int(
                price_tag.get_text(strip=True)
                .replace("₽", "")
                .replace("руб", "")
                .replace(" ", "")
            )

            services.append({"name": name, "price": price})

        if services:
            result[category_name] = services

    return result


def save_json(data, filename):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Сохранено: {path}")


def main():
    services_by_category = extract_services_by_category(SERVICE_HTML)
    save_json(services_by_category, "services_by_category.json")


if __name__ == "__main__":
    main()
