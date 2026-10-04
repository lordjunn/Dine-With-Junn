import os
import json
import calendar
import urllib.request
import urllib.parse
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Any, Optional

from pipeline.config import (
    BASE_DIR, CONTENT_DIR, IMAGES_DIR, TEMPLATES_DIR,
    DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, REVIEW_SERVER_PORT
)
from pipeline.parser import MarkdownContentParser
from pipeline.image_processor import ImageProcessor

class DiscordImageSyncer:
    """Manages Discord photo fetching, local visual review server, and image processing."""

    def __init__(self, bot_token: Optional[str] = None, channel_id: Optional[str] = None):
        self.bot_token = bot_token or DISCORD_BOT_TOKEN
        self.channel_id = channel_id or DISCORD_CHANNEL_ID
        self.parser = MarkdownContentParser()
        self.processor = ImageProcessor()
        self.last_error: Optional[str] = None

    def fetch_candidates(self, limit: int = 50, mock: bool = False) -> List[Dict[str, Any]]:
        """Fetches candidate image attachments from Discord channel or generates mock items."""
        self.last_error = None
        if mock or not self.bot_token or not self.channel_id or "your_" in self.bot_token:
            if not mock and (not self.bot_token or not self.channel_id or "your_" in self.bot_token):
                print("[!] Discord credentials not configured in .env. Falling back to mock test candidates.")
                self.last_error = "Discord credentials (DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID) not configured in .env. Showing local mock photos."
            return self._generate_mock_candidates(limit=limit)

        candidates = []
        before = None
        try:
            import requests
            import urllib3
            urllib3.disable_warnings()

            while len(candidates) < limit:
                page_limit = min(100, max(limit, 20))
                url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages?limit={page_limit}"
                if before:
                    url += f"&before={before}"

                resp = requests.get(
                    url,
                    headers={
                        "Authorization": f"Bot {self.bot_token}",
                        "User-Agent": "DineWithJunn-Sync/2.0"
                    },
                    timeout=15,
                    verify=False
                )

                if resp.status_code != 200:
                    if resp.status_code == 403:
                        print("\n" + "=" * 65)
                        print(" [⚠️ DISCORD PERMISSION ERROR: NO ACCESS TO CHANNEL]")
                        print(f" -> Channel ID: {self.channel_id}")
                        print(" -> Reason: Bot lacks permission to view this channel or read history.")
                        print(" -> How to Fix in Discord:")
                        print("    1. In Discord, right-click the channel -> 'Edit Channel'.")
                        print("    2. Go to 'Permissions' -> Add your bot/role.")
                        print("    3. Enable: [✓] View Channel, [✓] Read Message History.")
                        print("=" * 65 + "\n")
                        self.last_error = f"Bot lacks permission to view Discord channel {self.channel_id} (HTTP 403 Forbidden). Ensure bot has 'View Channel' and 'Read Message History' permissions enabled."
                    elif resp.status_code == 401:
                        print("\n[⚠️ DISCORD AUTH ERROR] Invalid DISCORD_BOT_TOKEN! Check your .env file.\n")
                        self.last_error = "Invalid Discord Bot Token (HTTP 401 Unauthorized). Check your .env file."
                    elif resp.status_code == 404:
                        print(f"\n[⚠️ DISCORD ERROR] Channel ID {self.channel_id} not found (HTTP 404).\n")
                        self.last_error = f"Discord channel ID {self.channel_id} not found (HTTP 404)."
                    else:
                        print(f"[!] Discord API returned HTTP {resp.status_code}: {resp.text}")
                        self.last_error = f"Discord API returned HTTP {resp.status_code}."
                    break

                messages = resp.json()
                if not messages:
                    break

                for msg in messages:
                    for att in msg.get("attachments", []):
                        ct = att.get("content_type", "")
                        if "image" in ct or att.get("filename", "").lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            candidates.append({
                                "id": att.get("id"),
                                "filename": att.get("filename"),
                                "url": att.get("url"),
                                "thumbnail_url": att.get("proxy_url") or att.get("url")
                            })
                    # Check embeds as fallback
                    for embed in msg.get("embeds", []):
                        if embed.get("type") == "image":
                            e_url = embed.get("url") or embed.get("thumbnail", {}).get("url")
                            if e_url:
                                candidates.append({
                                    "id": str(len(candidates) + 1),
                                    "filename": "embed_image.png",
                                    "url": e_url,
                                    "thumbnail_url": e_url
                                })

                    if len(candidates) >= limit:
                        break

                before = messages[-1]["id"]

            # Reverse to chronological order (earliest uploaded first)
            candidates.reverse()
            result = candidates[-limit:] if len(candidates) >= limit else candidates
            print(f"[*] Fetched {len(result)} photo(s) from Discord (Pool: {limit}).")
            return result

        except Exception as e:
            print(f"[!] Discord API fetch failed ({e}). Falling back to mock test candidates.")
            self.last_error = f"Discord API connection failed: {e}. Falling back to mock test candidates."
            return self._generate_mock_candidates(limit=limit)

    def _generate_mock_candidates(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Generates mock photo candidates for offline testing."""
        candidates = []
        july_dir = IMAGES_DIR / "2026" / "July"
        if july_dir.exists():
            for p in sorted(july_dir.glob("*.png"))[:limit]:
                rel_url = f"/images/2026/July/{p.name}"
                candidates.append({
                    "id": p.stem,
                    "filename": p.name,
                    "url": rel_url,
                    "thumbnail_url": rel_url,
                    "local_path": str(p)
                })

        if not candidates:
            for i in range(1, limit + 1):
                candidates.append({
                    "id": f"mock_{i}",
                    "filename": f"sample_photo_{i}.png",
                    "url": f"https://picsum.photos/400/400?random={i}",
                    "thumbnail_url": f"https://picsum.photos/400/400?random={i}"
                })

        return candidates

    def launch_review_server(self, slug: str, limit: Optional[int] = None, mock: bool = False, port: int = REVIEW_SERVER_PORT):
        """Starts a temporary local webserver for visual confirmation in the default browser."""
        md_path = CONTENT_DIR / f"{slug}.md"
        if not md_path.exists():
            print(f"[Error] Month file not found: {md_path}")
            return

        month_data = self.parser.parse_file(md_path)

        # Smart pool sizing: calculate unlinked and total meals
        total_meals = sum(len(day.meals) for day in month_data.days)
        unlinked_meals = sum(
            1 for day in month_data.days for meal in day.meals 
            if not meal.image or not meal.image.strip()
        )
        target = unlinked_meals if unlinked_meals > 0 else total_meals
        target = max(target, 1)
        smart_pool = min(max(target * 2, 10), 50)

        # Respect CLI limit -> .env DISCORD_FETCH_LIMIT -> smart default
        env_limit = os.getenv("DISCORD_FETCH_LIMIT")
        if limit is not None:
            fetch_count = limit
            print(f"[*] Candidate limit set by CLI: {fetch_count}")
        elif env_limit and env_limit.strip().isdigit():
            fetch_count = int(env_limit.strip())
            print(f"[*] Candidate limit set by .env: {fetch_count}")
        else:
            fetch_count = smart_pool
            print(f"[*] Smart candidate pool auto-scaled to {fetch_count} photos ({unlinked_meals} unlinked meals out of {total_meals} total).")

        print(f"[*] Fetching candidate image pool ({fetch_count} photos max) for {month_data.title}...")
        candidates = self.fetch_candidates(limit=fetch_count, mock=mock)

        # Collect meals that have empty or missing images
        meals_list = []
        for day in month_data.days:
            for meal in day.meals:
                meals_list.append({
                    "date": day.date_str,
                    "day_of_week": day.day_of_week,
                    "dish_name": meal.dish_name,
                    "restaurant": meal.restaurant,
                    "meal_type": meal.meal_type,
                    "price_str": meal.price_str,
                    "current_image": meal.image
                })

        # Read review.html template
        review_html_path = TEMPLATES_DIR / "review.html"
        with open(review_html_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        warning_banner_html = ""
        if self.last_error:
            warning_banner_html = f'''
  <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; display: flex; align-items: flex-start; gap: 1rem;">
    <div style="font-size: 1.4rem; line-height: 1;">⚠️</div>
    <div style="flex: 1;">
      <div style="font-weight: 700; color: #fca5a5; font-size: 0.95rem; margin-bottom: 0.25rem;">Discord Permission / Connection Warning</div>
      <div style="font-size: 0.85rem; color: #fecaca; line-height: 1.4;">{self.last_error}</div>
      <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
        <strong>Quick Fix in Discord:</strong> Right-click channel &rarr; <strong>Edit Channel</strong> &rarr; <strong>Permissions</strong> &rarr; Add your bot role &rarr; Turn ON <code>View Channel</code> &amp; <code>Read Message History</code>.
      </div>
    </div>
  </div>
'''

        rendered_html = (
            template_content
            .replace("{{ month.title }}", month_data.title)
            .replace("{{ month.slug }}", month_data.slug)
            .replace("{{ warning_banner | safe }}", warning_banner_html)
            .replace("{{ meals_json | safe }}", json.dumps(meals_list))
            .replace("{{ candidates_json | safe }}", json.dumps(candidates))
        )

        syncer_self = self

        class ReviewRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                decoded_path = urllib.parse.unquote(self.path)
                if decoded_path == "/" or decoded_path == "/review.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(rendered_html.encode("utf-8"))
                elif decoded_path.startswith("/images/"):
                    # Serve local image files for preview
                    rel_path = decoded_path[len("/images/"):]
                    img_file = IMAGES_DIR / rel_path
                    if img_file.exists():
                        self.send_response(200)
                        self.send_header("Content-Type", "image/png")
                        self.end_headers()
                        with open(img_file, "rb") as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_response(404)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/api/confirm":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    data = json.loads(body)

                    # Process confirmed assignments
                    syncer_self._apply_confirmed_mappings(data, md_path, month_data)

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

                    # Shutdown server in separate thread
                    print("\n[+] Confirmation received! Markdown updated.")
                    threading.Thread(target=self.server.shutdown).start()

            def log_message(self, format, *args):
                pass  # Quiet logging

        server = HTTPServer(("127.0.0.1", port), ReviewRequestHandler)
        print(f"[*] Review server launched at: http://127.0.0.1:{port}/")
        print("[*] Opening your browser for visual meal-to-photo pairing...")
        webbrowser.open(f"http://127.0.0.1:{port}/")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            print("[*] Review server closed.")

    def _apply_confirmed_mappings(self, data: Dict[str, Any], md_path: Path, month_data: Any):
        """Processes each confirmed image and updates Markdown file."""
        assignments = data.get("assignments", [])
        year = month_data.year
        month_name = calendar.month_name[month_data.month]

        for idx, item in enumerate(assignments, start=1):
            dish_name = item.get("dish_name", "")
            date_str = item.get("date", "")
            url = item.get("url", "")

            if not url:
                continue

            dest_filename = f"{year}, {month_name}, image {idx}.png"

            # Check if url is local or remote
            if url.startswith("/images/"):
                src_path = IMAGES_DIR / url[len("/images/"):]
            elif url.startswith("http://") or url.startswith("https://"):
                # Download remote image temporarily
                temp_dl = BASE_DIR / f"temp_dl_{idx}.png"
                import requests
                r = requests.get(url, stream=True, timeout=20)
                with open(temp_dl, "wb") as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                src_path = temp_dl
            else:
                src_path = Path(url)

            if src_path.exists():
                saved_rel_path = self.processor.process_and_save(src_path, year, month_name, dest_filename)
                self.processor.update_markdown_meal_image(md_path, dish_name, saved_rel_path)
                print(f"  -> Applied: {dish_name} => {saved_rel_path}")

                # Clean temporary downloaded file
                if "temp_dl_" in str(src_path) and src_path.exists():
                    os.remove(src_path)
