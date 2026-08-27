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

CONFIG_FILE = BASE_DIR / "config.json"

import json

def load_site_config() -> dict:
    default_cfg = {
        "author": {
            "name": "Lord Junn",
            "nickname": "The Food Man",
            "tagline": "With passion For Real, Good Food",
            "discord": "lordjunn",
            "avatar": "images/avatars/mutsumi.png"
        },
        "site": {
            "title": "Dine with Junn",
            "legacy_mmu_url": "https://lordjunn.github.io/Food-MMU/index.html"
        }
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default_cfg, **data}
        except Exception:
            pass
    return default_cfg

# Site Metadata
SITE_TITLE = "Dine with Junn"
SITE_AUTHOR = "Lord Junn"
LEGACY_MMU_ARCHIVE_URL = "https://lordjunn.github.io/Food-MMU/index.html"
