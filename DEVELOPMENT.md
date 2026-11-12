# Development Guide

## Source and generated files

Monthly Markdown files in [`content/`](content/) are parsed into typed data
objects by [`pipeline/parser.py`](pipeline/parser.py). Analytics are calculated
by [`pipeline/analytics.py`](pipeline/analytics.py), and
[`pipeline/builder.py`](pipeline/builder.py) renders the static site into
`dist/`.

The builder also generates search data and, in CI, the CSV datasets in
`data/`. Generated files should not be edited by hand.

## Build locally

```powershell
python scripts/cli.py validate
python scripts/cli.py build
python scripts/cli.py build --csv
```

`validate` checks Markdown structure, referenced images, and a complete
SiteBuilder smoke test.

## Month visibility

`new-month` creates a calendar skeleton. A month that remains 100% identical to
that generated template is still built as a direct month page and remains
reachable through chronological previous/next navigation, but it is excluded
from the homepage spotlight, archive cards, search JSON, and CSV datasets.

Once a month has custom opening/closing writing, a real meal, or other
month-specific content, it is treated as a real month. This intentionally keeps
quiet but meaningful months visible.

## Image workflow

`sync-images` selects the newest month with an unlinked meal when no slug is
provided. The review UI writes image paths back to the source Markdown.
Images must be committed alongside those paths before CI validation can pass.

Image processing and generated site output use content comparisons to avoid
rewriting identical files.

## CI and deployment

The workflow in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml):

1. Installs dependencies and Ruff.
2. Validates Markdown and referenced assets.
3. Builds the static site and CSV datasets.
4. Commits changed generated CSVs.
5. Uploads and deploys `dist/` to GitHub Pages.

Keep unfinished image references empty (`- Image: ""`) until the corresponding
file is ready to push.

## Making changes

Prefer changes to the source pipeline, templates, or static assets rather than
editing `dist/`. Run the smallest relevant check first, then run
`python scripts/cli.py validate` before considering the change complete.
