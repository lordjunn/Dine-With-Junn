# 🍽️ Dine with Junn (V2)

A modernized, Markdown-first personal food diary, culinary chronicle, and real-world expense tracker by **Lord Junn** (*"The Food Man"*).

---

## 🚀 Quick Start (on your test machine / HDD)

### 1. Setup Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure your Discord bot token:
```bash
cp .env.example .env
```

### 3. Build Static Site
```bash
# Build full static site to /dist
python scripts/cli.py build
```

### 4. Sync Discord Photos (Visual Confirmation Workflow)
```bash
# Fetch photos for an in-progress month, open visual review UI in browser, confirm, and update Markdown
python scripts/cli.py sync-images 2026-08
```

### 5. Migrate V1 HTML Month to Markdown
```bash
# Migrate a legacy V1 HTML month file to Markdown
python scripts/cli.py migrate "path/to/Jul 26.html"
```

---

## 📁 Directory Structure

```
Dine With Junn/
├── content/               # Source Markdown files (YYYY-MM.md)
│   ├── 2026-07.md        # Finished month
│   └── 2026-08.md        # Active in-progress month
├── images/                # Organized image repository
│   └── 2026/
│       ├── July/
│       └── August/
├── pipeline/              # Python Core Modules
│   ├── __init__.py
│   ├── config.py         # Project paths & configuration
│   ├── schema.py         # Pydantic data schemas
│   ├── parser.py         # Markdown & frontmatter parser
│   ├── analytics.py      # Spending & statistic calculations
│   ├── discord_sync.py   # Discord bot fetch & local review UI
│   ├── image_processor.py# Image resizing & optimization
│   ├── builder.py        # Jinja2 SSG builder
│   └── migrator.py       # V1 HTML to V2 Markdown converter
├── scripts/
│   └── cli.py            # Unified command-line interface
├── static/                # Static assets (CSS, JS, Icons)
│   ├── css/
│   └── js/
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── month.html
│   ├── archives.html
│   ├── all.html
│   └── review.html
├── dist/                  # Generated 100% static output for GitHub Pages
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 📜 Historical Heritage
The 4-year undergraduate era (August 2022 – July 2026) is preserved at the legacy [Food-MMU Archive](https://lordjunn.github.io/Food-MMU/index.html).
V2 continues the journey into post-graduate life, career milestones, and culinary exploration across Klang Valley and beyond.
