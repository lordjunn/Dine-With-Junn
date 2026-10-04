import re
import shutil
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
                resized.save(dest_path, "PNG", optimize=True)
        except ImportError:
            # Fallback if Pillow is not yet installed in bare environment: copy original
            shutil.copy2(src_path, dest_path)

        # Return relative path for Markdown
        return f"images/{year}/{month_name}/{filename}"

    def update_markdown_meal_image(self, md_path: Path, dish_name: str, new_image_path: str):
        """Updates or inserts the '- Image: ...' line for a specific dish in the Markdown file."""
        if not md_path.exists():
            return

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the ### Dish Name section
        pattern = rf'(###\s+{re.escape(dish_name)}[^\n]*\n)(.*?)(?=\n###|\n##|$)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
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

            content = content[:match.start()] + header + updated_body + content[match.end():]

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
