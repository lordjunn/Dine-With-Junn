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
# Automatically detects latest month and generates the next one (e.g. 2026-09.md with all 30 calendar days)
python scripts/cli.py new-month

# Or generate a specific month with a custom era title:
python scripts/cli.py new-month 2026-10 --era "Corporate Slavery: Arc 1"
```

### 5. Build Static Site
```bash
# Build full static site to /dist
python scripts/cli.py build
```

### 5. Sync Discord Photos (Visual Confirmation Workflow)
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

## ☁️ Automated GitHub Actions Deployment
When you push changes to `main`:
1. GitHub Actions automatically triggers if files in `content/`, `images/`, `templates/`, or `static/` are modified.
2. It runs `python scripts/cli.py build` in the cloud.
3. Automatically deploys the static `/dist` site straight to **GitHub Pages**.

> **One-Time GitHub Setup**: In your GitHub repository, go to **Settings → Pages → Build and deployment → Source**, and select **GitHub Actions**.

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
