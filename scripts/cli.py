import sys
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.migrator import V1HtmlMigrator
from pipeline.config import CONTENT_DIR

def cmd_migrate(args):
    """Migrates a legacy V1 HTML month file to V2 Markdown."""
    target_path = Path(args.html_file)
    if not target_path.exists():
        # Check in V1 default path
        v1_default = Path(r"C:\Users\Junn Kit\OneDrive\Food blog\Logs") / target_path.name
        if v1_default.exists():
            target_path = v1_default
        else:
            print(f"[Error] Target HTML file does not exist: {args.html_file}")
            sys.exit(1)

    migrator = V1HtmlMigrator()
    print(f"[*] Migrating: {target_path} ...")
    output_path = migrator.migrate_file(target_path)
    print(f"[+] Successfully migrated to: {output_path}")

def cmd_build(args):
    """Builds the static site to /dist (Available in Phase 5)."""
    print("[*] Dine with Junn V2 Static Site Builder")
    try:
        from pipeline.builder import SiteBuilder
        builder = SiteBuilder()
        builder.build_all()
        print("[+] Build complete! Static site generated in /dist")
    except ImportError:
        print("[!] Builder module will be activated in Phase 5.")

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
    syncer = DiscordImageSyncer()
    syncer.launch_review_server(args.slug, limit=args.limit, mock=args.mock)

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
        print(f"[!] {out_md_path.name} already exists! Use --force if you want to overwrite.")
        return

    era = args.era if args.era else "Unknown grounds"

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
  prose: ""
expenses:
  rental: 0.00
  utilities: 0.00
  petrol: 0.00
  etc: []
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
    new_month_parser.add_argument("--era", type=str, default=None, help="Era chapter title (default: 'Unknown grounds')")
    new_month_parser.add_argument("--force", action="store_true", help="Overwrite if file already exists")
    new_month_parser.add_argument("--dry-run", action="store_true", help="Print preview without writing file")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a V1 HTML month file to Markdown")
    migrate_parser.add_argument("html_file", type=str, help="Path or filename of the V1 HTML file (e.g. 'Logs/Jul 26.html')")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build static site to /dist")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start local web server and open site in browser")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080)")

    # Sync-images command
    sync_parser = subparsers.add_parser("sync-images", help="Fetch photos from Discord and launch visual review UI")
    sync_parser.add_argument("slug", type=str, help="Month slug (e.g. '2026-08')")
    sync_parser.add_argument("--limit", type=int, default=None, help="Number of Discord photos to fetch (defaults to number of meals)")
    sync_parser.add_argument("--mock", action="store_true", help="Run in mock/offline mode with sample photos")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "sync-hdd":
        cmd_sync_hdd(args)
    elif args.command == "new-month":
        cmd_new_month(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "sync-images":
        cmd_sync_images(args)

if __name__ == "__main__":
    main()
