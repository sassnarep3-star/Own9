(function () {
  var q = document.getElementById('q');
  var s = document.getElementById('status');
  var count = document.getElementById('count');
  if (!q || !s) { return; }
  var rows = Array.prototype.slice.call(document.querySelectorAll('table.register tbody tr'));
  function apply() {
    var term = q.value.trim().toLowerCase();
    var status = s.value;
    var shown = 0;
    rows.forEach(function (row) {
      var okText = !term || (row.getAttribute('data-search') || '').indexOf(term) !== -1;
      var okStatus = !status || row.getAttribute('data-status') === status;
      var show = okText && okStatus;
      row.hidden = !show;
      if (show) { shown += 1; }
    });
    if (count) { count.textContent = shown + ' of ' + rows.length + ' rows shown'; }
  }
  q.addEventListener('input', apply);
  s.addEventListener('change', apply);
  apply();
})();
