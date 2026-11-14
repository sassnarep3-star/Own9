// Row filter for the long tables. Dependency-free, keyboard and screen-reader safe:
// it hides rows only, it never removes them from the document.
(function () {
  'use strict';

  function setup(input) {
    var wrap = input.closest('section');
    if (!wrap) { return; }
    var tables = wrap.querySelectorAll('table tbody');
    var bodies = Array.prototype.slice.call(tables);
    var caption = wrap.querySelector('caption');
    var base = caption ? caption.textContent : '';

    input.addEventListener('input', function () {
      var needle = input.value.trim().toLowerCase();
      var shown = 0;
      var total = 0;
      bodies.forEach(function (tbody) {
        Array.prototype.forEach.call(tbody.rows, function (row) {
          total += 1;
          var hit = !needle || row.textContent.toLowerCase().indexOf(needle) !== -1;
          row.classList.toggle('hidden', !hit);
          if (hit) { shown += 1; }
        });
      });
      if (caption) {
        caption.textContent = needle
          ? base + '  —  showing ' + shown + ' of ' + total + ' rows.'
          : base;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    Array.prototype.forEach.call(document.querySelectorAll('input#q'), setup);
  });
})();
