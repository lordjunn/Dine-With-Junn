import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

class V1HtmlMigrator:
    """Migrates legacy Dine with Junn V1 HTML month files into V2 Markdown."""

    MONTH_NAME_TO_NUM = {
        "Jan": 1, "January": 1,
        "Feb": 2, "February": 2,
        "Mar": 3, "March": 3,
        "Apr": 4, "April": 4,
        "May": 5,
        "Jun": 6, "June": 6,
        "Jul": 7, "July": 7,
        "Aug": 8, "August": 8,
        "Sep": 9, "Sept": 9, "September": 9,
        "Oct": 10, "October": 10,
        "Nov": 11, "November": 11,
        "Dec": 12, "December": 12,
    }

    MONTH_NUM_TO_FULL = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    def __init__(self, v1_base_dir: Optional[Path] = None, v2_base_dir: Optional[Path] = None):
        self.v1_base_dir = Path(v1_base_dir) if v1_base_dir else Path(r"C:\Users\Junn Kit\OneDrive\Food blog")
        self.v2_base_dir = Path(v2_base_dir) if v2_base_dir else Path(__file__).resolve().parent.parent

    def parse_html_file(self, html_path: Path) -> Dict[str, Any]:
        """Parses a V1 HTML month file and returns structured data."""
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # 1. Extract #header-config attributes with dedicated regex
        year_match = re.search(r'data-year="([^"]*)"', content, re.DOTALL | re.IGNORECASE)
        month_match = re.search(r'data-month="([^"]*)"', content, re.DOTALL | re.IGNORECASE)
        days_match = re.search(r'data-days="([^"]*)"', content, re.DOTALL | re.IGNORECASE)
        reasons_match = re.search(r'data-reasons="([^"]*)"', content, re.DOTALL | re.IGNORECASE)
        text_match = re.search(r'data-text="([^"]*)"', content, re.DOTALL | re.IGNORECASE)

        year_str = year_match.group(1).strip() if year_match else ""
        month_str = month_match.group(1).strip() if month_match else ""
        days_str = days_match.group(1).strip() if days_match else ""
        reasons_str = reasons_match.group(1).strip() if reasons_match else ""
        text_str = text_match.group(1).strip() if text_match else ""

        year = int(year_str) if year_str.isdigit() else 2026
        month_num = self.MONTH_NAME_TO_NUM.get(month_str, 7)
        full_month_name = self.MONTH_NUM_TO_FULL.get(month_num, "July")

        # Parse reasons list
        reasons = [r.strip() for r in reasons_str.split(",") if r.strip()]

        # Clean intro text: replace <br> with newlines, remove comments, clean up spacing
        intro_text = re.sub(r'<br\s*/?>', '\n', text_str, flags=re.IGNORECASE)
        intro_text = re.sub(r'<!--.*?-->', '', intro_text, flags=re.DOTALL).strip()
        intro_text = re.sub(r'\n{3,}', '\n\n', intro_text)

        # 2. Split into menu blocks
        raw_blocks = re.split(r'<div\s+class="menu">', content, flags=re.IGNORECASE)
        menu_blocks = raw_blocks[1:] if len(raw_blocks) > 1 else []

        days_data = []
        outro_data = {
            "title": "",
            "image": "",
            "prose": "",
            "expenses": {
                "rental": 0.0,
                "utilities": 0.0,
                "petrol": 0.0,
                "etc": []
            }
        }

        for block in menu_blocks:
            # Check if this block is the outro/footer block
            if "footer-container" in block or "Spendings" in block or "Purely food expenses" in block:
                self._parse_outro_block(block, outro_data)
                continue

            heading_match = re.search(r'<h2\s+class="menu-group-heading">\s*(.*?)\s*</h2>', block, re.DOTALL | re.IGNORECASE)
            heading_text = heading_match.group(1).strip() if heading_match else ""

            # Parse date heading like "01 Jul 2026 (Wednesday)" or "3 August 2022 (Wednesday)"
            date_match = re.match(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*\(([A-Za-z]+)\)', heading_text)
            if not date_match:
                # Might be blank skeleton or non-date block
                continue

            day_num = int(date_match.group(1))
            day_month_str = date_match.group(2)
            day_year_num = int(date_match.group(3))
            day_of_week = date_match.group(4)
            date_iso = f"{day_year_num:04d}-{self.MONTH_NAME_TO_NUM.get(day_month_str, month_num):02d}-{day_num:02d}"

            meals = self._parse_meals_in_block(block, day_year_num, full_month_name)
            if meals:
                days_data.append({
                    "date_str": date_iso,
                    "day_of_week": day_of_week,
                    "meals": meals
                })

        slug = f"{year:04d}-{month_num:02d}"
        nom_nom_days = int(days_str) if days_str.isdigit() else None

        return {
            "year": year,
            "month": month_num,
            "slug": slug,
            "title": f"Food Archive - {full_month_name} {year}",
            "nom_nom_days": nom_nom_days,
            "reasons": reasons,
            "intro_text": intro_text,
            "archive": {
                "era": "Unknown grounds" if (year >= 2026 and month_num >= 8) else "The MMU Chapters",
                "teaser": "Goodbye." if (year == 2026 and month_num == 7) else ("Now we wait." if (year == 2026 and month_num == 8) else ""),
                "image": f"images/{year}/{full_month_name}/Sakiko.png" if (year == 2026 and month_num == 7) else ""
            },
            "outro": {
                "title": outro_data.get("title", ""),
                "image": outro_data.get("image", ""),
                "prose": outro_data.get("prose", ""),
            },
            "expenses": outro_data.get("expenses", {}),
            "days": days_data
        }

    def _parse_meals_in_block(self, block_html: str, year: int, full_month_name: str) -> List[Dict[str, Any]]:
        """Extracts individual meal items from a day's menu block."""
        meal_items = []
        raw_items = re.split(r'<div\s+class="menu-item">', block_html, flags=re.IGNORECASE)
        item_chunks = raw_items[1:] if len(raw_items) > 1 else []

        for item_html in item_chunks:
            # Dish Name & Restaurant
            name_match = re.search(r'<span\s+class="menu-item-name">\s*(.*?)\s*</span>', item_html, re.DOTALL | re.IGNORECASE)
            raw_name = name_match.group(1).strip() if name_match else ""
            if not raw_name:
                continue

            dish_name = raw_name
            restaurant = ""
            if "[" in raw_name and raw_name.endswith("]"):
                dish_name, restaurant = raw_name[:-1].split("[", 1)
                dish_name = dish_name.strip()
                restaurant = restaurant.strip()

            # Price
            price_match = re.search(r'<span\s+class="menu-item-price">\s*(.*?)\s*</span>', item_html, re.DOTALL | re.IGNORECASE)
            price_str = price_match.group(1).strip() if price_match else ""
            price_num = self._clean_price(price_str)

            # Meal Type
            meal_type_match = re.search(r'<span\s+class="meal-type">\s*\((.*?)\)\s*</span>', item_html, re.DOTALL | re.IGNORECASE)
            meal_type = meal_type_match.group(1).strip() if meal_type_match else "Lunch"

            # Image
            img_match = re.search(r'<img\s+class="menu-item-image"\s+src="([^"]*?)"', item_html, re.DOTALL | re.IGNORECASE)
            raw_img_src = img_match.group(1).strip() if img_match else ""
            img_path = self._normalize_image_path(raw_img_src, year, full_month_name)

            # Description & itemized list
            desc_match = re.search(r'<p\s+class="menu-item-description">\s*(.*?)\s*</p>', item_html, re.DOTALL | re.IGNORECASE)
            desc_html = desc_match.group(1).strip() if desc_match else ""

            items = []
            ul_match = re.search(r'<ul>(.*?)</ul>', desc_html, re.DOTALL | re.IGNORECASE)
            if ul_match:
                li_matches = re.finditer(r'<li>(.*?)</li>', ul_match.group(1), re.DOTALL | re.IGNORECASE)
                for li in li_matches:
                    clean_li = re.sub(r'<[^>]*>', '', li.group(1)).strip()
                    if clean_li:
                        items.append(clean_li)
                desc_html = desc_html[:ul_match.start()] + desc_html[ul_match.end():]

            desc_prose = re.sub(r'<br\s*/?>', '\n', desc_html, flags=re.IGNORECASE)
            desc_prose = re.sub(r'<small>(.*?)</small>', r'\1', desc_prose, flags=re.DOTALL | re.IGNORECASE)
            desc_prose = re.sub(r'<!--.*?-->', '', desc_prose, flags=re.DOTALL)
            desc_prose = re.sub(r'\n{3,}', '\n\n', desc_prose).strip()

            meal_items.append({
                "dish_name": dish_name,
                "restaurant": restaurant,
                "price_str": price_str,
                "price": price_num,
                "meal_type": meal_type,
                "image": img_path,
                "description": desc_prose,
                "items": items
            })

        return meal_items

    def _parse_outro_block(self, block_html: str, outro_data: Dict[str, Any]):
        """Parses the outro retrospective card and spending breakdown."""
        name_match = re.search(r'<span\s+class="menu-item-name">\s*(.*?)\s*</span>', block_html, re.DOTALL | re.IGNORECASE)
        if name_match:
            outro_data["title"] = name_match.group(1).strip()

        img_match = re.search(r'<img\s+class="menu-item-image"\s+src="([^"]*?)"', block_html, re.DOTALL | re.IGNORECASE)
        if img_match:
            raw_src = img_match.group(1).strip()
            if raw_src:
                filename = Path(raw_src).name
                outro_data["image"] = f"images/2026/July/{filename}"

        desc_match = re.search(r'<p\s+class="menu-item-description">\s*(.*?)\s*</p>', block_html, re.DOTALL | re.IGNORECASE)
        if desc_match:
            full_desc = desc_match.group(1)
            ul_pos = full_desc.find("<ul")
            if ul_pos != -1:
                prose_html = full_desc[:ul_pos]
                expenses_html = full_desc[ul_pos:]
            else:
                prose_html = full_desc
                expenses_html = ""

            prose = re.sub(r'<br\s*/?>', '\n', prose_html, flags=re.IGNORECASE)
            prose = re.sub(r'<!--.*?-->', '', prose, flags=re.DOTALL).strip()
            prose = re.sub(r'\n{3,}', '\n\n', prose)
            outro_data["prose"] = prose

            self._parse_expenses_list(expenses_html, outro_data["expenses"])

    def _parse_expenses_list(self, expenses_html: str, expenses_dict: Dict[str, Any]):
        """Parses the nested <ul> list of expenses."""
        if not expenses_html:
            return

        rental_match = re.search(r'Rental\s*-\s*RM\s*([\d\.]+)', expenses_html, re.IGNORECASE)
        if rental_match:
            expenses_dict["rental"] = float(rental_match.group(1))

        utilities_match = re.search(r'Utilities\s*-\s*RM\s*([\d\.]+)', expenses_html, re.IGNORECASE)
        if utilities_match:
            expenses_dict["utilities"] = float(utilities_match.group(1))

        petrol_match = re.search(r'Petrol\s*-\s*RM\s*([\d\.]+)', expenses_html, re.IGNORECASE)
        if petrol_match:
            expenses_dict["petrol"] = float(petrol_match.group(1))

        etc_block_match = re.search(r'Etc\.?\s*Expenses.*?<ul>(.*?)</ul>', expenses_html, re.DOTALL | re.IGNORECASE)
        if etc_block_match:
            nested_lis = re.finditer(r'<li>\s*(.*?)\s*</li>', etc_block_match.group(1), re.DOTALL | re.IGNORECASE)
            for li in nested_lis:
                li_text = li.group(1).strip()
                item_match = re.match(r'(?:\((\d+)\))?\s*(.*?)\s*-\s*(?:RM\s*)?([\d\.]+)', li_text, re.IGNORECASE)
                if item_match:
                    day_val = int(item_match.group(1)) if item_match.group(1) else None
                    label_val = item_match.group(2).strip()
                    amount_val = float(item_match.group(3))
                    expenses_dict["etc"].append({
                        "day": day_val,
                        "label": label_val,
                        "amount": amount_val
                    })

    def _clean_price(self, price_str: str) -> float:
        """Parses a price string like 'RM 8.50', 'Free', or '<s>RM 5.50?</s> Free' into a numeric float."""
        if not price_str:
            return 0.0
        cleaned = re.sub(r'<[^>]*>', ' ', price_str).strip()
        if "free" in cleaned.lower():
            return 0.0
        nums = re.findall(r'\d+(?:\.\d+)?', cleaned)
        if nums:
            return float(nums[-1])
        return 0.0

    def _normalize_image_path(self, raw_src: str, year: int, full_month_name: str) -> str:
        """Normalizes legacy image paths like '2026/July/2026, July, image 1.png' to 'images/2026/July/...'."""
        if not raw_src:
            return ""
        if raw_src.startswith("http://") or raw_src.startswith("https://"):
            return raw_src
        filename = Path(raw_src).name
        return f"images/{year}/{full_month_name}/{filename}"

    def serialize_to_markdown(self, data: Dict[str, Any]) -> str:
        """Serializes structured month data into clean Markdown with YAML frontmatter."""
        lines = ["---"]
        lines.append(f'year: {data["year"]}')
        lines.append(f'month: {data["month"]}')
        lines.append(f'slug: "{data["slug"]}"')
        lines.append(f'title: "{data["title"]}"')
        if data.get("nom_nom_days") is not None:
            lines.append(f'nom_nom_days: {data["nom_nom_days"]}')

        # Reasons
        if data.get("reasons"):
            lines.append("reasons:")
            for reason in data["reasons"]:
                lines.append(f'  - "{reason}"')
        else:
            lines.append("reasons: []")

        # Intro text
        if data.get("intro_text"):
            lines.append("intro_text: |")
            for line in data["intro_text"].split("\n"):
                lines.append(f"  {line}")
        else:
            lines.append('intro_text: ""')

        # Archive
        lines.append("archive:")
        lines.append(f'  era: "{data["archive"].get("era", "Unknown grounds")}"')
        lines.append(f'  teaser: "{data["archive"].get("teaser", "")}"')
        lines.append(f'  image: "{data["archive"].get("image", "")}"')

        # Outro
        lines.append("outro:")
        lines.append(f'  title: "{data["outro"].get("title", "")}"')
        lines.append(f'  image: "{data["outro"].get("image", "")}"')
        if data["outro"].get("prose"):
            lines.append("  prose: |")
            for line in data["outro"]["prose"].split("\n"):
                lines.append(f"    {line}")
        else:
            lines.append('  prose: ""')

        # Expenses
        expenses = data.get("expenses", {})
        lines.append("expenses:")
        lines.append(f'  rental: {expenses.get("rental", 0.0):.2f}')
        lines.append(f'  utilities: {expenses.get("utilities", 0.0):.2f}')
        lines.append(f'  petrol: {expenses.get("petrol", 0.0):.2f}')
        etc_items = expenses.get("etc", [])
        if etc_items:
            lines.append("  etc:")
            for item in etc_items:
                lines.append(f'    - label: "{item["label"]}"')
                if item.get("day"):
                    lines.append(f'      day: {item["day"]}')
                lines.append(f'      amount: {item["amount"]:.2f}')
        else:
            lines.append("  etc: []")

        lines.append("---\n")

        # Days & Meals
        for day in data.get("days", []):
            lines.append(f'## {day["date_str"]} ({day["day_of_week"]})\n')
            for meal in day.get("meals", []):
                dish_header = f'### {meal["dish_name"]}'
                if meal.get("restaurant"):
                    dish_header += f' [{meal["restaurant"]}]'
                lines.append(dish_header)
                if meal.get("price_str"):
                    lines.append(f'- Price: {meal["price_str"]}')
                lines.append(f'- Meal: {meal.get("meal_type", "Lunch")}')
                if meal.get("image"):
                    lines.append(f'- Image: {meal["image"]}')
                lines.append("")

                if meal.get("description"):
                    lines.append(meal["description"])
                    lines.append("")

                if meal.get("items"):
                    for item_bullet in meal["items"]:
                        lines.append(f'- {item_bullet}')
                    lines.append("")

        return "\n".join(lines).strip() + "\n"

    def copy_month_images(self, year: int, month_name: str):
        """Copies image assets from V1 directory to V2 image directory."""
        v1_img_dir = self.v1_base_dir / "Logs" / str(year) / month_name
        v2_img_dir = self.v2_base_dir / "images" / str(year) / month_name
        if v1_img_dir.exists():
            v2_img_dir.mkdir(parents=True, exist_ok=True)
            for img_file in v1_img_dir.glob("*.png"):
                dest = v2_img_dir / img_file.name
                shutil.copy2(img_file, dest)
            for img_file in v1_img_dir.glob("*.jpg"):
                dest = v2_img_dir / img_file.name
                shutil.copy2(img_file, dest)

    def migrate_file(self, html_path: Path, output_md_path: Optional[Path] = None) -> Path:
        """Migrates a single HTML file to Markdown and relocates images."""
        data = self.parse_html_file(html_path)
        markdown_text = self.serialize_to_markdown(data)

        if not output_md_path:
            content_dir = self.v2_base_dir / "content"
            content_dir.mkdir(parents=True, exist_ok=True)
            output_md_path = content_dir / f"{data['slug']}.md"

        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)

        # Copy images
        full_month_name = self.MONTH_NUM_TO_FULL.get(data["month"], "July")
        self.copy_month_images(data["year"], full_month_name)

        return output_md_path
