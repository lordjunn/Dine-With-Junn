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

def main():
    parser = argparse.ArgumentParser(description="Dine with Junn V2 - Master CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

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
    sync_parser.add_argument("--mock", action="store_true", help="Run in mock/offline mode with sample photos")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "sync-images":
        cmd_sync_images(args)

if __name__ == "__main__":
    main()
