/* Comportamentos das páginas de leitura: progresso, sumário, exemplos e lista de verificação. */
(function () {
  'use strict';
  var chave = 'vd_leitura_' + (document.body.dataset.chave || location.pathname);
  var ls = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  /* ---- progresso, sumário ativo e voltar ao topo ---- */
  var barra = document.getElementById('progress-bar');
  var topo = document.getElementById('back-to-top');
  var links = Array.prototype.slice.call(document.querySelectorAll('#sidebar a[href^="#"]'));
  var alvos = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
  var agendado = false;
  function aoRolar() {
    agendado = false;
    var total = document.documentElement.scrollHeight - window.innerHeight;
    barra.style.width = (total > 0 ? (window.scrollY / total) * 100 : 0) + '%';
    topo.style.display = window.scrollY > 600 ? 'flex' : 'none';
    var atual = -1;
    for (var i = 0; i < alvos.length; i++) {
      if (alvos[i] && alvos[i].getBoundingClientRect().top <= 140) atual = i;
    }
    links.forEach(function (a, i) { a.classList.toggle('active', i === atual); });
  }
  window.addEventListener('scroll', function () { if (!agendado) { agendado = true; requestAnimationFrame(aoRolar); } }, { passive: true });
  aoRolar();
  topo.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });

  /* ---- sumário no celular ---- */
  var toggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('overlay');
  function fechar() { sidebar.classList.remove('open'); toggle.classList.remove('active'); overlay.style.display = 'none'; }
  toggle.addEventListener('click', function () {
    var aberto = sidebar.classList.toggle('open');
    toggle.classList.toggle('active', aberto);
    overlay.style.display = aberto ? 'block' : 'none';
  });
  overlay.addEventListener('click', fechar);
  sidebar.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', fechar); });

  /* ---- exemplos recolhíveis ---- */
  var exemplos = Array.prototype.slice.call(document.querySelectorAll('details.exemplo'));
  if (exemplos.length) {
    var barraEx = document.createElement('div');
    barraEx.className = 'exemplos-acoes';
    barraEx.innerHTML = '<button type="button">Abrir todos os exemplos</button>';
    exemplos[0].parentNode.insertBefore(barraEx, exemplos[0]);
    var btn = barraEx.querySelector('button');
    function rotulo() { btn.textContent = exemplos.every(function (d) { return d.open; }) ? 'Fechar todos os exemplos' : 'Abrir todos os exemplos'; }
    btn.addEventListener('click', function () {
      var abrir = !exemplos.every(function (d) { return d.open; });
      exemplos.forEach(function (d) { d.open = abrir; });
      rotulo();
    });
    exemplos.forEach(function (d) { d.addEventListener('toggle', rotulo); });
  }
  function abrirAlvo() {
    if (!location.hash) return;
    var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (el && el.tagName === 'DETAILS') el.open = true;
  }
  window.addEventListener('hashchange', abrirAlvo);
  abrirAlvo();
  links.forEach(function (a) {
    a.addEventListener('click', function () {
      var el = document.getElementById(a.getAttribute('href').slice(1));
      if (el && el.tagName === 'DETAILS') el.open = true;
    });
  });
  var abertosAntesDeImprimir = [];
  window.addEventListener('beforeprint', function () {
    abertosAntesDeImprimir = exemplos.map(function (d) { return d.open; });
    exemplos.forEach(function (d) { d.open = true; });
  });
  window.addEventListener('afterprint', function () {
    exemplos.forEach(function (d, i) { d.open = abertosAntesDeImprimir[i]; });
  });

  /* ---- lista de verificação (fica salva neste navegador) ---- */
  var caixas = Array.prototype.slice.call(document.querySelectorAll('ul.checklist input[type=checkbox]'));
  if (caixas.length) {
    var salvo = ls.get(chave + '_checklist', {});
    var lista = caixas[0].closest('ul.checklist');
    var prog = document.createElement('p');
    prog.className = 'checklist-progresso';
    lista.parentNode.insertBefore(prog, lista.nextSibling);
    function atualizar() {
      var n = caixas.filter(function (c) { return c.checked; }).length;
      prog.textContent = n === caixas.length
        ? '✓ Tudo marcado — você está pronto para o Passo 2.'
        : n + ' de ' + caixas.length + ' itens marcados (fica salvo neste navegador).';
    }
    caixas.forEach(function (c) {
      c.checked = !!salvo[c.dataset.chk];
      c.addEventListener('change', function () {
        salvo[c.dataset.chk] = c.checked;
        ls.set(chave + '_checklist', salvo);
        atualizar();
      });
    });
    atualizar();
  }
})();
