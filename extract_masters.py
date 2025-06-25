import re
import json
from pathlib import Path
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
JS_PATH = BASE_DIR / "static" / "js" / "main.js"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def extract_masters_from_js(js_path):
    with open(js_path, encoding="utf-8") as f:
        js_content = f.read()

    blocks = re.findall(r"\.html\(`(.*?)`\)", js_content, re.DOTALL)

    salons = ["Пушкинская", "Ленина", "Красная"]
    result = []

    for salon, raw_html in zip(salons, blocks):
        html = f"<div>{raw_html}</div>"
        soup = BeautifulSoup(html, "html.parser")

        for block in soup.select(".accordion__block"):
            name_tag = block.select_one(".accordion__block_master")
            role_tag = block.select_one(".accordion__block_prof")
            image_tag = block.select_one("img")

            if not name_tag:
                continue

            result.append({
                "name": name_tag.text.strip(),
                "role": role_tag.text.strip() if role_tag else "",
                "photo": image_tag["src"] if image_tag else "",
                "salon": f"BeautyCity {salon}"
            })

    return result


def save_json(data, filename):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Сохранено: {path}")


def main():
    masters = extract_masters_from_js(JS_PATH)
    save_json(masters, "masters.json")


if __name__ == "__main__":
    main()
