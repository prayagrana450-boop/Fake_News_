(function(){
  function renderHistoryChart(){
    const el = document.getElementById('historyChart');
    if(!el) return;
    const data = window.__historyChartData;
    if(!data || !data.labels || !data.datasets) return;

    const ctx = el.getContext('2d');
    // eslint-disable-next-line no-undef
    new Chart(ctx, {
      type: 'line',
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#e6edf7' } },
          tooltip: { callbacks: { label: function(context){
            const v = context.parsed.y;
            return context.dataset.label + ': ' + v;
          }}}
        },
        scales: {
          x: {
            ticks: { color: '#9aa7bd' },
            grid: { color: 'rgba(255,255,255,0.06)' }
          },
          y: {
            beginAtZero: true,
            ticks: { color: '#9aa7bd' },
            grid: { color: 'rgba(255,255,255,0.06)' }
          }
        }
      }
    });
  }

  function renderPieChart(){
    const el = document.getElementById('pieChart');
    if(!el) return;
    const data = window.__pieChartData;
    if(!data || !data.labels || !data.datasets) return;

    const ctx = el.getContext('2d');
    new Chart(ctx, {
      type: 'pie',
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#e6edf7' } },
          tooltip: { callbacks: { label: function(context){
            const label = context.label || '';
            const v = context.parsed || 0;
            return label + ': ' + v;
          }}}
        }
      }
    });
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){
      renderHistoryChart();
      renderPieChart();
    });
  } else {
    renderHistoryChart();
    renderPieChart();
  }
})();



