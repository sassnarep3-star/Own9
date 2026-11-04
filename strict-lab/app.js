/* Progressive enhancement only: content and exports work without JavaScript. */
'use strict';
const search = document.querySelector('#table-search');
if (search) {
  search.addEventListener('input', () => {
    const query = search.value.toLocaleLowerCase().trim();
    document.querySelectorAll('.data-section').forEach(section => {
      const rows = [...section.querySelectorAll('tbody tr')];
      let visible = 0;
      rows.forEach(row => {
        row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
        if (!row.hidden) visible++;
      });
      section.querySelector('.table-count').textContent =
        `${visible} of ${rows.length} entries · Sources describe context, not proof of a strategy’s performance.`;
    });
  });
}
