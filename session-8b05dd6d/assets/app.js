// Row filter for tables marked with a search box. No network calls, no dependencies.
(function () {
  function bind(input) {
    var id = input.getAttribute('data-filter');
    var table = document.getElementById(id);
    var counter = document.querySelector('[data-count="' + id + '"]');
    if (!table) return;
    function update() {
      var terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
      var rows = table.tBodies[0].rows;
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {
        var text = rows[i].textContent.toLowerCase();
        var ok = terms.every(function (t) { return text.indexOf(t) !== -1; });
        rows[i].hidden = !ok;
        if (ok) shown++;
      }
      if (counter) counter.textContent = shown + ' of ' + rows.length + ' rows';
    }
    input.addEventListener('input', update);
    update();
  }
  document.querySelectorAll('input[data-filter]').forEach(bind);
})();
