import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
IMAGES_DIR = BASE_DIR / "images"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DIST_DIR = BASE_DIR / "dist"

# Optional dotenv loading (pure fallback if python-dotenv is not installed)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# Discord Bot Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
REVIEW_SERVER_PORT = int(os.getenv("REVIEW_SERVER_PORT", 8000))

# Image Settings
MEAL_IMAGE_SIZE = (400, 400)
MEAL_IMAGE_FORMAT = "PNG"

# Site Metadata
SITE_TITLE = "Dine with Junn"
SITE_AUTHOR = "Lord Junn"
LEGACY_MMU_ARCHIVE_URL = "https://lordjunn.github.io/Food-MMU/index.html"
