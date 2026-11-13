# Dine with Junn

## Why this exists

Dine with Junn is a personal food diary, expense tracker, and life archive.
It records more than what was eaten: prices, portions, places, workdays,
commutes, financial changes, and the reflections that give each month context.

The project exists to make those memories searchable and durable without
turning the diary into a database form. Markdown keeps the source readable,
portable, and easy to edit years later.

## What V2 is

V2 is the Markdown-first continuation of the original Food-MMU archive. The
undergraduate archive covers August 2022 through March 2026; V2 continues
through post-graduate life, work, adulthood, and culinary exploration.

The site is generated from monthly Markdown files. The generated website is a
presentation of the diary, not the source of truth.

## Core ideas

- `content/` is the source of truth for monthly entries.
- `images/` contains photos referenced by the diary.
- Empty image fields are valid while photos are still being collected.
- A month that is exactly the untouched generated template is kept available
  as a page/navigation target, but is not featured in archives or datasets.
- A quiet month with custom writing is still a real month and remains visible.
- `dist/` and CSV datasets are generated outputs; do not edit them manually.
- CI validates content, builds the site, and deploys it to GitHub Pages.

## Project map

| Path | Purpose |
| --- | --- |
| [`content/`](content/) | Monthly Markdown diary files |
| [`images/`](images/) | Committed meal and archive images |
| [`pipeline/`](pipeline/) | Parsing, analytics, image sync, and site building |
| [`scripts/`](scripts/) | Command-line entry points and validation |
| [`templates/`](templates/) | Jinja2 site templates |
| [`static/`](static/) | CSS and JavaScript assets |
| [`config.json`](config.json) | Site metadata and recurring expenses |
| [`EDITING_GUIDE.md`](EDITING_GUIDE.md) | Daily diary and command instructions |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Architecture, CI, and contribution notes |
| [`CHANGELOG.md`](CHANGELOG.md) | Log of notable pipeline, CLI, and format changes |

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/cli.py serve
```

For normal diary editing, read the [Editing Guide](EDITING_GUIDE.md).
For implementation and deployment details, read the
[Development Guide](DEVELOPMENT.md).

## Historical heritage

The four-year undergraduate era is preserved in the legacy
[Food-MMU Archive](https://lordjunn.github.io/Food-MMU/index.html).
