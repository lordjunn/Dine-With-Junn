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

# Pure Python fallback .env parser
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k not in os.environ or not os.environ[k]:
                    os.environ[k] = v

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
        },
        "labels": {
            "nom_nom_days": "Nom nom days"
        }
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                result = {**default_cfg, **data}
                if "labels" in data:
                    result["labels"] = {**default_cfg["labels"], **data["labels"]}
                return result
        except Exception:
            pass
    return default_cfg

# Site Metadata
SITE_TITLE = "Dine with Junn"
SITE_AUTHOR = "Lord Junn"
LEGACY_MMU_ARCHIVE_URL = "https://lordjunn.github.io/Food-MMU/index.html"
