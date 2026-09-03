document.addEventListener('DOMContentLoaded', function() {
  const searchBox = document.getElementById('searchBox');
  const sortDropdown = document.getElementById('sortDropdown');
  const viewModeDropdown = document.getElementById('viewModeDropdown');
  const insightsControls = document.getElementById('insightsControls');
  const insightMetricDropdown = document.getElementById('insightMetricDropdown');
  const showInsightButton = document.getElementById('showInsightButton');
  const insightsPanel = document.getElementById('insightsPanel');
  const resultCountText = document.getElementById('resultCount');
  const viewHeading = document.getElementById('viewHeading');
  const resultsList = document.getElementById('resultsList');

  let currentMode = 'food'; // 'food', 'endings', or 'starters'
  let rawDatabase = { meals: [], summaries: [] };
  let allItems = [];
  let isInsightOpen = false;

  const metricLabels = {
    total: 'Total Cash Damage',
    purelyFood: 'Purely Food Expenses',
    breakfast: 'Breakfast Total',
    lunch: 'Lunch Total',
    dinner: 'Dinner Total',
    avgPerDay: 'Average Cost Per Day',
    etcExpenses: 'Etc. Expenses'
  };

  const metricShortLabels = {
    total: 'Total',
    purelyFood: 'Pure Food',
    breakfast: 'Breakfast',
    lunch: 'Lunch',
    dinner: 'Dinner',
    avgPerDay: 'Avg/Day',
    etcExpenses: 'Etc'
  };

  // Load JSON database
  fetch('data/food_database.json')
    .then(r => r.json())
    .then(data => {
      rawDatabase = data;
      setMode(viewModeDropdown ? viewModeDropdown.value : 'food');
    })
    .catch(err => {
      console.error('Failed to load food_database.json:', err);
      resultCountText.textContent = 'Error loading database.';
    });

  function updateSortDropdownLabels() {
    const ascOpt = sortDropdown.querySelector('option[value="price-asc"]');
    const descOpt = sortDropdown.querySelector('option[value="price-desc"]');
    if (!ascOpt || !descOpt) return;

    if (currentMode === 'food') {
      ascOpt.textContent = 'Sort by Price (Lowest)';
      descOpt.textContent = 'Sort by Price (Highest)';
    } else {
      ascOpt.textContent = 'Sort by Metric (Lowest)';
      descOpt.textContent = 'Sort by Metric (Highest)';
    }
  }

  function shouldShowInsightsControls() {
    if (currentMode === 'food') return false;
    const sortVal = String(sortDropdown.value || '');
    return sortVal === 'price-asc' || sortVal === 'price-desc';
  }

  function refreshInsightsControlsVisibility() {
    const show = shouldShowInsightsControls();
    insightsControls.style.display = show ? 'flex' : 'none';

    if (!show && isInsightOpen) {
      isInsightOpen = false;
      insightsPanel.style.display = 'none';
      insightsPanel.innerHTML = '';
      showInsightButton.textContent = 'Show Insights Leaderboard';
    }
  }

  function setMode(mode) {
    currentMode = mode;
    if (viewModeDropdown && viewModeDropdown.value !== mode) {
      viewModeDropdown.value = mode;
    }
    updateSortDropdownLabels();

    if (currentMode === 'starters') {
      allItems = rawDatabase.summaries || [];
      viewHeading.textContent = 'All Month Starters & Predictions';
    } else if (currentMode === 'endings') {
      allItems = rawDatabase.summaries || [];
      viewHeading.textContent = 'All Month Endings & Retrospectives';
    } else {
      allItems = rawDatabase.meals || [];
      viewHeading.textContent = 'All Food Logs';
      isInsightOpen = false;
      insightsPanel.style.display = 'none';
      showInsightButton.textContent = 'Show Insights Leaderboard';
    }

    refreshInsightsControlsVisibility();
    render();
  }

  function debounce(fn, delay) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function parseSearchQuery(rawInput) {
    const keyword = String(rawInput || '').toLowerCase().trim();
    const priceFilters = [];

    if (!keyword) {
      return { terms: [], priceFilters, cleanedKeyword: '' };
    }

    const priceFilterRegex = /(>=|<=|=|>|<)\s*(?:r?m\s*)?(\d+(?:\.\d+)?)/gi;
    let match;
    while ((match = priceFilterRegex.exec(keyword)) !== null) {
      const val = parseFloat(match[2]);
      if (!isNaN(val)) priceFilters.push({ op: match[1], value: val });
    }

    let cleaned = keyword.replace(priceFilterRegex, ' ');
    if (cleaned.includes('free')) {
      priceFilters.push({ op: '=', value: 0 });
      cleaned = cleaned.replace(/\bfree\b/g, ' ');
    }

    const terms = cleaned.split(/\s+/).filter(t => t.length > 0);
    return { terms, priceFilters, cleanedKeyword: cleaned.trim() };
  }

  function evaluatePrice(priceNum, filters) {
    if (!filters.length) return true;
    for (const f of filters) {
      if (f.op === '>' && !(priceNum > f.value)) return false;
      if (f.op === '>=' && !(priceNum >= f.value)) return false;
      if (f.op === '<' && !(priceNum < f.value)) return false;
      if (f.op === '<=' && !(priceNum <= f.value)) return false;
      if (f.op === '=' && !(Math.abs(priceNum - f.value) < 0.01)) return false;
    }
    return true;
  }

  function getMetricValue(item, metricKey) {
    if (!item) return 0;
    if (metricKey === 'total') return parseFloat(item.total_cash_damage || 0);
    if (metricKey === 'purelyFood') return parseFloat(item.purely_food || 0);
    return parseFloat(item[metricKey] || 0);
  }

  function filterItems(items, query) {
    const { terms, priceFilters } = parseSearchQuery(query);
    const isMetricSort = currentMode !== 'food' && (sortDropdown.value === 'price-asc' || sortDropdown.value === 'price-desc');
    const activeMetric = isMetricSort ? insightMetricDropdown.value : 'total';

    return items.filter(item => {
      // 1. Price/Metric check
      let priceVal = 0;
      if (currentMode === 'food') {
        priceVal = typeof item.price_num === 'number' ? item.price_num : (parseFloat(item.price) || 0);
      } else {
        priceVal = getMetricValue(item, activeMetric);
      }

      if (!evaluatePrice(priceVal, priceFilters)) return false;

      // 2. Text terms match
      if (!terms.length) return true;
      const haystack = (
        (item.dish_name || '') + ' ' +
        (item.restaurant || '') + ' ' +
        (item.meal_type || '') + ' ' +
        (item.description || '') + ' ' +
        (item.items ? item.items.join(' ') : '') + ' ' +
        (item.date || '') + ' ' +
        (item.title || '') + ' ' +
        (item.outro_title || '') + ' ' +
        (item.month_slug || '') + ' ' +
        (item.prose || '') + ' ' +
        (item.intro_text || '') + ' ' +
        (item.era || '') + ' ' +
        (item.teaser || '') + ' ' +
        (item.reasons ? item.reasons.join(' ') : '')
      ).toLowerCase();

      return terms.every(t => haystack.includes(t));
    });
  }

  function sortItems(items, sortKey) {
    const copy = [...items];
    const isMetricSort = currentMode !== 'food' && (sortKey === 'price-asc' || sortKey === 'price-desc');
    const activeMetric = isMetricSort ? insightMetricDropdown.value : 'total';

    if (currentMode !== 'food' && isMetricSort) {
      if (sortKey === 'price-asc') {
        return copy.sort((a, b) => {
          const valA = getMetricValue(a, activeMetric);
          const valB = getMetricValue(b, activeMetric);
          if (valA !== valB) return valA - valB;
          return String(a.month_slug || '').localeCompare(String(b.month_slug || ''));
        });
      } else {
        return copy.sort((a, b) => {
          const valA = getMetricValue(a, activeMetric);
          const valB = getMetricValue(b, activeMetric);
          if (valA !== valB) return valB - valA;
          return String(b.month_slug || '').localeCompare(String(a.month_slug || ''));
        });
      }
    }

    switch (sortKey) {
      case 'date-asc':
        return copy.sort((a, b) => String(a.date || a.month_slug).localeCompare(String(b.date || b.month_slug)));
      case 'date-desc':
        return copy.sort((a, b) => String(b.date || b.month_slug).localeCompare(String(a.date || a.month_slug)));
      case 'price-asc':
        return copy.sort((a, b) => (parseFloat(a.price || 0)) - (parseFloat(b.price || 0)));
      case 'price-desc':
        return copy.sort((a, b) => (parseFloat(b.price || 0)) - (parseFloat(a.price || 0)));
      default:
        return copy;
    }
  }

  function render() {
    refreshInsightsControlsVisibility();

    const query = searchBox.value;
    const sortKey = sortDropdown.value;
    const isMetricSort = currentMode !== 'food' && (sortKey === 'price-asc' || sortKey === 'price-desc');
    const activeMetric = isMetricSort ? insightMetricDropdown.value : 'total';

    const filtered = filterItems(allItems, query);
    const sorted = sortItems(filtered, sortKey);

    resultCountText.textContent = `Showing ${sorted.length} of ${allItems.length} ${currentMode === 'food' ? 'meals' : 'months'}`;

    if (!sorted.length) {
      resultsList.innerHTML = '<div class="no-results" style="padding: 2rem; text-align: center; color: var(--text-muted);">No matching entries found. Try another query.</div>';
      if (isInsightOpen) renderInsights([]);
      return;
    }

    if (currentMode === 'food') {
      resultsList.innerHTML = sorted.map(item => `
        <article class="search-item-card">
          ${item.image ? `
            <div class="search-item-media">
              <img src="${item.image}" alt="${item.dish_name}" loading="lazy">
            </div>
          ` : ''}
          <div class="search-item-info">
            <div class="search-item-header">
              <h3 class="search-dish-name">${item.dish_name}</h3>
              <span class="search-price">${item.price_str || 'Free'}</span>
            </div>
            <div class="search-meta-row">
              ${item.restaurant ? `<span class="search-vendor">[${item.restaurant}]</span>` : ''}
              <span>${item.meal_type}</span>
            </div>
            ${item.description ? `<p class="search-desc">${item.description.replace(/\n/g, '<br>')}</p>` : ''}
            <div class="search-date-link">
              Logged on: <a href="${item.month_slug}.html#${item.date}">${item.date} (${item.day_of_week}) &rarr;</a>
            </div>
          </div>
        </article>
      `).join('');
    } else if (currentMode === 'starters') {
      // Month Starters View (Predictions & Openings)
      resultsList.innerHTML = sorted.map(item => {
        const monthLabel = item.title ? item.title.replace('Food Archive - ', '') : item.month_slug;
        const imageSrc = item.starter_image || item.image;
        const eraTag = item.era ? `<span class="badge" style="background: rgba(140, 0, 255, 0.15); color: #c084fc; border: 1px solid rgba(140, 0, 255, 0.3); font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 999px; margin-left: 0.5rem;">${item.era}</span>` : '';
        const reasonsHtml = (item.reasons && item.reasons.length) 
          ? `<div style="font-size: 0.8rem; color: #38bdf8; margin: 0.3rem 0;"><strong>Key Schedule:</strong> ${item.reasons.join(', ')}</div>` 
          : '';

        const labelNomNom = (rawDatabase.labels && rawDatabase.labels.nom_nom_days) || 'Nom Nom Days';
        return `
        <article class="search-item-card summary-item-card">
          ${imageSrc ? `
            <div class="search-item-media">
              <img src="${imageSrc}" alt="${item.title}" loading="lazy">
            </div>
          ` : ''}
          <div class="search-item-info">
            <div class="search-item-header">
              <h3 class="search-dish-name">Opening Thoughts - ${monthLabel} ${eraTag}</h3>
              <span class="search-price">RM ${Number(item.total_cash_damage || 0).toFixed(2)}</span>
            </div>
            <div class="search-meta-row">
              <span><strong>${monthLabel}</strong></span>
              ${item.teaser ? `<span>•</span><span><em>"${item.teaser}"</em></span>` : ''}
              <span>•</span>
              <span>${labelNomNom}: ${item.nom_nom_days || 'N/A'}</span>
            </div>
            ${reasonsHtml}
            ${item.intro_text ? `
              <div class="summary-prose-scrollbox">
                ${item.intro_text.replace(/\n/g, '<br>')}
              </div>
            ` : `
              <div class="summary-prose-scrollbox" style="color: var(--text-muted); font-style: italic;">
                No opening predictions recorded.
              </div>
            `}
            <div class="search-date-link">
              <a href="${item.month_slug}.html">Open Full Month (${item.month_slug}) &rarr;</a>
            </div>
          </div>
        </article>
      `;}).join('');
    } else {
      // Month Endings View (Retrospectives)
      const labelNomNom = (rawDatabase.labels && rawDatabase.labels.nom_nom_days) || 'Nom Nom Days';
      resultsList.innerHTML = sorted.map(item => {
        const displayTitle = item.outro_title || item.title || item.month_slug;
        const monthLabel = item.title ? item.title.replace('Food Archive - ', '') : item.month_slug;
        const isOngoing = !item.has_ending;
        const ongoingBadge = isOngoing 
          ? `<span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 999px; margin-left: 0.5rem;">🌱 Ongoing Month</span>` 
          : '';

        let priceTagHtml = '';
        if (isMetricSort && activeMetric !== 'total') {
          const metricVal = getMetricValue(item, activeMetric);
          const shortLabel = metricShortLabels[activeMetric] || activeMetric;
          priceTagHtml = `<span class="search-price">${shortLabel}: RM ${metricVal.toFixed(2)}</span>`;
        } else {
          priceTagHtml = `<span class="search-price">RM ${Number(item.total_cash_damage || 0).toFixed(2)}</span>`;
        }

        const proseContent = item.prose 
          ? item.prose.replace(/\n/g, '<br>')
          : (item.intro_text 
              ? `<em style="color: #4ade80;">[Month is active — showing Day 1 Opening Thoughts preview]</em><br><br>${item.intro_text.replace(/\n/g, '<br>')}`
              : `<em style="color: var(--text-muted);">No month ending recorded yet.</em>`);

        const imageSrc = item.image || item.starter_image;

        return `
        <article class="search-item-card summary-item-card">
          ${imageSrc ? `
            <div class="search-item-media">
              <img src="${imageSrc}" alt="${displayTitle}" loading="lazy">
            </div>
          ` : ''}
          <div class="search-item-info">
            <div class="search-item-header">
              <h3 class="search-dish-name">${displayTitle} ${ongoingBadge}</h3>
              ${priceTagHtml}
            </div>
            <div class="search-meta-row">
              <span><strong>${monthLabel}</strong></span>
              <span>•</span>
              <span>Pure Food: RM ${Number(item.purely_food || 0).toFixed(2)}</span>
              <span>•</span>
              <span>${labelNomNom}: ${item.nom_nom_days || 'N/A'}</span>
            </div>
            <div class="summary-prose-scrollbox">
              ${proseContent}
            </div>
            <div class="search-date-link">
              <a href="${item.month_slug}.html">Open Full Month (${item.month_slug}) &rarr;</a>
            </div>
          </div>
        </article>
      `;}).join('');
    }

    if (isInsightOpen) {
      renderInsights(sorted);
    }
  }

  function renderInsights(items) {
    const metric = insightMetricDropdown.value;
    const sortKey = sortDropdown.value;
    const isAsc = sortKey === 'price-asc';

    const rows = items.map(it => ({
      slug: it.month_slug,
      title: it.outro_title || it.title || it.month_slug,
      val: getMetricValue(it, metric)
    }));

    if (isAsc) {
      rows.sort((a, b) => a.val - b.val);
    } else {
      rows.sort((a, b) => b.val - a.val);
    }

    const headingOrder = isAsc ? 'Lowest to Highest' : 'Highest to Lowest';

    if (!rows.length) {
      insightsPanel.innerHTML = `
        <div class="insights-title">Insights: ${metricLabels[metric]}</div>
        <p class="insights-subtitle">No data available for this metric.</p>
      `;
      return;
    }

    insightsPanel.innerHTML = `
      <div class="insights-title">📊 Leaderboard: ${metricLabels[metric]}</div>
      <p class="insights-subtitle">Ranked from ${headingOrder} across currently filtered months</p>
      <ul class="insights-list">
        ${rows.map((r, i) => `
          <li class="insights-item">
            <span><strong>#${i + 1}</strong> <a href="${r.slug}.html">${r.title}</a></span>
            <span><strong>RM ${Number(r.val).toFixed(2)}</strong></span>
          </li>
        `).join('')}
      </ul>
    `;
  }

  // Event Listeners
  searchBox.addEventListener('input', debounce(render, 150));

  sortDropdown.addEventListener('change', () => {
    refreshInsightsControlsVisibility();
    render();
  });

  if (viewModeDropdown) {
    viewModeDropdown.addEventListener('change', () => {
      setMode(viewModeDropdown.value);
    });
  }

  insightMetricDropdown.addEventListener('change', render);

  showInsightButton.addEventListener('click', () => {
    isInsightOpen = !isInsightOpen;
    insightsPanel.style.display = isInsightOpen ? 'block' : 'none';
    showInsightButton.textContent = isInsightOpen ? 'Hide Insights Leaderboard' : 'Show Insights Leaderboard';
    if (isInsightOpen) render();
  });
});
