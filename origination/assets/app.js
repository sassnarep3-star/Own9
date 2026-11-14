// Dependency-free table filtering. No network calls, no tracking.
(function () {
  'use strict';
  var STORE = {};
  function debounce(fn, wait) {
    var t;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, wait);
    };
  }
  function filter(input) {
    var id = input.getAttribute('data-filter');
    var body = document.getElementById(id);
    if (!body) return;
    var needle = (input.value || '').trim().toLowerCase();
    var rows = body.querySelectorAll('tr');
    var shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var show = !needle || rows[i].textContent.toLowerCase().indexOf(needle) !== -1;
      rows[i].hidden = !show;
      if (show) shown++;
    }
    var out = document.querySelector('[data-count="' + id + '"]');
    if (!out) {
      out = document.createElement('span');
      out.className = 'hint';
      out.setAttribute('data-count', id);
      input.parentNode.appendChild(out);
    }
    var total = rows.length;
    out.textContent = (needle ? '  ' + shown + ' of ' + total + ' rows match' : '  ' + total + ' rows');
    out.style.marginLeft = '8px';
  }
  document.addEventListener('input', debounce(function (event) {
    if (event.target && event.target.getAttribute && event.target.getAttribute('data-filter')) {
      filter(event.target);
    }
  }, 120));
  document.addEventListener('reset', function (event) {
    var form = event.target;
    var inputs = form.querySelectorAll('[data-filter]');
    for (var i = 0; i < inputs.length; i++) { inputs[i].value = ''; filter(inputs[i]); }
  });
  window.OWN9 = STORE;
})();
