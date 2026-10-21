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

  /* ---- recursos COM-B (só nas leituras geradas com "recursos_comb") ---- */
  function escHtml(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* frases para revelar */
  document.querySelectorAll('.revelar').forEach(function (bloco) {
    var cartoes = Array.prototype.slice.call(bloco.querySelectorAll('details.revela'));
    var btnTodas = bloco.querySelector('.revelar-todas');
    if (!btnTodas) return;
    function rotuloTodas() { btnTodas.textContent = cartoes.every(function (d) { return d.open; }) ? 'Esconder todas' : 'Revelar todas'; }
    btnTodas.addEventListener('click', function () {
      var abrir = !cartoes.every(function (d) { return d.open; });
      cartoes.forEach(function (d) { d.open = abrir; });
      rotuloTodas();
    });
    cartoes.forEach(function (d) { d.addEventListener('toggle', rotuloTodas); });
  });
  var revelas = Array.prototype.slice.call(document.querySelectorAll('details.revela'));
  var revelasAntes = [];
  window.addEventListener('beforeprint', function () {
    revelasAntes = revelas.map(function (d) { return d.open; });
    revelas.forEach(function (d) { d.open = true; });
  });
  window.addEventListener('afterprint', function () {
    revelas.forEach(function (d, i) { d.open = revelasAntes[i]; });
  });

  /* explicação curta ao tocar numa sigla */
  var dadosSiglas = document.getElementById('dados-siglas');
  if (dadosSiglas) {
    var SIG = {};
    try { SIG = JSON.parse(dadosSiglas.textContent); } catch (e) {}
    var pop = document.createElement('div');
    pop.className = 'sigla-pop';
    pop.setAttribute('role', 'dialog');
    pop.hidden = true;
    document.body.appendChild(pop);
    var popDe = null;
    var fecharPop = function () { pop.hidden = true; popDe = null; };
    var abrirPop = function (el) {
      var d = SIG[el.dataset.sigla];
      if (!d) return;
      var cod = /^[A-D]\d$/.test(d.cod) ? d.cod : 'a seção';
      pop.innerHTML =
        '<span class="pop-fam">' + escHtml(d.familia) + '</span>' +
        '<div class="pop-cab"><span class="sigla s-' + escHtml(d.classe) + '">' + escHtml(el.dataset.sigla) + '</span><strong>' + escHtml(d.nome) + '</strong></div>' +
        '<p>' + escHtml(d.pergunta) + '</p>' +
        '<a href="#' + escHtml(d.id) + '">Ler ' + escHtml(cod) + ' →</a>';
      pop.hidden = false;
      var r = el.getBoundingClientRect();
      var largura = pop.offsetWidth;
      var esquerda = Math.min(Math.max(12, r.left + window.scrollX - 12), window.scrollX + document.documentElement.clientWidth - largura - 12);
      var topo = r.bottom + window.scrollY + 8;
      if (r.bottom + pop.offsetHeight + 16 > window.innerHeight && r.top > pop.offsetHeight + 16) topo = r.top + window.scrollY - pop.offsetHeight - 8;
      pop.style.left = esquerda + 'px';
      pop.style.top = topo + 'px';
      popDe = el;
    };
    document.addEventListener('click', function (e) {
      var alvo = e.target.closest ? e.target : e.target.parentElement;
      var s = alvo.closest('abbr.sigla');
      if (s) { e.preventDefault(); if (popDe === s) fecharPop(); else abrirPop(s); return; }
      if (alvo.closest('.sigla-pop a')) { fecharPop(); fecharCartao(); return; }
      if (!alvo.closest('.sigla-pop')) fecharPop();
    });
    document.addEventListener('keydown', function (e) {
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('abbr.sigla')) { e.preventDefault(); abrirPop(e.target); }
      if (e.key === 'Escape') fecharPop();
    });
    // no celular a barra de endereço dispara resize ao rolar: só fecha se a largura mudar
    var larguraAntes = window.innerWidth;
    window.addEventListener('resize', function () { if (window.innerWidth !== larguraAntes) { larguraAntes = window.innerWidth; fecharPop(); } });
    var gavetaCorpo = document.querySelector('.cartao-corpo');
    if (gavetaCorpo) gavetaCorpo.addEventListener('scroll', fecharPop, { passive: true });
  }

  /* cartão de bolso: o resumo "O passo em uma página" numa gaveta lateral */
  var btnCartao = document.getElementById('btn-cartao');
  var gaveta = document.getElementById('cartao');
  var fundo = document.getElementById('cartao-fundo');
  var cartaoAberto = false;
  function fecharCartao() {
    if (!gaveta || !cartaoAberto) return;
    cartaoAberto = false;
    gaveta.classList.remove('aberto');
    fundo.hidden = true;
    btnCartao.setAttribute('aria-expanded', 'false');
    setTimeout(function () { if (!cartaoAberto) gaveta.hidden = true; }, 300);
    btnCartao.focus();
  }
  if (btnCartao && gaveta) {
    var corpoCartao = gaveta.querySelector('.cartao-corpo');
    var abrirCartao = function () {
      if (!corpoCartao.childElementCount) {
        var origem = document.getElementById(corpoCartao.dataset.origem);
        if (origem) {
          var copia = origem.cloneNode(true);
          copia.removeAttribute('id');
          copia.querySelectorAll('[id]').forEach(function (el) { el.removeAttribute('id'); });
          corpoCartao.appendChild(copia);
        }
      }
      cartaoAberto = true;
      gaveta.hidden = false;
      fundo.hidden = false;
      btnCartao.setAttribute('aria-expanded', 'true');
      requestAnimationFrame(function () { gaveta.classList.add('aberto'); });
      gaveta.querySelector('.cartao-fechar').focus();
    };
    btnCartao.addEventListener('click', function () { if (cartaoAberto) fecharCartao(); else abrirCartao(); });
    fundo.addEventListener('click', fecharCartao);
    gaveta.querySelector('.cartao-fechar').addEventListener('click', fecharCartao);
    corpoCartao.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('a[href^="#"]')) fecharCartao();
    });
    document.querySelectorAll('a.link-cartao').forEach(function (a) {
      a.addEventListener('click', function (e) { e.preventDefault(); abrirCartao(); });
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fecharCartao(); });
  }
})();
