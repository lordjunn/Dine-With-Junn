import sys
import argparse
import datetime
import json
import re
from pathlib import Path
from typing import Optional

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.migrator import V1HtmlMigrator
from pipeline.config import BASE_DIR, CONTENT_DIR, V1_BASE_DIR


def _load_recurring_expenses() -> dict:
    """Loads recurring monthly expenses from config.json."""
    config_path = BASE_DIR / "config.json"
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read {config_path.name}: {exc}") from exc

    recurring = config.get("recurring_monthly_expenses", {})
    if not isinstance(recurring, dict):
        raise ValueError("config.json recurring_monthly_expenses must be an object.")
    return recurring


def _yaml_scalar(value) -> str:
    """Formats a simple config value safely for the generated YAML."""
    if isinstance(value, str):
        return json.dumps(value)
    if value is None:
        return ""
    return str(value)


def _render_recurring_expenses() -> str:
    """Renders configured recurring expenses for a month's frontmatter."""
    recurring = _load_recurring_expenses()
    adulting_fees = recurring.get("adulting_fees", [])
    if adulting_fees and not isinstance(adulting_fees, list):
        raise ValueError("config.json adulting_fees must be a list.")

    lines = ["  Adulting fees:"]
    for item in adulting_fees:
        if not isinstance(item, dict) or not str(item.get("label", "")).strip():
            raise ValueError("Each adulting fee must be an object with a label.")
        lines.append(f"    - label: {_yaml_scalar(item['label'])}")
        lines.append(f"      day: {_yaml_scalar(item.get('day'))}")
        lines.append(f"      amount: {_yaml_scalar(item.get('amount', 0.0))}")
        if item.get("note"):
            lines.append(f"      note: {_yaml_scalar(item['note'])}")
    if not adulting_fees:
        lines.append("    # Add recurring fees here in config.json.")

    for key in ("utilities", "petrol"):
        lines.append(f"  {key}: {_yaml_scalar(recurring.get(key, 0.0))}")
    lines.append("  etc: []")
    return "\n".join(lines)


def _is_empty_month_template(month_path: Path) -> bool:
    """Returns true only when a month has no meaningful user-entered content."""
    from pipeline.parser import MarkdownContentParser

    month = MarkdownContentParser().parse_file(month_path)
    if any(day.meals for day in month.days):
        return False
    expenses = month.expenses
    recurring = _load_recurring_expenses()
    expected_adulting = {
        (
            str(item.get("label", "")).strip(),
            float(item.get("amount", 0.0)),
            int(item["day"]) if item.get("day") is not None else None,
            str(item.get("note", "")).strip(),
        )
        for item in recurring.get("adulting_fees", [])
        if isinstance(item, dict)
    }
    actual_adulting = {
        (item.label, item.amount, item.day, item.note)
        for item in expenses.adulting_items
    }
    expected_adulting_total = sum(item[1] for item in expected_adulting)
    if (
        expenses.rental != expected_adulting_total
        or expenses.utilities != float(recurring.get("utilities", 0.0))
        or expenses.petrol != float(recurring.get("petrol", 0.0))
        or actual_adulting != expected_adulting
        or any(item.amount != 0 for item in expenses.etc)
        or any(item.amount != 0 for item in expenses.work_claims)
    ):
        return False

    intro = month.intro_text.strip()
    intro_is_placeholder = (
        not intro
        or intro.startswith("Opening thoughts, mood, and predictions for ")
        or intro == "Your opening predictions, hopes, and fears for the month..."
    )
    meaningful_sections = (
        not intro_is_placeholder,
        any(reason.strip() and not reason.startswith("Milestone 1:") for reason in month.reasons),
        bool(month.archive.teaser.strip() or month.archive.image.strip()),
        bool(month.outro.title.strip() or month.outro.image.strip() or month.outro.prose.strip()),
    )
    if any(meaningful_sections):
        return False
    return True

def cmd_migrate(args):
    """Migrates a legacy V1 HTML month file to V2 Markdown."""
    target_path = Path(args.html_file)
    if not target_path.exists():
        # Check in V1 default path
        v1_default = V1_BASE_DIR / "Logs" / target_path.name if V1_BASE_DIR else None
        if v1_default and v1_default.exists():
            target_path = v1_default
        else:
            print(f"[Error] Target HTML file does not exist: {args.html_file}")
            sys.exit(1)

    migrator = V1HtmlMigrator()
    print(f"[*] Migrating: {target_path} ...")
    output_path = migrator.migrate_file(target_path)
    print(f"[+] Successfully migrated to: {output_path}")

def _snapshot_sources() -> dict:
    """Maps every watched source file to (mtime_ns, size) for change detection."""
    snapshot = {}
    roots = [BASE_DIR / name for name in ("content", "templates", "static", "images", "themes")]
    paths = [BASE_DIR / "config.json"]
    for root in roots:
        if root.exists():
            paths.extend(p for p in root.rglob("*") if p.is_file())
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue  # file vanished mid-scan (editor temp file etc.)
        snapshot[path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _watch_and_build(build_once, interval: float = 1.0):
    """Runs build_once() now, then again whenever a source file changes. Ctrl+C to stop."""
    import time

    def safe_build():
        try:
            build_once()
        except Exception as exc:  # keep watching so a half-saved file doesn't kill the loop
            print(f"[!] Build failed: {exc}")

    safe_build()
    previous = _snapshot_sources()
    print("[*] Watching content/, templates/, static/, images/, themes/ and config.json... (Ctrl+C to stop)")
    print("    Changes to Python files in pipeline/ or scripts/ need a restart.")
    try:
        while True:
            time.sleep(interval)
            current = _snapshot_sources()
            if current == previous:
                continue
            changed = sorted({p for p in current.keys() | previous.keys() if current.get(p) != previous.get(p)})
            time.sleep(0.3)  # let the editor finish writing
            names = ", ".join(str(p.relative_to(BASE_DIR)) for p in changed[:3])
            more = f" (+{len(changed) - 3} more)" if len(changed) > 3 else ""
            print(f"[*] Change detected: {names}{more}")
            previous = _snapshot_sources()
            safe_build()
    except KeyboardInterrupt:
        print("\n[*] Watch stopped.")


def cmd_build(args):
    """Builds the static site to /dist."""
    print("[*] Dine with Junn V2 Static Site Builder")
    try:
        from pipeline.builder import SiteBuilder
    except ImportError:
        print("[!] Builder module will be activated in Phase 5.")
        return

    export_csv = True if getattr(args, "csv", False) else None

    def build_once():
        SiteBuilder().build_all(export_csv=export_csv)
        print("[+] Build complete! Static site generated in /dist")

    if getattr(args, "watch", False):
        _watch_and_build(build_once)
    else:
        build_once()

def cmd_serve(args):
    """Serves the /dist folder on a local web server and opens the browser."""
    import http.server
    import socketserver
    import webbrowser
    from pipeline.config import DIST_DIR

    if not (DIST_DIR / "index.html").exists():
        print("[*] Site not built yet. Building first...")
        from pipeline.builder import SiteBuilder
        SiteBuilder().build_all()

    port = args.port
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(DIST_DIR), **k)
    
    print(f"[*] Serving Dine with Junn V2 at: http://localhost:{port}/")
    print("[*] Opening your web browser... (Press Ctrl+C to stop)")
    webbrowser.open(f"http://localhost:{port}/index.html")

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")

def cmd_sync_images(args):
    """Fetches photos from Discord and launches visual review UI."""
    from pipeline.discord_sync import DiscordImageSyncer

    slug = args.slug or _find_latest_image_sync_month()
    if not slug:
        print("[Error] No month with at least one written meal was found in content/.")
        print("       Add a meal first, or provide a specific slug.")
        return

    if not args.slug:
        print(f"[*] No month specified; selected {slug}.")

    syncer = DiscordImageSyncer()
    syncer.launch_review_server(slug, limit=args.limit, mock=args.mock)


def _find_latest_image_sync_month() -> Optional[str]:
    """Finds the newest month with meals, preferring meals without image paths."""
    from pipeline.parser import MarkdownContentParser

    parser = MarkdownContentParser()
    months_with_meals: list[tuple[str, bool]] = []
    for month_path in sorted(CONTENT_DIR.glob("*.md"), key=lambda path: path.stem, reverse=True):
        try:
            month = parser.parse_file(month_path)
        except (OSError, ValueError, TypeError):
            continue

        meals = [meal for day in month.days for meal in day.meals]
        if meals:
            has_unlinked_meal = any(not meal.image.strip() for meal in meals)
            months_with_meals.append((month_path.stem, has_unlinked_meal))

    for slug, has_unlinked_meal in months_with_meals:
        if has_unlinked_meal:
            return slug
    return months_with_meals[0][0] if months_with_meals else None

def cmd_validate(args):
    """Runs data, markdown, and image asset validation checks."""
    from scripts.validate import validate_content_and_assets
    code = validate_content_and_assets()
    sys.exit(code)

def _get_previous_month_era(year: int, month: int) -> tuple[str, str]:
    """Finds previous month's markdown file and extracts its era. Returns (era, source_description)."""
    import re
    from pipeline.config import CONTENT_DIR

    # 1. Exact previous calendar month (e.g. 2026-09 for 2026-10)
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_slug = f"{prev_y:04d}-{prev_m:02d}"
    candidate_file = CONTENT_DIR / f"{prev_slug}.md"

    # 2. If exact previous file doesn't exist, pick the latest file prior to this month
    target_slug = f"{year:04d}-{month:02d}"
    if not candidate_file.exists():
        earlier_files = sorted(f for f in CONTENT_DIR.glob("*.md") if f.stem < target_slug)
        if earlier_files:
            candidate_file = earlier_files[-1]
        else:
            all_files = sorted(CONTENT_DIR.glob("*.md"))
            candidate_file = all_files[-1] if all_files else None

    if candidate_file and candidate_file.exists():
        try:
            content = candidate_file.read_text(encoding="utf-8")
            m = re.search(r'^\s*era:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
            if m and m.group(1).strip():
                return m.group(1).strip(), candidate_file.name
        except Exception:
            pass

    return "Unknown grounds", "default"

def cmd_new_month(args):
    """Generates a complete new month Markdown template with exact calendar dates."""
    import calendar
    import datetime
    from pipeline.config import CONTENT_DIR, IMAGES_DIR

    # 1. Determine Year & Month
    if args.month_str:
        target = args.month_str.strip()
        if "-" in target:
            parts = target.split("-")
            year = int(parts[0])
            month = int(parts[1])
        else:
            dt = datetime.datetime.strptime(target, "%b %Y")
            year = dt.year
            month = dt.month
    else:
        # Automatically compute NEXT month following latest existing file in content/
        existing_files = sorted(CONTENT_DIR.glob("*.md"))
        if existing_files:
            latest_stem = existing_files[-1].stem
            y_str, m_str = latest_stem.split("-")
            y, m = int(y_str), int(m_str)
            if m == 12:
                year, month = y + 1, 1
            else:
                year, month = y, m + 1
        else:
            now = datetime.datetime.now()
            year, month = now.year, now.month

    month_name = calendar.month_name[month]
    slug = f"{year:04d}-{month:02d}"
    out_md_path = CONTENT_DIR / f"{slug}.md"

    if out_md_path.exists() and not args.force:
        if args.refresh_empty:
            if _is_empty_month_template(out_md_path):
                print(f"[*] {out_md_path.name} is still empty; refreshing its template.")
            else:
                print(f"[!] {out_md_path.name} has meaningful content; refusing to refresh it.")
                print("    Use --force only if you intentionally want to overwrite it.")
                return
        else:
            print(f"[!] {out_md_path.name} already exists! Use --refresh-empty or --force.")
            return

    if args.era:
        era = args.era
        print(f"[*] Era set to: '{era}' (via --era)")
    else:
        era, source = _get_previous_month_era(year, month)
        if source != "default":
            print(f"[*] Era set to: '{era}' (inherited from {source})")
        else:
            print(f"[*] Era set to default: '{era}'")

    # 2. Generate Calendar Days Skeleton
    num_days = calendar.monthrange(year, month)[1]
    days_blocks = []
    for day in range(1, num_days + 1):
        day_date = datetime.date(year, month, day)
        day_str = day_date.strftime("%Y-%m-%d")
        weekday_str = day_date.strftime("%A")

        days_blocks.append(f"""## {day_str} ({weekday_str})

### [Dish Name] [Restaurant]
- Price: RM 0.00
- Meal: Breakfast
- Image: ""

Breakfast review...

### [Dish Name] [Restaurant]
- Price: RM 0.00
- Meal: Lunch
- Image: ""

Lunch review...
- Portion: details
- Taste: details

### [Dish Name] [Restaurant]
- Price: RM 0.00
- Meal: Dinner
- Image: ""

Dinner review...
""")

    # 3. Assemble Full Markdown File
    md_content = f"""---
year: {year}
month: {month}
slug: "{slug}"
title: "Food Archive - {month_name} {year}"
nom_nom_days: 0
reasons:
  - "Milestone 1: 1/{month}"
intro_text: |
  Opening thoughts, mood, and predictions for {month_name} {year}...
archive:
  era: "{era}"
  teaser: ""
  image: ""
outro:
  title: ""
  image: ""
  # Closing reflections, post-month review, and afterthoughts for {month_name} {year}...
  prose: |
    
expenses:
{_render_recurring_expenses()}
---

{"".join(days_blocks).strip()}
"""

    if args.dry_run:
        print(f"[*] --dry-run: Would generate {out_md_path} ({num_days} days).")
        print(f"[*] Preview of top frontmatter:\n{md_content[:280]}...")
        return

    out_md_path.write_text(md_content, encoding="utf-8")
    print(f"[+] Successfully generated new month template: {out_md_path.name} ({num_days} days)")

    # Ensure images folder exists: images/YYYY/MonthName/
    month_img_dir = IMAGES_DIR / str(year) / month_name
    month_img_dir.mkdir(parents=True, exist_ok=True)
    print(f"[+] Created image directory: {month_img_dir}")

_DAY_HEADER_RE = re.compile(r'(?m)^##\s+(\d{4}-\d{2}-\d{2})\s*\(.*?\)')
_TEMPLATE_LINE_RES = [
    re.compile(r'^###\s*\[Dish Name\]\s*\[Restaurant\]$', re.I),
    re.compile(r'^- Price:\s*(RM\s*0(\.0+)?)?$', re.I),
    re.compile(r'^- Meal:\s*\w*$', re.I),
    re.compile(r'^- Image:\s*(""|\'\')?$', re.I),
    re.compile(r'^(Breakfast|Lunch|Dinner) review\.\.\.$', re.I),
    re.compile(r'^- (Portion|Taste): details$', re.I),
]


def _is_empty_day_section(section: str) -> bool:
    """True when a day section holds nothing but untouched template placeholders."""
    lines = section.splitlines()[1:]  # first line is the '## date' header
    for line in lines:
        stripped = line.strip()
        if stripped and not any(rx.match(stripped) for rx in _TEMPLATE_LINE_RES):
            return False
    return True


def _purge_empty_days_in_text(text: str, before: datetime.date) -> tuple[str, list[str]]:
    """Removes empty day sections dated before `before`. Returns (new_text, purged_dates)."""


    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        return text, []
    body = parts[2]

    matches = list(_DAY_HEADER_RE.finditer(body))
    if not matches:
        return text, []

    kept = [body[:matches[0].start()]]
    purged: list[str] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        section = body[match.start():end]
        try:
            day_date = datetime.date.fromisoformat(match.group(1))
        except ValueError:
            kept.append(section)
            continue
        if day_date < before and _is_empty_day_section(section):
            purged.append(match.group(1))
        else:
            kept.append(section)

    if not purged:
        return text, []
    return "---" + parts[1] + "---" + "".join(kept), purged


def cmd_purge_empty(args):
    """Deletes day sections with no logged meals, from the start of the month(s) up to yesterday."""
    if args.before:
        try:
            before = datetime.date.fromisoformat(args.before)
        except ValueError:
            print(f"[Error] Invalid --before date '{args.before}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        before = datetime.date.today()

    if args.month_str:
        files = [CONTENT_DIR / f"{args.month_str.strip()}.md"]
        if not files[0].exists():
            print(f"[Error] Month file not found: {files[0]}")
            sys.exit(1)
    else:
        files = sorted(CONTENT_DIR.glob("*.md"))

    print(f"[*] Purging empty days dated before {before.isoformat()} (days on/after it are kept).")
    total = 0
    for md_path in files:
        with md_path.open("r", encoding="utf-8", newline="") as f:
            text = f.read()
        new_text, purged = _purge_empty_days_in_text(text, before)
        if not purged:
            continue
        total += len(purged)
        label = "Would purge" if args.dry_run else "Purged"
        print(f"[+] {md_path.name}: {label} {len(purged)} empty day(s): {purged[0]} .. {purged[-1]}")
        if not args.dry_run:
            with md_path.open("w", encoding="utf-8", newline="") as f:
                f.write(new_text)

    if total == 0:
        print("[*] Nothing to purge.")
    elif args.dry_run:
        print(f"[*] --dry-run: {total} day(s) would be removed; no files were changed.")
    else:
        print(f"[+] Removed {total} empty day(s).")

def _smart_sync_file(src: Path, dst: Path) -> bool:
    """Copies src to dst ONLY if dst does not exist or has different size/mtime."""
    if dst.exists():
        src_stat = src.stat()
        dst_stat = dst.stat()
        # If identical size and modified time matches within 1 second, skip copy
        if src_stat.st_size == dst_stat.st_size and abs(src_stat.st_mtime - dst_stat.st_mtime) < 1.0:
            return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(src, dst)
    return True

def cmd_sync_hdd(args):
    """Safely copies only modified/new source files to an external HDD path without touching .git or .venv."""
    import os

    dest_input = args.dest
    if not dest_input:
        dest_input = os.getenv("HDD_PATH")
    if not dest_input and Path(r"K:\Github\Dine With Junn").exists():
        dest_input = r"K:\Github\Dine With Junn"

    if not dest_input:
        print("[Error] Please provide the target HDD destination path!\nUsage: python scripts/cli.py sync-hdd \"E:\\Dine-With-Junn\"")
        return

    dest_dir = Path(dest_input).resolve()
    if not dest_dir.exists():
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"[*] Created target directory: {dest_dir}")
        except Exception as e:
            print(f"[Error] Could not access or create target directory {dest_dir}: {e}")
            return

    # 1. If target is a Git repo, pull remote changes first (e.g. from GitHub Actions)
    if (dest_dir / ".git").exists():
        print(f"[*] Checking for remote Git updates at: {dest_dir}")
        try:
            import subprocess
            res = subprocess.run(["git", "pull"], cwd=str(dest_dir), capture_output=True, text=True, check=False)
            if res.returncode == 0:
                stdout_msg = res.stdout.strip()
                if "Already up to date" in stdout_msg:
                    print("    -> Repo is up to date with remote.")
                else:
                    print(f"    -> Pulled latest remote changes:\n{stdout_msg}")
                    # If remote had updates (e.g. CI auto-generated CSVs or remote edits), sync them back to OneDrive
                    for d in ["data", "content"]:
                        pulled_dir = dest_dir / d
                        if pulled_dir.exists():
                            for p_file in pulled_dir.rglob("*"):
                                if p_file.is_file():
                                    local_f = BASE_DIR / p_file.relative_to(dest_dir)
                                    if not local_f.exists() or p_file.stat().st_mtime > local_f.stat().st_mtime:
                                        _smart_sync_file(p_file, local_f)
                                        print(f"    -> Synced remote update to OneDrive: {local_f.name}")
            else:
                err_msg = res.stderr.strip() or res.stdout.strip()
                print(f"    -> [Notice] git pull output: {err_msg}")
        except Exception as e:
            print(f"    -> [Notice] Could not run git pull: {e}")

    print(f"[*] Starting smart incremental sync to: {dest_dir}")

    sync_dirs = ["content", "images", "templates", "static", "pipeline", "scripts", ".github"]
    sync_files = ["config.json", "requirements.txt", "README.md", ".gitignore", ".env.example"]

    copied_files = 0
    skipped_files = 0

    # Sync directories recursively with incremental checks
    for d in sync_dirs:
        src_dir = BASE_DIR / d
        if not src_dir.exists():
            continue
        for src_file in src_dir.rglob("*"):
            if src_file.is_file():
                # Ignore temp / cache patterns
                if "__pycache__" in src_file.parts or src_file.suffix in [".pyc", ".DS_Store"]:
                    continue
                rel_path = src_file.relative_to(BASE_DIR)
                dst_file = dest_dir / rel_path
                if _smart_sync_file(src_file, dst_file):
                    copied_files += 1
                else:
                    skipped_files += 1

    # Sync top-level files
    for f in sync_files:
        src_file = BASE_DIR / f
        if src_file.exists() and src_file.is_file():
            dst_file = dest_dir / f
            if _smart_sync_file(src_file, dst_file):
                copied_files += 1
            else:
                skipped_files += 1

    # Clean up obsolete generate_csv.yml on HDD if present
    old_csv_wf = dest_dir / ".github" / "workflows" / "generate_csv.yml"
    if old_csv_wf.exists():
        try:
            old_csv_wf.unlink()
            print(f"[*] Cleaned up retired workflow on HDD: {old_csv_wf.name}")
        except Exception:
            pass

    print(f"[+] Smart sync complete!")
    print(f"    -> Updated / Copied: {copied_files} file(s)")
    print(f"    -> Skipped (unchanged): {skipped_files} file(s)")
    print(f"[*] Target's .git repository and .venv environments were safely protected.")

def main():
    parser = argparse.ArgumentParser(description="Dine with Junn V2 - Master CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Sync-hdd command
    sync_hdd_parser = subparsers.add_parser("sync-hdd", help="Copy project files to an external HDD directory safely (protects .git/.venv)")
    sync_hdd_parser.add_argument("dest", nargs="?", type=str, help="Destination directory path (e.g. 'E:\\Dine-With-Junn')")

    # New-month command
    new_month_parser = subparsers.add_parser("new-month", help="Auto-generate next month's Markdown template with calendar days")
    new_month_parser.add_argument("month_str", nargs="?", type=str, help="Optional target month e.g. '2026-09'. Defaults to next month.")
    new_month_parser.add_argument("--era", type=str, default=None, help="Era chapter title (defaults to inheriting previous month's era)")
    new_month_parser.add_argument("--force", action="store_true", help="Overwrite if file already exists")
    new_month_parser.add_argument(
        "--refresh-empty",
        action="store_true",
        help="Replace an existing month only when it still has no meals, expenses, or notes",
    )
    new_month_parser.add_argument("--dry-run", action="store_true", help="Print preview without writing file")

    # Purge-empty command
    purge_parser = subparsers.add_parser(
        "purge-empty",
        help="Delete day sections with no logged meals, up to yesterday (today is kept)",
    )
    purge_parser.add_argument("month_str", nargs="?", type=str, help="Optional month slug e.g. '2026-11'. Defaults to all months.")
    purge_parser.add_argument("--before", type=str, default=None, help="Purge days before this YYYY-MM-DD date instead of today")
    purge_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without writing files")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a V1 HTML month file to Markdown")
    migrate_parser.add_argument("html_file", type=str, help="Path or filename of the V1 HTML file (e.g. 'Logs/Jul 26.html')")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build static site to /dist")
    build_parser.add_argument("--watch", action="store_true", help="Keep running and rebuild whenever source files change")
    build_parser.add_argument("--csv", action="store_true", help="Force export CSV datasets locally (default: skipped locally, handled via GitHub Actions)")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start local web server and open site in browser")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080)")

    # Sync-images command
    sync_parser = subparsers.add_parser("sync-images", help="Fetch photos from Discord and launch visual review UI")
    sync_parser.add_argument(
        "slug",
        nargs="?",
        type=str,
        help="Optional month slug (defaults to newest month with an unlinked meal)",
    )
    sync_parser.add_argument("--limit", type=int, default=None, help="Number of Discord photos to fetch (defaults to number of meals)")
    sync_parser.add_argument("--mock", action="store_true", help="Run in mock/offline mode with sample photos")

    # Validate command
    subparsers.add_parser("validate", help="Validate all markdown logs, images, and test site generation")

    # Help command
    subparsers.add_parser("help", help="Show this help message")

    args = parser.parse_args()
    if not args.command or args.command == "help":
        parser.print_help()
        sys.exit(0)

    if args.command == "sync-hdd":
        cmd_sync_hdd(args)
    elif args.command == "new-month":
        cmd_new_month(args)
    elif args.command == "purge-empty":
        cmd_purge_empty(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "sync-images":
        cmd_sync_images(args)
    elif args.command == "validate":
        cmd_validate(args)

if __name__ == "__main__":
    main()
