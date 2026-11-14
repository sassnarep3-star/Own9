(function(){
  document.querySelectorAll('input.filter').forEach(function(input){
    var table=document.getElementById(input.getAttribute('data-table'));
    if(!table) return;
    input.addEventListener('input', function(){
      var q=input.value.trim().toLowerCase(); var shown=0;
      Array.prototype.forEach.call(table.tBodies[0].rows, function(row){
        var hit=!q || row.textContent.toLowerCase().indexOf(q)>-1; row.hidden=!hit; if(hit) shown++;
      });
      var count=table.parentNode.parentNode.parentNode.querySelector('.row-count span');
      if(count) count.textContent = shown + ' of ' + table.tBodies[0].rows.length + ' rows';
    });
  });
})();
