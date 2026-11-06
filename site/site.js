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

/* usage: replay the example session like a screen recording */
(function () {
  var cc = document.querySelector('.cc');
  if (!cc || !window.requestAnimationFrame) return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var log = cc.querySelector('.cc-log'), status = cc.querySelector('.cc-status');
  var lbl = status.querySelector('.lbl'), sec = status.querySelector('.sec'), star = status.querySelector('.star');
  var typed = cc.querySelector('.typed'), replay = cc.querySelector('.cc-replay'), skip = cc.querySelector('.cc-skip');
  var nodes = Array.prototype.slice.call(log.children);
  var run = 0, spin = null;
  cc.classList.add('js');

  function wait(ms, id) { return new Promise(function (ok, no) { setTimeout(function () { id === run ? ok() : no(); }, ms); }); }
  function scroll() { log.scrollTop = log.scrollHeight; }
  function add(n) { log.appendChild(n); scroll(); return n; }
  function busy(text) {
    var t0 = Date.now(), f = ['·', '✢', '✳', '✶', '✻', '✽'], k = 0;
    lbl.textContent = text; sec.textContent = ''; cc.classList.add('busy');
    clearInterval(spin);
    spin = setInterval(function () {
      star.textContent = f[k++ % f.length];
      var s = Math.floor((Date.now() - t0) / 1000);
      sec.textContent = s ? '(' + s + 's · esc to interrupt)' : '';
    }, 120);
  }
  function idle() { clearInterval(spin); cc.classList.remove('busy'); }
  function stream(el, text, step, ms, id) {
    var parts = text.split(/(\s+)/), i = 0;
    el.textContent = '';
    return new Promise(function (ok, no) {
      (function tick() {
        if (id !== run) return no();
        el.textContent += parts.slice(i, i + step).join(''); i += step; scroll();
        if (i < parts.length) setTimeout(tick, ms); else ok();
      })();
    });
  }
  function typeIn(text, id) {
    typed.textContent = '';
    return new Promise(function (ok, no) {
      var i = 0;
      (function tick() {
        if (id !== run) return no();
        typed.textContent = text.slice(0, ++i);
        if (i < text.length) setTimeout(tick, 18 + Math.random() * 40); else ok();
      })();
    });
  }

  async function play() {
    var id = ++run;
    replay.hidden = true; skip.hidden = false;
    log.innerHTML = ''; typed.textContent = ''; idle();
    try {
      await wait(500, id);
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i].cloneNode(true), c = n.className;
        if (c === 'cc-user') {
          var text = n.lastChild.textContent.replace(/^\s+/, '');
          await typeIn(text, id); await wait(450, id);
          typed.textContent = ''; add(n); await wait(250, id);
        } else if (c === 'cc-think') {
          busy(cc.dataset.thinking); await wait(1800, id); idle();
          add(n);
          var th = nodes[++i].cloneNode(true), tt = th.textContent;
          add(th); await stream(th, tt, 4, 45, id); await wait(300, id);
        } else if (c === 'cc-tool') {
          busy(cc.dataset.running); await wait(500, id);
          var dot = n.querySelector('.dot'); dot.classList.remove('ok'); dot.classList.add('run');
          add(n);
          await wait(/run_wbpp|wbpp_status|fetch/.test(n.textContent) ? 2200 : 900, id);
          idle(); dot.classList.remove('run'); dot.classList.add('ok');
          while (nodes[i + 1] && nodes[i + 1].className.indexOf('cc-out') === 0) { add(nodes[++i].cloneNode(true)); await wait(90, id); }
          await wait(350, id);
        } else if (c === 'cc-say') {
          var p = n.querySelector('p'), st = p.textContent;
          add(n); await stream(p, st, 2, 35, id); await wait(700, id);
        } else if (c === 'cc-note') {
          await wait(400, id); add(n); await wait(1200, id);
        } else { add(n); }
      }
    } catch (e) { return; }
    idle(); replay.hidden = false; skip.hidden = true;
  }
  function showAll() {
    run++; idle(); typed.textContent = '';
    log.innerHTML = '';
    nodes.forEach(function (n) { log.appendChild(n.cloneNode(true)); });
    scroll(); replay.hidden = false; skip.hidden = true;
  }
  replay.addEventListener('click', play);
  skip.addEventListener('click', showAll);
  replay.hidden = false; skip.hidden = true;
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      if (es[0].isIntersecting) { io.disconnect(); play(); }
    }, { threshold: 0.35 });
    io.observe(cc);
  } else play();
})();
