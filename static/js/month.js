document.addEventListener('DOMContentLoaded', function() {
  initCollapsibleDescriptions();
  initMealChart();
  initMonthKeyboardNav();
});

// --- Collapsible Long Descriptions ---
function initCollapsibleDescriptions() {
  const COLLAPSE_THRESHOLD = 195; // px height

  document.querySelectorAll('.meal-description').forEach(desc => {
    if (desc.scrollHeight > COLLAPSE_THRESHOLD) {
      desc.classList.add('is-collapsible');

      const btn = document.createElement('button');
      btn.className = 'description-toggle';
      btn.textContent = 'Read more \u25BC';
      desc.parentElement.appendChild(btn);

      btn.addEventListener('click', () => {
        const expanded = desc.classList.toggle('is-expanded');
        btn.textContent = expanded ? 'Show less \u25B2' : 'Read more \u25BC';
      });
    }
  });
}

// --- Chart.js Meal Cost Chart ---
let chartInstance = null;

function getChartColors(isDark) {
  return {
    textColor: isDark ? '#f1f5f9' : '#1e293b',
    tickColor: isDark ? '#cbd5e1' : '#475569',
    gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
    barBg: isDark ? 'rgba(140, 0, 255, 0.35)' : 'rgba(140, 0, 255, 0.45)',
    barBorder: isDark ? 'rgba(168, 85, 247, 1)' : 'rgba(126, 34, 206, 1)'
  };
}

function initMealChart() {
  const canvas = document.getElementById('mealChart');
  if (!canvas || !window.mealChartData || typeof Chart === 'undefined') return;

  const data = window.mealChartData;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const colors = getChartColors(isDark);

  const datasets = [
    {
      label: 'Total Daily Cost (RM)',
      data: data.dailyCosts,
      backgroundColor: colors.barBg,
      borderColor: colors.barBorder,
      borderWidth: 2,
      borderRadius: 6,
      type: 'bar',
      order: 2
    }
  ];

  // Breakfast line
  if (data.breakfastCosts && data.breakfastCosts.some(c => c > 0)) {
    datasets.push({
      label: 'Breakfast (RM)',
      data: data.breakfastCosts,
      borderColor: '#f43f5e',
      backgroundColor: '#f43f5e',
      tension: 0.3,
      type: 'line',
      order: 1
    });
  }

  // Lunch line
  if (data.lunchCosts && data.lunchCosts.some(c => c > 0)) {
    datasets.push({
      label: 'Lunch (RM)',
      data: data.lunchCosts,
      borderColor: '#f59e0b',
      backgroundColor: '#f59e0b',
      tension: 0.3,
      type: 'line',
      order: 1
    });
  }

  // Dinner line
  if (data.dinnerCosts && data.dinnerCosts.some(c => c > 0)) {
    datasets.push({
      label: 'Dinner (RM)',
      data: data.dinnerCosts,
      borderColor: '#0284c7',
      backgroundColor: '#0284c7',
      tension: 0.3,
      type: 'line',
      order: 1
    });
  }

  const ctx = canvas.getContext('2d');
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        x: {
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.tickColor,
            font: { weight: '600' }
          }
        },
        y: {
          beginAtZero: true,
          grid: { color: colors.gridColor },
          ticks: {
            color: colors.tickColor,
            font: { weight: '600' },
            callback: value => 'RM ' + Number(value).toFixed(2)
          }
        }
      },
      onHover: (event, chartElement) => {
        const target = event.native ? event.native.target : (event.chart ? event.chart.canvas : null);
        if (target) {
          target.style.cursor = chartElement && chartElement.length ? 'pointer' : 'default';
        }
      },
      onClick: (event, elements) => {
        if (elements.length > 0 && data.dateIds) {
          const index = elements[0].index;
          const targetId = data.dateIds[index];
          if (targetId) {
            const el = document.getElementById(targetId);
            if (el) {
              el.scrollIntoView({ behavior: 'smooth', block: 'start' });
              try {
                history.replaceState(null, '', '#' + targetId);
              } catch (err) {}
              el.classList.remove('highlight-glow');
              void el.offsetWidth;
              el.classList.add('highlight-glow');
            }
          }
        }
      },
      plugins: {
        legend: {
          labels: {
            color: colors.textColor,
            boxWidth: 14,
            font: { weight: '600' }
          }
        },
        tooltip: {
          callbacks: {
            title: context => {
              if (!context || !context.length) return '';
              const index = context[0].dataIndex;
              return (data.fullLabels && data.fullLabels[index]) ? data.fullLabels[index] : context[0].label;
            },
            label: context => ` ${context.dataset.label}: RM ${Number(context.raw || 0).toFixed(2)}`
          }
        }
      }
    }
  });

  // Listen to theme changes from the theme button
  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      setTimeout(() => {
        const nextIsDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const nextColors = getChartColors(nextIsDark);

        if (chartInstance) {
          chartInstance.options.scales.x.grid.color = nextColors.gridColor;
          chartInstance.options.scales.x.ticks.color = nextColors.tickColor;
          chartInstance.options.scales.y.grid.color = nextColors.gridColor;
          chartInstance.options.scales.y.ticks.color = nextColors.tickColor;
          chartInstance.options.plugins.legend.labels.color = nextColors.textColor;
          chartInstance.data.datasets[0].backgroundColor = nextColors.barBg;
          chartInstance.data.datasets[0].borderColor = nextColors.barBorder;
          chartInstance.update();
        }
      }, 50);
    });
  }
}

// --- Keyboard Navigation: Left/Right Arrows between Months ---
function initMonthKeyboardNav() {
  window.addEventListener('keydown', (e) => {
    // Ignore if typing inside an input, textarea, or contentEditable element
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable) {
      return;
    }
    if (e.key === 'ArrowLeft') {
      const prevBtn = document.querySelector('.month-nav-header .month-nav-prev a.nav-month-btn');
      if (prevBtn && prevBtn.href) {
        window.location.href = prevBtn.href;
      }
    } else if (e.key === 'ArrowRight') {
      const nextBtn = document.querySelector('.month-nav-header .month-nav-next a.nav-month-btn');
      if (nextBtn && nextBtn.href) {
        window.location.href = nextBtn.href;
      }
    }
  });
}
