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

### 3. Sync to External HDD (Zero File Explorer Drag-and-Drop)
```bash
# Safely mirrors your latest Markdown files & photos to your HDD (protects .git and .venv)
python scripts/cli.py sync-hdd "E:\Dine-With-Junn"
```

### 4. Generate Next Month's Template Automatically
```bash
# Automatically detects latest month and generates the next one (e.g. 2026-10.md with calendar days)
python scripts/cli.py new-month

# Or generate a specific month with a custom era title:
python scripts/cli.py new-month 2026-11 --era "Arc 1"
```

### 5. Sync Discord Photos (Visual Confirmation Workflow)
```bash
# Fetch photos for an in-progress month, open visual review UI in browser, confirm, and update Markdown
python scripts/cli.py sync-images 2026-10
```

### 6. Validate Markdown, Images & Build Integrity
```bash
# Validates frontmatter, verifies that all referenced images exist on disk, and smoke-tests site builder
python scripts/cli.py validate
```

### 7. Build Static Site
```bash
# Build full static site to /dist (CSVs skipped locally by default to prevent merge conflicts)
python scripts/cli.py build

# Force local CSV dataset generation (optional):
python scripts/cli.py build --csv
```

### 8. Local Preview & Serve
```bash
# Starts local web server at http://localhost:8080 and automatically launches browser
python scripts/cli.py serve
```

### 9. Migrate V1 HTML Month to Markdown
```bash
# Migrate a legacy V1 HTML month file to Markdown
python scripts/cli.py migrate "path/to/Jul 26.html"
```

---

## ☁️ Automated GitHub Actions Deployment
When you push changes to `main`:
1. **Lint & Code Quality**: Runs `ruff` across Python core modules.
2. **Integrity Validation**: Runs `scripts/validate.py` to ensure all `.md` files parse cleanly and no image links are missing.
3. **Build & Auto-CSVs**: Builds the static `/dist` site and auto-generates official CSV datasets (`data/menu_*.csv`) in the cloud with `[skip ci]`.
4. **Deploy**: Automatically deploys the static `/dist` site straight to **GitHub Pages**.

> **One-Time GitHub Setup**: In your GitHub repository, go to **Settings → Pages → Build and deployment → Source**, and select **GitHub Actions**.

---

## 📁 Directory Structure

```
Dine With Junn/
├── content/               # Source Markdown files (YYYY-MM.md)
│   ├── 2026-09.md        # Archived month
│   └── 2026-10.md        # Active in-progress month
├── data/                  # Auto-generated CSV datasets (handled via CI)
│   ├── menu_items2.csv
│   ├── menu_endings.csv
│   └── menu_starters.csv
├── images/                # Organized image repository
│   └── 2026/
│       ├── September/
│       └── October/
├── pipeline/              # Python Core Modules
│   ├── __init__.py
│   ├── config.py         # Project paths & configuration
│   ├── schema.py         # Data schemas & display helpers
│   ├── parser.py         # Markdown & frontmatter parser
│   ├── analytics.py      # Spending & statistic calculations
│   ├── discord_sync.py   # Discord bot fetch & local review UI
│   ├── image_processor.py# Image resizing & optimization
│   ├── builder.py        # Jinja2 SSG builder & date autolinker
│   └── migrator.py       # V1 HTML to V2 Markdown converter
├── scripts/
│   ├── cli.py            # Unified command-line interface
│   └── validate.py       # CI asset and content integrity validator
├── static/                # Static assets (CSS, JS, Icons)
│   ├── css/
│   └── js/
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── month.html
│   ├── archives.html
│   ├── all.html
│   ├── 404.html
│   └── review.html
├── dist/                  # Generated 100% static output for GitHub Pages
├── config.json            # Site metadata & navigation labels
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 📜 Historical Heritage
The 4-year undergraduate era (August 2022 – March 2026) is preserved at the legacy [Food-MMU Archive](https://lordjunn.github.io/Food-MMU/index.html).  
V2 continues the journey into post-graduate life, career milestones, and culinary exploration across Klang Valley and beyond.
