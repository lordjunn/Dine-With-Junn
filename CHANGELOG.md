# Changelog

Notable changes to the Dine with Junn pipeline, CLI, and content format.
Newest first. Dates are `YYYY-MM-DD`.

## 2026-11-12

### Added
- Auto-scaffolding of `work_claims` template block: `new-month` in `scripts/cli.py` now includes an initial `work_claims` block in generated month frontmatter, matching `etc`.
- Automatic placeholder filtering: work claims entries with empty labels and `0.00` amounts are cleanly excluded during parsing, keeping static `dist/` builds unpolluted without requiring manual commenting.

### Fixed
- Fixed Ruff `F821` undefined `datetime` error in `scripts/cli.py` by promoting `datetime` import to module scope and typing `_purge_empty_days_in_text`.
- Added `EDITING_GUIDE.md`, `DEVELOPMENT.md`, and `CHANGELOG.md` to `sync-hdd` whitelist to ensure repository documentation mirrors cleanly to external git storage.

## 2026-11-06

### Added
- `purge-empty` CLI command: deletes day sections with no logged meals dated
  before today (today and later are kept). Supports a month slug, `--before`,
  and `--dry-run`. Days containing any real text are never removed.
- `build --watch`: keeps running and rebuilds `dist/` whenever files in
  `content/`, `templates/`, `static/`, `images/`, `themes/` or `config.json`
  change. Pair with an editor live-reload server pointed at `dist/`.
- Image shorthand: a bare filename in `archive.image`, `outro.image`, or a
  meal `- Image:` line resolves to `images/<year>/<Month name>/<file>`. Values
  containing `/` or `\` are used as written.

- Mobile homepage: the latest-month card's cover image now fills the whole card
  and fades into the text area instead of ending in a plain white box.

### Fixed
- Mobile homepage: the "Latest Food Diary Entry" card was clipped (teaser and
  buttons cut off) because its desktop `max-height: 320px` still applied to the
  stacked mobile layout.

### Changed
- CI: bumped GitHub Actions in `deploy.yml` to Node 24 versions (checkout v5,
  setup-python v6, configure-pages v6, upload-pages-artifact v5,
  deploy-pages v5).
- `slug` in frontmatter is now optional; blank or missing falls back to
  `YYYY-MM`.
- `content/2026-11.md` uses `image: "Sakiko.png"` for its archive image.
