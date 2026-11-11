# 🍽️ Dine with Junn V2 — The Complete Editing Guide

Welcome to your official editing guide for **Dine with Junn V2**! Keep this file handy whenever you want a quick reference for writing meals, pricing, notes, and running commands.

---

## 🚀 Quick-Start Cheatsheet

### 1. Basic Meal Entry
Under any date header, write:

```markdown
### Roti Telur + Teh Tarik [Jasir Bistro]
- Price: RM 4.80
- Meal: Breakfast
- Image: ""

Type your general impressions and thoughts here.
- Item 1: Roti Telur was crispy, 3.00
- Item 2: Teh Tarik was sweet, 1.80

Any closing thoughts or commute stories here.
```

---

## 🏷️ Title & Restaurant Formats (All Supported!)

You can write dish titles in any of these formats — the builder supports all of them:

| Format | Example | How It Renders |
| :--- | :--- | :--- |
| **Standard** | `### Roti Telur [Jasir Bistro]` | **Roti Telur** `[Jasir Bistro]` |
| **Double Brackets** | `### [Roti Telur] [Jasir Bistro]` | **Roti Telur** `[Jasir Bistro]` |
| **No Restaurant** | `### Chicken Rice` | **Chicken Rice** |
| **Question Mark** | `### Bihun Goreng? [Valiram]` | **Bihun Goreng?** `[Valiram]` |

---

## 💰 How to Write Prices & Free Meals

The system automatically calculates your **Total Cash Damage** and **Meal Averages** based on what you write:

| Scenario | What to write | Wallet Damage | Visual Badge |
| :--- | :--- | :--- | :--- |
| **Regular Price** | `- Price: RM 8.50` | `RM 8.50` | `RM 8.50` |
| **Pure Free Meal** | `- Price: Free` | `RM 0.00` | `Free` |
| **Treated / Belanja** | `- Price: ~~RM 6.50~~ Free` | `RM 0.00` | `<s>RM 6.50</s> Free` |
| **Unknown Price** | `- Price: <s>Unknown</s> Free?` | `RM 0.00` | `<s>Unknown</s> Free?` |
| **Free with Note** | `- Price: Free (Belanja)` | `RM 0.00` | `Free (Belanja)` |

---

## 📅 Dates & Skipping Meals

* **Date Header Format**: `## YYYY-MM-DD (DayName)` (e.g. `## 2026-09-02 (Wednesday)`).
* **Skipping Meals / Eating at Home**:
  * You **do not need to delete** empty days or unfilled template slots (`### [Dish Name] [Restaurant]`).
  * The builder **automatically ignores all empty days and unfilled placeholders** when building the website!
  * To tidy the Markdown anyway, run `python scripts/cli.py purge-empty` — it deletes untouched/empty
    day sections dated **before today** (today and later are kept). Add `--dry-run` to preview,
    pass a month like `2026-11` to limit it, or `--before YYYY-MM-DD` to change the cutoff.
    A day with any real text in it is never removed.
* **Multiple Meals in One Day**:
  * Just write another `### Dish 2` block right under the same date!

---

## 📑 Frontmatter & Expenses Reference

At the very top of each month (`content/2026-XX.md`):

```yaml
---
year: 2026
month: 9
slug: "2026-09"          # Optional: blank/missing -> YYYY-MM
title: "Food Archive - September 2026"
nom_nom_days: 0          # Leave as 0 -> Automatically counts active eating days!
reasons:
  - "Sukma Holiday: 1/9"  # Key calendar schedules / milestones
intro_text: |
  Your opening predictions, hopes, and fears for the month...
archive:
  era: "Arc 1"            # Life Chapter name for Archives Hub
  teaser: "3× the pay. Am I 3× better?"
  image: "Yuki.png"      # Bare filename -> images/2026/September/Yuki.png
outro:
  title: "So... What Now?"
  image: "Mutsumi.png"   # A value with a '/' is used as the exact path
  prose: |
    Your month-ending retrospective essay...
expenses:
  rental: 0.00            # Or "Adulting fees: 0.00"
  utilities: 0.00
  petrol: 0.00
  etc: 
    - label: "Parking"
      day: 2
      amount: 4.24
    - label: "LRT Day Pass"
      day: 2
      amount: 7.00        # Comments allowed with # !
---
```

Image shorthand applies to `archive.image`, `outro.image`, and meal `- Image:` lines: a bare
filename is looked up in `images/<year>/<Month name>/` of that month. Anything containing a
`/` (e.g. `images/2026/August/pic.png`) is used exactly as written.

---

### Recurring monthly adulting fees

`new-month` copies the entries in `config.json` → `recurring_monthly_expenses.adulting_fees`
into every newly generated month. Update the label, day, amount, or note there when a
recurring bill changes. Utilities and petrol can be set in the same configuration block.

If a generated month was never filled in, refresh it safely with:

```powershell
python scripts/cli.py new-month 2026-11 --refresh-empty
```

The command only replaces a month that still has no meals, non-zero expenses, or meaningful
notes. It refuses to wipe a month that has been started.

## 📸 Adding Photos from Discord

1. Leave `- Image: ""` empty while logging daily meals.
2. At the end of the week or month, run:
   ```powershell
   python scripts/cli.py sync-images
   ```
   This automatically chooses the newest month with at least one written meal and
   prioritizes months that still have meals without image paths. You can still target
   a specific month with `python scripts/cli.py sync-images 2026-09`.
3. A visual web review tool opens in your browser.
4. Click **Confirm & Apply Images** — it downloads, resizes, and writes the image paths into your Markdown file automatically!

---

## ⚡ Essential Commands Cheatsheet

| Action | Command |
| :--- | :--- |
| **🔨 Build Static Site** | `python scripts/cli.py build` |
| **👀 Auto-Rebuild on Save** | `python scripts/cli.py build --watch` (pair with Live Server on `dist/`) |
| **🌐 Preview in Browser** | `python scripts/cli.py serve` |
| **📸 Sync Discord Photos** | `python scripts/cli.py sync-images 2026-09` |
| **✨ Create Next Month** | `python scripts/cli.py new-month --era "Arc 1"` |
| **🔄 Refresh Empty Month** | `python scripts/cli.py new-month 2026-11 --refresh-empty` |
| **🧹 Purge Empty Days** | `python scripts/cli.py purge-empty --dry-run` |
| **💾 Backup & Sync to HDD**| `python scripts/cli.py sync-hdd "K:\Github\Dine With Junn"` |
