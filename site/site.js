(function () {
  var root = document.documentElement;
  var btn = document.querySelector('.theme');
  if (btn) btn.addEventListener('click', function () {
    var next = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.dataset.theme = next;
    try { localStorage.setItem('aa-theme', next); } catch (e) {}
  });
  document.querySelectorAll('.copy').forEach(function (b) {
    var label = b.textContent;
    b.addEventListener('click', function () {
      var text = b.parentNode.querySelector('code').textContent;
      var done = function () { b.textContent = b.dataset.copied; setTimeout(function () { b.textContent = label; }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () {});
    });
  });
})();
