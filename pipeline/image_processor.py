import re
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple

from pipeline.config import BASE_DIR, IMAGES_DIR, MEAL_IMAGE_SIZE

class ImageProcessor:
    """Handles square resizing, optimization, and Markdown path injection for meal photos."""

    def __init__(self, images_dir: Optional[Path] = None):
        self.images_dir = Path(images_dir) if images_dir else IMAGES_DIR

    def process_and_save(self, src_path: Path, year: int, month_name: str, filename: str) -> str:
        """Resizes/crops an image to 400x400 and saves it to images/YYYY/Month/filename."""
        target_dir = self.images_dir / str(year) / month_name
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / filename

        try:
            from PIL import Image, ImageOps
            with Image.open(src_path) as img:
                img = ImageOps.exif_transpose(img)  # auto-rotate based on phone camera orientation
                img = img.convert("RGB")
                # Direct resize to MEAL_IMAGE_SIZE (400x400) without cropping (preserves 100% of content)
                resized = img.resize(MEAL_IMAGE_SIZE, Image.Resampling.LANCZOS)
                output = BytesIO()
                resized.save(output, "PNG", optimize=True)
                output_bytes = output.getvalue()
                existing_bytes = dest_path.read_bytes() if dest_path.exists() else None
                if existing_bytes != output_bytes:
                    dest_path.write_bytes(output_bytes)
        except ImportError:
            # Fallback if Pillow is not yet installed in bare environment: copy original
            source_bytes = src_path.read_bytes()
            existing_bytes = dest_path.read_bytes() if dest_path.exists() else None
            if existing_bytes != source_bytes:
                dest_path.write_bytes(source_bytes)

        # Return relative path for Markdown
        return f"images/{year}/{month_name}/{filename}"

    def update_markdown_meal_image(
        self,
        md_path: Path,
        dish_name: str,
        new_image_path: str,
        date_str: str = "",
    ) -> bool:
        """Updates or inserts the '- Image: ...' line for a specific dish in the Markdown file."""
        if not md_path.exists():
            return False

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Match both `### Dish [Restaurant]` and `### [Dish] [Restaurant]` forms.
        title_pattern = rf'(?:{re.escape(dish_name)}|\[{re.escape(dish_name)}\])'
        meal_pattern = rf'(###\s+{title_pattern}(?:\s+\[[^\n]*\])?[^\n]*\n)(.*?)(?=\n###|\n##|$)'
        if date_str:
            day_pattern = rf'(^##\s+{re.escape(date_str)}[^\n]*\n)(.*?)(?=^##\s|\Z)'
            day_match = re.search(day_pattern, content, re.MULTILINE | re.DOTALL)
            if not day_match:
                return False
            day_content = day_match.group(2)
            match = re.search(meal_pattern, day_content, re.DOTALL)
            if not match:
                return False
            start = day_match.start(2) + match.start()
            end = day_match.start(2) + match.end()
        else:
            match = re.search(meal_pattern, content, re.DOTALL)
            if not match:
                return False
            start = match.start()
            end = match.end()

        header = match.group(1)
        meal_body = match.group(2)

        if "- Image:" in meal_body:
            # Replace existing - Image: line
            updated_body = re.sub(r'- Image:[^\n]*', f'- Image: {new_image_path}', meal_body)
        else:
            # Insert after - Meal: line or at start of body
            if "- Meal:" in meal_body:
                updated_body = re.sub(r'(- Meal:[^\n]*)', f'\\1\n- Image: {new_image_path}', meal_body)
            else:
                updated_body = f"- Image: {new_image_path}\n" + meal_body

        content = content[:start] + header + updated_body + content[end:]

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
