import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

from pipeline.config import (
    BASE_DIR, CONTENT_DIR, IMAGES_DIR, TEMPLATES_DIR,
    STATIC_DIR, DIST_DIR, LEGACY_MMU_ARCHIVE_URL, load_site_config
)
from pipeline.schema import MonthData, MonthAnalytics
from pipeline.parser import MarkdownContentParser
from pipeline.analytics import SpendingAnalyticsEngine

class SiteBuilder:
    """Static site generator compiling Markdown content and Jinja2 templates into /dist."""

    def __init__(self, content_dir: Optional[Path] = None, dist_dir: Optional[Path] = None):
        self.content_dir = Path(content_dir) if content_dir else CONTENT_DIR
        self.dist_dir = Path(dist_dir) if dist_dir else DIST_DIR
        self.parser = MarkdownContentParser(self.content_dir)
        self.analytics_engine = SpendingAnalyticsEngine()

    def build_all(self):
        """Executes the full static site build process."""
        print(f"[*] Starting build process...")
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        site_config = load_site_config()

        # 1. Parse all months
        months_data: List[tuple[MonthData, MonthAnalytics]] = []
        md_files = sorted(self.content_dir.glob("*.md"))

        if not md_files:
            print("[!] No Markdown files found in content/ directory.")
            return

        for md_file in md_files:
            month_obj = self.parser.parse_file(md_file)
            analytics_obj = self.analytics_engine.compute(month_obj)
            months_data.append((month_obj, analytics_obj))

        print(f"[*] Parsed {len(months_data)} monthly log(s).")

        # 2. Setup Jinja2 Environment (or standalone fallback)
        jinja_env = self._get_jinja_env()

        # 3. Generate Database JSON for Search
        self._export_search_database(months_data)

        # 4. Render Index Page
        latest_month_obj, latest_analytics = months_data[-1]
        self._render_page(
            jinja_env,
            "index.html",
            self.dist_dir / "index.html",
            {
                "root_path": "",
                "active_page": "index",
                "site_config": site_config,
                "latest_month": latest_month_obj,
                "latest_analytics": latest_analytics,
                "latest_month_slug": latest_month_obj.slug,
                "latest_month_title": latest_month_obj.title,
                "months": [m[0] for m in reversed(months_data)]
            }
        )

        # 5. Render Archives Hub Page
        all_months_list = [m[0] for m in reversed(months_data)]
        eras_map: Dict[str, List[MonthData]] = {}
        for m in all_months_list:
            era_name = m.archive.era if m.archive.era else "Chronological Logs"
            if era_name not in eras_map:
                eras_map[era_name] = []
            eras_map[era_name].append(m)

        era_groups = list(eras_map.items())

        self._render_page(
            jinja_env,
            "archives.html",
            self.dist_dir / "archives.html",
            {
                "root_path": "",
                "active_page": "archives",
                "site_config": site_config,
                "months": all_months_list,
                "era_groups": era_groups,
                "latest_month_slug": latest_month_obj.slug,
                "latest_month_title": latest_month_obj.title,
            }
        )

        # 6. Render Universal Search Page
        self._render_page(
            jinja_env,
            "all.html",
            self.dist_dir / "all.html",
            {
                "root_path": "",
                "active_page": "all",
                "site_config": site_config,
                "latest_month_slug": latest_month_obj.slug,
                "latest_month_title": latest_month_obj.title,
            }
        )

        # 7. Render Individual Monthly Pages
        for idx, (month_obj, analytics_obj) in enumerate(months_data):
            prev_month = months_data[idx - 1][0] if idx > 0 else None
            next_month = months_data[idx + 1][0] if idx < len(months_data) - 1 else None

            out_file = self.dist_dir / f"{month_obj.slug}.html"
            self._render_page(
                jinja_env,
                "month.html",
                out_file,
                {
                    "root_path": "",
                    "active_page": month_obj.slug,
                    "site_config": site_config,
                    "month": month_obj,
                    "analytics": analytics_obj,
                    "prev_month": prev_month,
                    "next_month": next_month,
                    "latest_month_slug": latest_month_obj.slug,
                    "latest_month_title": latest_month_obj.title,
                }
            )

            # Compatibility alias: dist/Logs/Jul 26.html
            self._generate_legacy_alias(month_obj)

        # 8. Copy Static Assets and Images
        self._copy_assets()

        print(f"[+] Build complete! Generated static site in: {self.dist_dir}")

    def _get_jinja_env(self):
        """Initializes Jinja2 environment if installed."""
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            return Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"])
            )
        except ImportError:
            return None

    def _render_page(self, env: Any, template_name: str, out_path: Path, context: Dict[str, Any]):
        """Renders template via Jinja2 if available, or using standalone renderer."""
        if env:
            template = env.get_template(template_name)
            html_content = template.render(**context)
        else:
            html_content = self._standalone_render(template_name, context)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _standalone_render(self, template_name: str, ctx: Dict[str, Any]) -> str:
        """Standalone template compiler that resolves templates without external packages."""
        base_html = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
        child_html = (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")

        # Extract blocks from child
        blocks = {}
        for block_match in re.finditer(r'{%\s*block\s+([a-zA-Z0-9_]+)\s*%}(.*?){%\s*endblock\s*%}', child_html, re.DOTALL):
            blocks[block_match.group(1)] = block_match.group(2)

        # Substitute blocks in base
        result = base_html
        for block_name, block_content in blocks.items():
            result = re.sub(
                rf'{{\%\s*block\s+{block_name}\s*\%}}.*?{{\%\s*endblock\s*\%}}',
                lambda m, bc=block_content: bc,
                result,
                flags=re.DOTALL
            )

        # Clean any unreplaced blocks in base
        result = re.sub(r'{%\s*block\s+[a-zA-Z0-9_]+\s*%}(.*?){%\s*endblock\s*%}', r'\1', result, flags=re.DOTALL)

        # Handle favicon and site_config
        root_path = ctx.get("root_path", "")
        site_config = ctx.get("site_config", {})
        avatar_path = site_config.get("author", {}).get("avatar", "images/avatars/mutsumi.png") if site_config else "images/avatars/mutsumi.png"
        result = re.sub(
            r'{%\s*if\s+site_config.*?{%\s*endif\s*%}',
            f'<link rel="icon" type="image/png" href="{root_path}{avatar_path}">',
            result,
            flags=re.DOTALL
        )

        # Specific template renders for standalone mode
        if template_name == "index.html":
            result = self._render_standalone_index(result, ctx)
        elif template_name == "archives.html":
            result = self._render_standalone_archives(result, ctx)
        elif template_name == "all.html":
            result = self._render_standalone_all(result, ctx)
        elif template_name == "month.html":
            result = self._render_standalone_month(result, ctx)

        # Global variable replacements
        result = result.replace("{{ root_path }}", root_path)
        result = result.replace("{{ latest_month_slug }}", ctx.get("latest_month_slug", ""))
        result = result.replace("{{ latest_month_title }}", ctx.get("latest_month_title", ""))

        # Handle active page classes cleanly
        active_page = ctx.get("active_page", "")
        latest_slug = ctx.get("latest_month_slug", "")
        result = result.replace("{% if active_page == 'index' %}active{% endif %}", "active" if active_page == "index" else "")
        result = result.replace('{% if active_page == "index" %}active{% endif %}', "active" if active_page == "index" else "")
        result = result.replace("{% if active_page == latest_month_slug %}active{% endif %}", "active" if active_page == latest_slug else "")
        result = result.replace("{% if active_page == 'archives' %}active{% endif %}", "active" if active_page == "archives" else "")
        result = result.replace('{% if active_page == "archives" %}active{% endif %}', "active" if active_page == "archives" else "")
        result = result.replace("{% if active_page == 'all' %}active{% endif %}", "active" if active_page == "all" else "")
        result = result.replace('{% if active_page == "all" %}active{% endif %}', "active" if active_page == "all" else "")

        # Clean unrendered simple tags
        result = re.sub(r'{%\s*if\s+.*?%}', '', result)
        result = re.sub(r'{%\s*endif\s*%}', '', result)
        result = re.sub(r'{%\s*else\s*%}', '', result)

        return result

    def _render_standalone_index(self, html: str, ctx: Dict[str, Any]) -> str:
        root_path = ctx.get("root_path", "")
        site_config = ctx.get("site_config", {})
        avatar_path = site_config.get("author", {}).get("avatar", "images/avatars/mutsumi.png") if site_config else "images/avatars/mutsumi.png"
        html = re.sub(
            r'<img src="\{\{ root_path \}\}\{\{ site_config\.author\.avatar.*?alt="Lord Junn"',
            f'<img src="{root_path}{avatar_path}" alt="Lord Junn"',
            html
        )
        latest = ctx.get("latest_month")
        if latest:
            img_src = latest.archive.image or latest.outro.image
            img_html = f'<img src="{img_src}" alt="{latest.title}">' if img_src else '<div class="spotlight-placeholder">🍽️</div>'
            intro_trunc = (latest.intro_text[:220] + "...") if len(latest.intro_text) > 220 else latest.intro_text
            days_count = latest.nom_nom_days or len(latest.days)
            month_name = latest.title.replace("Food Archive - ", "") if latest.title.startswith("Food Archive - ") else latest.title
            teaser_html = f'<div class="spotlight-teaser">"{latest.archive.teaser}"</div>' if latest.archive.teaser else ''

            spotlight_section = f"""
  <section class="spotlight-section">
    <div class="section-header">
      <h2>✨ Latest Food Diary Entry</h2>
      <a href="{latest.slug}.html" class="view-all-link">Read Full Month &rarr;</a>
    </div>

    <div class="spotlight-card">
      <div class="spotlight-media">
        {img_html}
      </div>
      <div class="spotlight-body">
        <span class="spotlight-tag">Active / Latest Month</span>
        <h3 class="spotlight-title">{month_name}</h3>
        {teaser_html}
        <div class="spotlight-meta">Nom Nom Days: <strong>{days_count} days</strong></div>
        <p class="spotlight-prose">
          {intro_trunc}
        </p>
        <div class="spotlight-actions">
          <a href="{latest.slug}.html" class="btn-primary">Explore {latest.slug} Entries</a>
          <a href="all.html" class="btn-secondary">Search All Meals</a>
        </div>
      </div>
    </div>
  </section>"""
            html = re.sub(
                r'<!-- Latest Entry Spotlight -->.*?<!-- Life Chapters & Eras -->',
                f'<!-- Latest Entry Spotlight -->\n{spotlight_section}\n\n  <!-- Life Chapters & Eras -->',
                html,
                flags=re.DOTALL
            )
        return html

    def _render_standalone_archives(self, html: str, ctx: Dict[str, Any]) -> str:
        months = ctx.get("months", [])
        eras_map: Dict[str, List[MonthData]] = {}
        for m in months:
            era_name = m.archive.era if m.archive.era else "Chronological Logs"
            if era_name not in eras_map:
                eras_map[era_name] = []
            eras_map[era_name].append(m)

        sections_html = []
        for era_name, era_months in eras_map.items():
            cards_html = []
            for m in era_months:
                img_html = f'<img src="{m.archive.image or m.outro.image}" alt="{m.title}" class="archive-img">' if (m.archive.image or m.outro.image) else '<div class="archive-placeholder">🍽️</div>'
                teaser_text = f'"{m.archive.teaser}"' if m.archive.teaser else (m.intro_text[:80] + "...")
                month_label = m.title.replace("Food Archive - ", "") if m.title.startswith("Food Archive - ") else m.title
                cards_html.append(f"""
              <div class="archive-card">
                <a href="{m.slug}.html" class="archive-card-link">
                  <div class="archive-image-wrapper">{img_html}</div>
                  <div class="archive-card-body">
                    <h3 class="archive-month-title">{month_label}</h3>
                    <p class="archive-teaser">{teaser_text}</p>
                  </div>
                </a>
              </div>""")

            tag_text = f"{len(era_months)} Month" if len(era_months) == 1 else f"{len(era_months)} Months"
            sections_html.append(f"""
    <section class="era-section">
      <div class="era-header">
        <h2>{era_name}</h2>
        <span class="era-tag">{tag_text}</span>
      </div>
      <div class="archives-grid">
        {"".join(cards_html)}
      </div>
    </section>""")

        all_eras_html = "\n\n".join(sections_html)
        html = re.sub(
            r'<!-- Dynamic Era Sections -->.*?<!-- MMU Heritage Archive Section -->',
            f'<!-- Dynamic Era Sections -->\n{all_eras_html}\n\n  <!-- MMU Heritage Archive Section -->',
            html,
            flags=re.DOTALL
        )
        return html

    def _render_standalone_all(self, html: str, ctx: Dict[str, Any]) -> str:
        return html

    def _render_standalone_month(self, html: str, ctx: Dict[str, Any]) -> str:
        month = ctx["month"]
        analytics = ctx["analytics"]
        prev_m = ctx.get("prev_month")
        next_m = ctx.get("next_month")

        # Month Title & Meta
        html = html.replace("{{ month.title }}", month.title)
        days_stat = str(month.nom_nom_days or len(month.days))
        html = html.replace("{{ month.nom_nom_days }}", days_stat)
        if month.intro_text:
            html = html.replace("{{ month.intro_text | replace('\\n', '<br>') | safe }}", month.intro_text.replace("\n", "<br>"))

        # Prev / Next
        prev_link = f'<a href="{prev_m.slug}.html" class="nav-month-btn">&larr; {prev_m.title}</a>' if prev_m else ''
        next_link = f'<a href="{next_m.slug}.html" class="nav-month-btn">{next_m.title} &rarr;</a>' if next_m else ''
        html = re.sub(r'{%\s*if\s+prev_month\s*%}.*?{%\s*endif\s*%}', prev_link, html, flags=re.DOTALL)
        html = re.sub(r'{%\s*if\s+next_month\s*%}.*?{%\s*endif\s*%}', next_link, html, flags=re.DOTALL)

        # Reasons
        reasons_lis = "\n".join([f"<li>{r}</li>" for r in month.reasons])
        html = re.sub(r'{%\s*for\s+reason\s+in\s+month\.reasons\s*%}.*?{%\s*endfor\s*%}', reasons_lis, html, flags=re.DOTALL)

        # 1. Generate Daily Stream Section
        days_html = []
        for day in month.days:
            meals_html = []
            for meal in day.meals:
                media_html = f'<div class="meal-media"><img class="meal-image" src="{meal.image}" alt="{meal.dish_name}" loading="lazy"></div>' if meal.image else ''
                vendor_html = f'<span class="vendor-tag">[{meal.restaurant}]</span>' if meal.restaurant else ''
                bullets_html = ""
                if meal.items:
                    bullets_html = '<ul class="itemized-bullets">' + "".join([f"<li>{b}</li>" for b in meal.items]) + '</ul>'
                desc_html = f'<p>{meal.description.replace(chr(10), "<br>")}</p>' if meal.description else ''

                meals_html.append(f"""
                  <article class="meal-card">
                    {media_html}
                    <div class="meal-details">
                      <div class="meal-header-row">
                        <h3 class="meal-title"><span class="dish-name">{meal.dish_name}</span>{vendor_html}</h3>
                        <span class="meal-price">{meal.price_str or 'Free'}</span>
                      </div>
                      <div class="meal-type-badge">{meal.meal_type}</div>
                      <div class="meal-description-wrapper">
                        <div class="meal-description">
                          {desc_html}
                          {bullets_html}
                        </div>
                      </div>
                    </div>
                  </article>""")

            days_html.append(f"""
              <div class="day-group">
                <h2 class="day-heading">{day.date_str} ({day.day_of_week})</h2>
                <div class="meals-list">
                  {"".join(meals_html)}
                </div>
              </div>""")

        daily_stream_block = f"""
  <section class="daily-stream">
    {"".join(days_html)}
  </section>"""

        # Replace Daily Stream Block
        html = re.sub(
            r'<!-- Daily Meal Stream -->.*?<!-- Outro Retrospective & Spending Summary -->',
            f'<!-- Daily Meal Stream -->\n{daily_stream_block}\n\n  <!-- Outro Retrospective & Spending Summary -->',
            html,
            flags=re.DOTALL
        )

        # 2. Generate Outro Retrospective & Spending Summary Section (2-Row Clean Layout)
        media_html = f'<div class="outro-media"><img src="{month.outro.image}" alt="{month.outro.title}" class="outro-image"></div>' if month.outro.image else ''
        prose_html = f'<div class="description-scrollbox">{month.outro.prose.replace(chr(10), "<br>")}</div>' if month.outro.prose else ''
        outro_heading = month.outro.title if month.outro.title else "Month-Ending Retrospective"

        etc_items_html = ""
        if month.expenses.etc:
            etc_lis = "".join([f"<li>{'(' + str(it.day) + ') ' if it.day else ''}{it.label} - RM {it.amount:.2f}</li>" for it in month.expenses.etc])
            etc_items_html = f"""
            <li class="stat-etc">
              <strong>Etc. Expenses:</strong> RM {analytics.etc_expenses_total:.2f}
              <ul class="etc-nested-list">
                {etc_lis}
              </ul>
            </li>"""

        rent_html = f"<li><strong>Rental:</strong> RM {month.expenses.rental:.2f}</li>" if month.expenses.rental > 0 else ""
        util_html = f"<li><strong>Utilities:</strong> RM {month.expenses.utilities:.2f}</li>" if month.expenses.utilities > 0 else ""
        petrol_html = f"<li><strong>Petrol:</strong> RM {month.expenses.petrol:.2f}</li>" if month.expenses.petrol > 0 else ""

        outro_block = f"""
  <section class="outro-section">
    <div class="outro-top-row">
      {media_html}
      <div class="outro-prose-col">
        <h2 class="outro-title">{outro_heading}</h2>
        {prose_html}
      </div>
    </div>

    <!-- Full-Width Bottom Row: Spending Breakdown -->
    <div class="spending-summary-box">
      <div class="spending-header-row">
        <h3>📊 Complete Spending Breakdown</h3>
        <div class="cash-damage-badge">
          <span class="damage-label">Total Cash Damage</span>
          <span class="damage-amount">RM {analytics.total_cash_damage:.2f}</span>
        </div>
      </div>
      <ul class="spending-list">
        <li class="stat-pure-food">
          <strong>Purely food expenses:</strong> RM {analytics.purely_food_expenses:.2f}
        </li>
        <li>
          <strong>Breakfast:</strong> RM {analytics.breakfast_total:.2f}
          <span class="avg-note">(~RM {analytics.breakfast_average:.2f} per meal)</span>
        </li>
        <li>
          <strong>Lunch:</strong> RM {analytics.lunch_total:.2f}
          <span class="avg-note">(~RM {analytics.lunch_average:.2f} per meal)</span>
        </li>
        <li>
          <strong>Dinner:</strong> RM {analytics.dinner_total:.2f}
          <span class="avg-note">(~RM {analytics.dinner_average:.2f} per meal)</span>
        </li>
        <li class="stat-avg-day">
          <strong>Average cost per day:</strong> RM {analytics.average_cost_per_day:.2f}
        </li>
        {etc_items_html}
        {rent_html}
        {util_html}
        {petrol_html}
      </ul>
    </div>
  </section>"""

        # Replace Outro Section Block
        html = re.sub(
            r'<!-- Outro Retrospective & Spending Summary -->.*?<!-- Chart.js Visualization Canvas -->',
            f'<!-- Outro Retrospective & Spending Summary -->\n{outro_block}\n\n  <!-- Chart.js Visualization Canvas -->',
            html,
            flags=re.DOTALL
        )

        # 3. Replace Chart JSON dataset template tags directly
        html = html.replace("{{ analytics.chart_labels | tojson }}", json.dumps(analytics.chart_labels))
        html = html.replace("{{ analytics.chart_daily_costs | tojson }}", json.dumps(analytics.chart_daily_costs))
        html = html.replace("{{ analytics.chart_breakfast_costs | tojson }}", json.dumps(analytics.chart_breakfast_costs))
        html = html.replace("{{ analytics.chart_lunch_costs | tojson }}", json.dumps(analytics.chart_lunch_costs))
        html = html.replace("{{ analytics.chart_dinner_costs | tojson }}", json.dumps(analytics.chart_dinner_costs))

        return html

    def _export_search_database(self, months_data: List[tuple[MonthData, MonthAnalytics]]):
        """Generates dist/data/food_database.json for instant search and metrics insights."""
        meals_records = []
        summaries_records = []

        for month_obj, analytics_obj in months_data:
            summaries_records.append({
                "month_slug": month_obj.slug,
                "title": month_obj.title,
                "outro_title": month_obj.outro.title if month_obj.outro.title else month_obj.title,
                "purely_food": analytics_obj.purely_food_expenses,
                "total_cash_damage": analytics_obj.total_cash_damage,
                "breakfast": analytics_obj.breakfast_total,
                "lunch": analytics_obj.lunch_total,
                "dinner": analytics_obj.dinner_total,
                "avgPerDay": analytics_obj.average_cost_per_day,
                "etcExpenses": analytics_obj.etc_expenses_total,
                "nom_nom_days": month_obj.nom_nom_days,
                "prose": month_obj.outro.prose,
                "image": month_obj.outro.image or month_obj.archive.image,
                "date": f"{month_obj.year}-{month_obj.month:02d}-28"
            })

            for day in month_obj.days:
                for meal in day.meals:
                    meals_records.append({
                        "dish_name": meal.dish_name,
                        "restaurant": meal.restaurant,
                        "price": meal.price,
                        "price_str": meal.price_str,
                        "meal_type": meal.meal_type,
                        "image": meal.image,
                        "date": day.date_str,
                        "day_of_week": day.day_of_week,
                        "month_slug": month_obj.slug,
                        "description": meal.description,
                        "items": meal.items
                    })

        data_dir = self.dist_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "food_database.json"

        with open(db_path, "w", encoding="utf-8") as f:
            json.dump({"meals": meals_records, "summaries": summaries_records}, f, indent=2)

        print(f"[*] Exported {len(meals_records)} meals and {len(summaries_records)} summaries to {db_path.name}")

    def _generate_legacy_alias(self, month_obj: MonthData):
        """Generates compatibility alias files for legacy links like dist/Logs/Jul 26.html."""
        month_map = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }
        short_m = month_map.get(month_obj.month, "Jul")
        yy = str(month_obj.year)[-2:]
        legacy_filename = f"{short_m} {yy}.html"

        logs_dir = self.dist_dir / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        alias_file = logs_dir / legacy_filename

        alias_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url=../{month_obj.slug}.html">
  <title>Redirecting to {month_obj.title}...</title>
</head>
<body>
  <p>Redirecting to <a href="../{month_obj.slug}.html">{month_obj.title}</a>...</p>
</body>
</html>"""
        with open(alias_file, "w", encoding="utf-8") as f:
            f.write(alias_html)

    def _copy_assets(self):
        """Copies static assets (CSS, JS) and images into dist."""
        dest_static = self.dist_dir / "static"
        if STATIC_DIR.exists():
            shutil.copytree(STATIC_DIR, dest_static, dirs_exist_ok=True)

        dest_images = self.dist_dir / "images"
        if IMAGES_DIR.exists():
            shutil.copytree(IMAGES_DIR, dest_images, dirs_exist_ok=True)
