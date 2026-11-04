'use strict';
const tables = [...document.querySelectorAll('table')];
const search = document.getElementById('table-search');
const filter = document.getElementById('table-filter');
function applyFilters() {
  const query = (search?.value || '').toLocaleLowerCase().trim();
  const status = filter?.value || '';
  let total = 0;
  for (const table of tables) {
    let visible = 0;
    const rows = [...table.tBodies[0].rows];
    for (const row of rows) {
      const matches = row.textContent.toLocaleLowerCase().includes(query) && row.textContent.toLocaleLowerCase().includes(status);
      row.hidden = !matches;
      if (matches) visible++;
    }
    const section = table.closest('.table-section');
    section.querySelector('.row-count').textContent = `${visible} of ${rows.length} entries`;
    section.querySelector('.empty').hidden = visible !== 0;
    total += visible;
  }
  const live = document.getElementById('search-status');
  if (live) live.textContent = `${total} matching entries`;
}
search?.addEventListener('input', applyFilters);
filter?.addEventListener('change', applyFilters);
function csvCell(value) {
  // Prevent spreadsheet formula execution, even if future source text begins so.
  const safe = /^[\s]*[=+\-@]/.test(value) ? `'${value}` : value;
  return `"${safe.replaceAll('"', '""')}"`;
}
for (const button of document.querySelectorAll('.export')) {
  button.addEventListener('click', () => {
    const table = button.closest('.table-section').querySelector('table');
    const rows = [table.tHead.rows[0], ...[...table.tBodies[0].rows].filter(row => !row.hidden)];
    const csv = rows.map(row => [...row.cells].map(cell => {
      const links = [...cell.querySelectorAll('a[href]')];
      if (cell.querySelector('.missing')) return csvCell('');
      return csvCell(links.length ? links.map(a => a.href).join(' | ') : cell.innerText.trim());
    }).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], {type: 'text/csv;charset=utf-8;'}));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `own9-${table.dataset.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-2026-11-04.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}
