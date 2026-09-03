import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from pipeline.schema import (
    MonthData, DayEntry, MealItem, Expenses, EtcExpenseItem,
    ArchiveMetadata, OutroMetadata
)

class MarkdownContentParser:
    """Parses Dine with Junn V2 Markdown content files into MonthData objects."""

    def __init__(self, content_dir: Optional[Path] = None):
        self.content_dir = Path(content_dir) if content_dir else Path(__file__).resolve().parent.parent / "content"

    def parse_file(self, md_path: Path) -> MonthData:
        """Parses a single Markdown file and returns a MonthData object."""
        with open(md_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        return self.parse_text(raw_text, filename=md_path.name)

    def parse_text(self, text: str, filename: str = "") -> MonthData:
        """Parses Markdown text with YAML frontmatter."""
        frontmatter_dict, body_text = self._split_frontmatter(text)

        year = int(frontmatter_dict.get("year", 2026))
        month = int(frontmatter_dict.get("month", 7))
        slug = str(frontmatter_dict.get("slug", f"{year:04d}-{month:02d}"))
        title = str(frontmatter_dict.get("title", f"Food Archive - {slug}"))
        nom_nom_days = frontmatter_dict.get("nom_nom_days", frontmatter_dict.get("food_days"))
        if nom_nom_days is not None:
            nom_nom_days = self._clean_int(nom_nom_days)

        reasons = frontmatter_dict.get("reasons", [])
        if isinstance(reasons, str):
            reasons = [r.strip() for r in reasons.split(",") if r.strip()]

        intro_text = str(frontmatter_dict.get("intro_text", "")).strip()

        # Archive Metadata
        archive_raw = frontmatter_dict.get("archive", {})
        archive = ArchiveMetadata(
            era=str(archive_raw.get("era", "Unknown grounds")),
            teaser=str(archive_raw.get("teaser", "")),
            image=str(archive_raw.get("image", ""))
        )

        # Outro Metadata
        outro_raw = frontmatter_dict.get("outro", {})
        outro = OutroMetadata(
            title=str(outro_raw.get("title", "")),
            image=str(outro_raw.get("image", "")),
            prose=str(outro_raw.get("prose", "")).strip()
        )

        # Expenses
        expenses_raw = frontmatter_dict.get("expenses", {})
        etc_items = []
        for item in expenses_raw.get("etc", []):
            if isinstance(item, dict):
                etc_items.append(EtcExpenseItem(
                    label=str(item.get("label", "")),
                    amount=self._clean_float(item.get("amount", 0.0)),
                    day=self._clean_int(item.get("day"))
                ))

        expenses = Expenses(
            rental=self._clean_float(expenses_raw.get("rental", expenses_raw.get("Adulting fees", 0.0))),
            utilities=self._clean_float(expenses_raw.get("utilities", 0.0)),
            petrol=self._clean_float(expenses_raw.get("petrol", 0.0)),
            etc=etc_items
        )

        # Parse Daily Entries
        days = self._parse_body_days(body_text)

        # Auto-compute active nom nom days if not explicitly overridden
        active_days_with_meals = len([d for d in days if len(d.meals) > 0])
        if nom_nom_days is None or nom_nom_days == 0:
            nom_nom_days = active_days_with_meals

        return MonthData(
            year=year,
            month=month,
            slug=slug,
            title=title,
            nom_nom_days=nom_nom_days,
            reasons=reasons,
            intro_text=intro_text,
            archive=archive,
            outro=outro,
            expenses=expenses,
            days=days
        )

    def _split_frontmatter(self, text: str) -> tuple[Dict[str, Any], str]:
        """Extracts YAML frontmatter and returns (dict, markdown_body)."""
        if not text.startswith("---"):
            return {}, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text

        yaml_content = parts[1]
        body = parts[2]

        frontmatter = self._parse_yaml(yaml_content)
        return frontmatter, body

    def _parse_yaml(self, yaml_text: str) -> Dict[str, Any]:
        """Parses YAML text with PyYAML if installed, otherwise uses pure-Python fallback."""
        try:
            import yaml
            parsed = yaml.safe_load(yaml_text)
            return parsed if isinstance(parsed, dict) else {}
        except ImportError:
            return self._fallback_yaml_parser(yaml_text)

    def _unquote(self, s: str) -> str:
        """Safely removes one layer of matching enclosing quotes."""
        s = s.strip()
        if len(s) >= 2:
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                return s[1:-1].strip()
        return s

    def _strip_inline_comment(self, s: str) -> str:
        """Strips trailing # comments unless inside quotes."""
        in_double = False
        in_single = False
        for idx, ch in enumerate(s):
            if ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '#' and not in_double and not in_single:
                return s[:idx].strip()
        return s.strip()

    def _clean_float(self, val: Any) -> float:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).split("#")[0].strip().replace(",", "")
        match = re.search(r'[-+]?\d*\.?\d+', s)
        return float(match.group()) if match else 0.0

    def _clean_int(self, val: Any) -> Optional[int]:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        s = str(val).split("#")[0].strip()
        match = re.search(r'[-+]?\d+', s)
        return int(match.group()) if match else None

    def _fallback_yaml_parser(self, yaml_text: str) -> Dict[str, Any]:
        """Pure-Python YAML parser for Dine with Junn frontmatter schema."""
        result: Dict[str, Any] = {
            "archive": {},
            "outro": {},
            "expenses": {"rental": 0.0, "utilities": 0.0, "petrol": 0.0, "etc": []},
            "reasons": []
        }
        lines = yaml_text.splitlines()
        i = 0
        current_section = None
        current_list = None
        current_item = None

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            # Top-level keys
            if not line.startswith(" ") and ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                current_section = None
                current_list = None
                current_item = None

                if val == "|":
                    block_lines = []
                    i += 1
                    while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                        block_lines.append(lines[i][2:] if lines[i].startswith("  ") else "")
                        i += 1
                    result[key] = "\n".join(block_lines).strip()
                    continue
                elif val == "[]" or val == "":
                    if key in ("archive", "outro", "expenses"):
                        current_section = key
                    elif key == "reasons":
                        current_list = "reasons"
                else:
                    val = self._unquote(val)
                    if val.isdigit():
                        result[key] = int(val)
                    else:
                        try:
                            result[key] = float(val)
                        except ValueError:
                            result[key] = val
                i += 1
                continue

            # Section sub-items
            if current_section == "expenses":
                if stripped.startswith("etc:"):
                    current_list = "etc"
                    i += 1
                    continue
                elif current_list == "etc":
                    if stripped.startswith("- "):
                        # New etc list item
                        current_item = {}
                        result["expenses"]["etc"].append(current_item)
                        sub_content = stripped[2:].strip()
                        if ":" in sub_content:
                            sk, sv = sub_content.split(":", 1)
                            sk, sv = sk.strip(), self._unquote(sv)
                            current_item[sk] = float(sv) if (sv.replace(".", "", 1).isdigit() and "." in sv) else (int(sv) if sv.isdigit() else sv)
                    elif current_item is not None and ":" in stripped:
                        sk, sv = stripped.split(":", 1)
                        sk, sv = sk.strip(), self._unquote(sv)
                        current_item[sk] = float(sv) if (sv.replace(".", "", 1).isdigit() and "." in sv) else (int(sv) if sv.isdigit() else sv)
                    i += 1
                    continue
                elif ":" in stripped:
                    sk, sv = stripped.split(":", 1)
                    sk, sv = sk.strip(), self._unquote(sv)
                    try:
                        result["expenses"][sk] = float(sv)
                    except ValueError:
                        result["expenses"][sk] = sv
                    i += 1
                    continue

            # Reasons list items
            if current_list == "reasons" and stripped.startswith("- "):
                reason_val = self._unquote(stripped[2:])
                result["reasons"].append(reason_val)
                i += 1
                continue

            # Outro / Archive sub-keys
            if current_section in ("archive", "outro"):
                if ":" in stripped:
                    sk, sv = stripped.split(":", 1)
                    sk = sk.strip()
                    sv = sv.strip()
                    if sv == "|":
                        block_lines = []
                        i += 1
                        while i < len(lines) and (lines[i].startswith("    ") or lines[i].startswith("  ") or not lines[i].strip()):
                            block_lines.append(lines[i].strip())
                            i += 1
                        result[current_section][sk] = "\n".join(block_lines).strip()
                        continue
                    else:
                        result[current_section][sk] = self._unquote(sv)

            i += 1

        return result

    def _parse_body_days(self, body_text: str) -> List[DayEntry]:
        """Parses the Markdown body text into daily entries and meals."""
        days = []
        # Split by ## YYYY-MM-DD (Day)
        day_sections = re.split(r'(?m)^##\s+(\d{4}-\d{2}-\d{2})\s*\((.*?)\)', body_text)

        # day_sections: [preamble, date_1, day_1, content_1, date_2, day_2, content_2, ...]
        if len(day_sections) > 1:
            for idx in range(1, len(day_sections), 3):
                date_str = day_sections[idx].strip()
                day_of_week = day_sections[idx + 1].strip()
                day_content = day_sections[idx + 2] if idx + 2 < len(day_sections) else ""

                meals = self._parse_meals(day_content)
                days.append(DayEntry(
                    date_str=date_str,
                    day_of_week=day_of_week,
                    meals=meals
                ))

        return days

    def _parse_meals(self, day_text: str) -> List[MealItem]:
        """Parses meal headers (### Dish Name [Restaurant]) and their attributes."""
        meals = []
        # Split by ### Dish Name
        meal_chunks = re.split(r'(?m)^###\s+(.*?)$', day_text)

        if len(meal_chunks) > 1:
            for idx in range(1, len(meal_chunks), 2):
                raw_title = meal_chunks[idx].strip()
                meal_body = meal_chunks[idx + 1] if idx + 1 < len(meal_chunks) else ""

                dish_name = raw_title.strip()
                restaurant = ""

                # Robust bracket matching: supports "Dish [Rest]" and "[Dish] [Rest]"
                if dish_name.endswith("]") and "[" in dish_name:
                    last_open = dish_name.rfind("[")
                    restaurant = dish_name[last_open + 1:-1].strip()
                    dish_name = dish_name[:last_open].strip()

                # Clean any outer brackets from dish_name
                if dish_name.startswith("[") and dish_name.endswith("]"):
                    dish_name = dish_name[1:-1].strip()

                # Check if this is an unfilled template placeholder slot
                is_placeholder_name = (
                    not dish_name 
                    or dish_name.lower() in ("dish name", "[dish name]", "", "- price: rm", "- price:", "- meal:", "- image:")
                    or dish_name.startswith("- Price:") 
                    or dish_name.startswith("- Meal:") 
                    or dish_name.startswith("- Image:")
                )
                is_placeholder_restaurant = (not restaurant or restaurant.lower() in ("restaurant", "[restaurant]", ""))
                
                if is_placeholder_name and is_placeholder_restaurant:
                    continue

                if is_placeholder_name and not is_placeholder_restaurant:
                    dish_name = f"Meal [{restaurant}]"

                # Parse attributes from lines starting with - Key: Value
                price_str = ""
                price_val = 0.0
                meal_type = "Lunch"
                image_path = ""
                desc_lines = []
                item_bullets = []

                body_lines = meal_body.strip().splitlines()
                reading_meta = True
                raw_content_lines = []

                for line in body_lines:
                    line_s = line.strip()
                    if reading_meta and line_s.startswith("- Price:"):
                        price_str = line_s[len("- Price:"):].strip()
                        price_val = self._parse_price_value(price_str)
                    elif reading_meta and line_s.startswith("- Meal:"):
                        meal_type = line_s[len("- Meal:"):].strip()
                    elif reading_meta and line_s.startswith("- Image:"):
                        image_path = self._unquote(line_s[len("- Image:"):].strip())
                    else:
                        reading_meta = False
                        raw_content_lines.append(line)
                        if line_s.startswith("- ") or line_s.startswith("* "):
                            item_bullets.append(line_s[2:].strip())

                description = "\n".join(raw_content_lines).strip()

                meals.append(MealItem(
                    dish_name=dish_name,
                    restaurant=restaurant,
                    price_str=price_str,
                    price=price_val,
                    meal_type=meal_type,
                    image=image_path,
                    description=description,
                    items=item_bullets
                ))

        return meals

    def _parse_price_value(self, price_str: str) -> float:
        """Parses a price string like 'RM 8.50', 'Free', or '<s>RM 5.50?</s> Free' into float."""
        if not price_str:
            return 0.0
        cleaned = re.sub(r'<[^>]*>', ' ', price_str).strip()
        if "free" in cleaned.lower():
            return 0.0
        nums = re.findall(r'\d+(?:\.\d+)?', cleaned)
        if nums:
            return float(nums[-1])
        return 0.0
