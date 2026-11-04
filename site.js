/* Progressive enhancement only: all research remains readable without JS. */
(() => {
  const control = document.querySelector('.filter');
  const input = document.querySelector('#row-search');
  const rows = [...document.querySelectorAll('tbody tr')];
  const count = document.querySelector('#row-count');
  if (!control || !input || !count || !rows.length) return;
  control.hidden = false;
  const update = () => {
    const query = input.value.trim().toLocaleLowerCase();
    let visible = 0;
    rows.forEach(row => {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
      if (!row.hidden) visible++;
    });
    count.textContent = `${visible} of ${rows.length} entries`;
  };
  input.addEventListener('input', update);
  update();
})();
