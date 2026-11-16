/* Client-side filter for the decision-readiness table.
   Dependency-free, progressive enhancement: without JavaScript every row is shown
   and the table is complete. */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') { fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  ready(function () {
    var table = document.querySelector('table.filterable');
    var search = document.getElementById('q');
    var status = document.getElementById('status');
    var reset = document.getElementById('reset');
    var count = document.getElementById('count');
    if (!table || !search || !status || !reset || !count) { return; }

    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    var total = rows.length;

    function rowText(row) {
      return (row.textContent || '').toLowerCase();
    }

    function rowStatus(row) {
      var pill = row.querySelector('.pill');
      if (!pill) { return ''; }
      var cls = pill.className || '';
      var m = cls.match(/pill-([a-z-]+)/);
      return m ? m[1] : '';
    }

    function apply() {
      var q = (search.value || '').trim().toLowerCase();
      var s = status.value || '';
      var shown = 0;
      rows.forEach(function (row) {
        var ok = true;
        if (q && rowText(row).indexOf(q) === -1) { ok = false; }
        if (ok && s && rowStatus(row) !== s) { ok = false; }
        row.hidden = !ok;
        if (ok) { shown += 1; }
      });
      count.textContent = shown + ' of ' + total + ' rows shown';
    }

    search.addEventListener('input', apply);
    status.addEventListener('change', apply);
    reset.addEventListener('click', function () {
      search.value = '';
      status.value = '';
      apply();
    });
    apply();
  });
}());
