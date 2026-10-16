import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.config import CONTENT_DIR, IMAGES_DIR, load_site_config
from pipeline.parser import MarkdownContentParser
from pipeline.builder import SiteBuilder

def validate_content_and_assets() -> int:
    """Validates markdown syntax, frontmatter integrity, image existence, and build viability."""
    errors = []
    warnings = []
    
    print("[*] Dine with Junn - CI Validator")
    print(f"[*] Project root: {BASE_DIR}")
    
    # 1. Validate config.json
    try:
        config = load_site_config()
        if not config:
            errors.append("config.json is empty or invalid.")
        else:
            print("[+] config.json parsed successfully.")
    except Exception as e:
        errors.append(f"config.json load error: {e}")

    # 2. Validate all markdown content files
    parser = MarkdownContentParser()
    md_files = sorted(CONTENT_DIR.glob("*.md"))
    
    if not md_files:
        errors.append("No markdown files found in content/ directory!")
        
    print(f"[*] Validating {len(md_files)} markdown log(s)...")

    for md_file in md_files:
        rel_md = md_file.relative_to(BASE_DIR)
        try:
            month = parser.parse_file(md_file)
        except Exception as e:
            errors.append(f"[{rel_md}] Failed to parse markdown: {e}")
            continue

        # Frontmatter integrity
        expected_slug = md_file.stem
        if month.slug != expected_slug:
            errors.append(f"[{rel_md}] Slug mismatch: expected '{expected_slug}', found '{month.slug}'")

        try:
            exp_y, exp_m = map(int, expected_slug.split("-"))
            if month.year != exp_y or month.month != exp_m:
                errors.append(f"[{rel_md}] Year/Month mismatch: expected {exp_y}-{exp_m:02d}, found {month.year}-{month.month:02d}")
        except ValueError:
            errors.append(f"[{rel_md}] Filename '{md_file.name}' does not follow YYYY-MM.md format")

        if not month.title.strip():
            warnings.append(f"[{rel_md}] Missing or empty title in frontmatter.")

        # Check archive hero image
        if month.archive.image:
            img_path = month.archive.image.strip('"\'')
            if img_path and not (BASE_DIR / img_path).exists():
                errors.append(f"[{rel_md}] archive.image not found on disk: '{img_path}'")

        # Check outro image
        if month.outro.image:
            img_path = month.outro.image.strip('"\'')
            if img_path and not (BASE_DIR / img_path).exists():
                errors.append(f"[{rel_md}] outro.image not found on disk: '{img_path}'")

        # Check each meal entry and meal image
        for day in month.days:
            for meal in day.meals:
                if not meal.dish_name.strip():
                    errors.append(f"[{rel_md}] Meal on {day.date_str} has empty dish name.")

                # Check meal photo if specified
                if meal.image:
                    clean_img = meal.image.strip('"\'')
                    if clean_img:
                        full_img_path = BASE_DIR / clean_img
                        if not full_img_path.exists():
                            errors.append(f"[{rel_md}] Meal photo missing: '{clean_img}' ({day.date_str} - {meal.dish_name})")

    # 3. Smoke Test SiteBuilder
    print("[*] Running SiteBuilder smoke test...")
    try:
        builder = SiteBuilder()
        builder.build_all(export_csv=False)
        print("[+] SiteBuilder build_all() completed successfully.")
    except Exception as e:
        errors.append(f"SiteBuilder smoke test failed: {e}")

    # Print summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    if warnings:
        print(f"\n[!] Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")

    if errors:
        print(f"\n[X] Errors ({len(errors)}):")
        for err in errors:
            print(f"    - {err}")
        print("\n[FAILED] CI Validation failed. Please resolve the errors above.")
        return 1

    print(f"\n[PASSED] All {len(md_files)} logs, assets, and build smoke tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(validate_content_and_assets())
