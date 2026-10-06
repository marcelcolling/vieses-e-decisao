/*
 * Portal Vieses e Decisão — sessão do estudante e salvamento automático.
 *
 * Cada atividade guarda as respostas em dois lugares:
 *   1. no navegador (localStorage), imediatamente, para nada se perder;
 *   2. na planilha Google da turma (via Apps Script), alguns segundos depois.
 * Se a planilha não estiver configurada (config.js), funciona só no navegador.
 *
 * API pública: window.VD
 */
(function () {
  'use strict';

  var CFG = window.VD_CONFIG || {};
  var URL_API = String(CFG.APPS_SCRIPT_URL || '').trim();
  var PLANILHA = URL_API.length > 0;
  var K_SESSAO = 'vd_sessao_v1';
  var K_DADOS = 'vd_dados_v1::';
  var ANON = '__anonimo__';
  var SCRIPT = document.currentScript;
  var RAIZ = SCRIPT ? new URL('../../', SCRIPT.src).href : '';

  /* ---------------- utilidades ---------------- */
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function limparNome(s) { return String(s || '').trim().replace(/\s+/g, ' '); }
  function normalizar(nome) {
    var s = limparNome(nome);
    if (s.normalize) s = s.normalize('NFD').replace(/[̀-ͯ]/g, '');
    return s.toLowerCase();
  }
  function fmtHora(ms) {
    if (!ms) return '';
    var d = new Date(Number(ms)), h = new Date();
    var hh = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
    if (d.toDateString() === h.toDateString()) return 'hoje às ' + hh;
    return String(d.getDate()).padStart(2, '0') + '/' + String(d.getMonth() + 1).padStart(2, '0') + ' às ' + hh;
  }
  function iniciais(nome) {
    var p = limparNome(nome).split(' ').filter(Boolean);
    return ((p[0] || '?').charAt(0) + (p.length > 1 ? p[p.length - 1].charAt(0) : '')).toUpperCase();
  }

  /* ---------------- sessão e dados locais ---------------- */
  var sessao = store.get(K_SESSAO, null);
  if (sessao && sessao.modo === 'planilha' && !PLANILHA) sessao.modo = 'local';

  var ouvSessao = [], ouvStatus = [], antesDeTrocar = [];
  function emitirSessao() {
    atualizarIdentificacaoImpressa();
    ouvSessao.forEach(function (f) { try { f(sessao); } catch (e) { console.error(e); } });
  }
  function notificar(f, estado, info) {
    ouvStatus.forEach(function (fn) { try { fn(f, estado, info); } catch (e) { console.error(e); } });
  }

  function escopo(id) { return K_DADOS + (id || (sessao ? sessao.id : ANON)); }
  function lerTodos() { return store.get(escopo(), {}); }
  function gravarTodos(obj) { store.set(escopo(), obj); }
  function registro(f) { return lerTodos()[f] || null; }
  function gravarRegistro(f, reg) { var t = lerTodos(); t[f] = reg; gravarTodos(t); }
  function emPlanilha() { return PLANILHA && sessao && sessao.modo === 'planilha'; }

  /* ---------------- comunicação com o Apps Script ---------------- */
  function api(payload) {
    var ctrl = window.AbortController ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, 30000);
    return fetch(URL_API, { method: 'POST', body: JSON.stringify(payload), signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .finally(function () { clearTimeout(t); });
  }
  function beacon(payload) {
    try {
      if (navigator.sendBeacon) {
        return navigator.sendBeacon(URL_API, new Blob([JSON.stringify(payload)], { type: 'text/plain;charset=utf-8' }));
      }
    } catch (e) {}
    return false;
  }

  function mesclarRemoto(remoto) {
    var local = lerTodos(), pend = [];
    Object.keys(remoto).forEach(function (f) {
      var r = remoto[f], l = local[f];
      if (l && l.pendente && (l.atualizado || 0) > (r.atualizado || 0)) { pend.push(f); return; }
      local[f] = { data: r.data, titulo: r.titulo, resumo: (l && l.resumo) || [], atualizado: r.atualizado, base: r.atualizado, pendente: false };
    });
    Object.keys(local).forEach(function (f) {
      if (local[f].pendente && !remoto[f] && pend.indexOf(f) < 0) pend.push(f);
    });
    gravarTodos(local);
    return pend;
  }
  function adotarAnonimo(pend) {
    var anon = store.get(escopo(ANON), {});
    if (!Object.keys(anon).length) return;
    var local = lerTodos(), resto = {};
    Object.keys(anon).forEach(function (f) {
      if (!local[f]) {
        local[f] = Object.assign({}, anon[f], { pendente: true, base: null });
        if (pend) pend.push(f);
      } else {
        resto[f] = anon[f];
      }
    });
    gravarTodos(local);
    if (Object.keys(resto).length) store.set(escopo(ANON), resto); else store.del(escopo(ANON));
  }

  function entrar(opts) {
    antesDeTrocar.forEach(function (f) { try { f(); } catch (e) {} });
    var nome = limparNome(opts.nome), chave = String(opts.chave || '').trim(), turma = limparNome(opts.turma);
    if (!nome) return Promise.resolve({ ok: false, erro: 'Informe seu nome ou o nome do grupo.' });
    if (!PLANILHA) {
      sessao = { id: normalizar(nome), nome: nome, turma: turma, chave: '', modo: 'local' };
      store.set(K_SESSAO, sessao);
      adotarAnonimo(null);
      emitirSessao();
      return Promise.resolve({ ok: true });
    }
    if (chave.length < 4) return Promise.resolve({ ok: false, erro: 'A palavra-chave precisa ter pelo menos 4 caracteres.' });
    return api({ acao: 'entrar', nome: nome, chave: chave, turma: turma, criar: !!opts.criar })
      .then(function (res) {
        if (!res || !res.ok) return res || { ok: false, erro: 'Resposta inválida da planilha.' };
        sessao = { id: res.aluno.id, nome: res.aluno.nome, turma: res.aluno.turma || '', chave: chave, modo: 'planilha' };
        store.set(K_SESSAO, sessao);
        var pend = mesclarRemoto(res.dados || {});
        adotarAnonimo(pend);
        emitirSessao();
        pend.forEach(function (f) { enviar(f); });
        return { ok: true, criado: !!res.criado };
      })
      .catch(function () {
        return { ok: false, erro: 'Não foi possível falar com a planilha da turma. Verifique sua conexão e tente de novo.' };
      });
  }

  function sair() {
    antesDeTrocar.forEach(function (f) { try { f(); } catch (e) {} });
    if (emPlanilha()) {
      var t = lerTodos();
      var pend = Object.keys(t).filter(function (f) { return t[f].pendente; });
      if (pend.length && !window.confirm('Há alterações que ainda não chegaram à planilha. Se sair agora, elas ficam só neste navegador. Sair mesmo assim?')) return;
      if (!pend.length) store.del(escopo());
    }
    sessao = null;
    store.del(K_SESSAO);
    emitirSessao();
  }

  /* Busca a versão mais recente na planilha (útil para grupos). */
  function sincronizar() {
    if (!emPlanilha()) return Promise.resolve({ ok: true, local: true });
    var s = sessao;
    return api({ acao: 'entrar', nome: s.nome, chave: s.chave, criar: false })
      .then(function (res) {
        if (!res || !res.ok) {
          if (res && (res.chaveIncorreta || res.naoEncontrado)) {
            toast('Sua palavra-chave não confere mais. Entre novamente.');
            sessao = null; store.del(K_SESSAO); emitirSessao(); abrirLogin();
          }
          return res;
        }
        var pend = mesclarRemoto(res.dados || {});
        pend.forEach(function (f) { enviar(f); });
        ouvSessao.forEach(function (f) { try { f(sessao, 'sincronizado'); } catch (e) {} });
        return res;
      })
      .catch(function () { return { ok: false, offline: true }; });
  }

  var enviando = {};
  function enviar(f, opts) {
    opts = opts || {};
    if (!emPlanilha()) return Promise.resolve({ ok: true, local: true });
    var reg = registro(f);
    if (!reg || (!reg.pendente && !opts.forcar)) return Promise.resolve({ ok: true });
    var payload = {
      acao: 'salvar', nome: sessao.nome, chave: sessao.chave, ferramenta: f,
      titulo: reg.titulo || f, data: reg.data, resumo: reg.resumo || [],
      base: reg.base == null ? null : reg.base, forcar: !!opts.forcar
    };
    if (opts.beacon) { beacon(payload); return Promise.resolve({ ok: true, beacon: true }); }
    if (enviando[f]) { enviando[f].denovo = true; return enviando[f].p; }

    var marca = reg.atualizado, ctl = { denovo: false };
    notificar(f, 'salvando');
    ctl.p = api(payload).then(function (res) {
      if (res && res.ok) {
        var atual = registro(f);
        if (atual) {
          atual.base = res.atualizado;
          if (atual.atualizado === marca) atual.pendente = false;
          gravarRegistro(f, atual);
        }
        notificar(f, atual && atual.pendente ? 'pendente' : 'ok', res.atualizado);
        return res;
      }
      if (res && res.conflito) {
        if (JSON.stringify(res.data) === JSON.stringify(reg.data)) {
          var a2 = registro(f); a2.base = res.atualizado; a2.pendente = false; gravarRegistro(f, a2);
          notificar(f, 'ok', res.atualizado);
          return { ok: true, atualizado: res.atualizado };
        }
        notificar(f, 'conflito', res);
        return res;
      }
      if (res && res.sessaoInvalida) {
        notificar(f, 'erro', res.erro);
        toast(res.erro || 'Entre novamente para continuar salvando na planilha.');
        return res;
      }
      notificar(f, 'erro', (res && res.erro) || 'Erro ao salvar.');
      return res;
    }).catch(function () {
      notificar(f, 'erro', 'Sem conexão com a planilha.');
      return { ok: false, offline: true };
    }).finally(function () {
      var de = ctl.denovo;
      delete enviando[f];
      if (de) enviar(f);
    });
    enviando[f] = ctl;
    return ctl.p;
  }

  /* ---------------- interface: barra, menu, modal, toast ---------------- */
  var toastEl = null, toastT = null;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement('div'); toastEl.className = 'vd-toast'; toastEl.setAttribute('role', 'status'); document.body.appendChild(toastEl); }
    toastEl.textContent = msg;
    toastEl.classList.add('on');
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.classList.remove('on'); }, 3800);
  }

  function atualizarIdentificacaoImpressa() {
    document.querySelectorAll('.vd-print-id').forEach(function (el) {
      var partes = [];
      if (sessao) { partes.push('Nome: ' + sessao.nome); if (sessao.turma) partes.push('Turma: ' + sessao.turma); }
      if (typeof el._extra === 'function') { var x = el._extra(); if (x) partes.push(x); }
      el.textContent = partes.join(' · ');
    });
  }

  var topbar = null;
  function montarTopbar(crumb) {
    if (topbar) return topbar;
    topbar = document.createElement('div');
    topbar.className = 'vd-topbar';
    topbar.innerHTML =
      '<div class="vd-topbar-inner">' +
        '<div class="vd-left">' +
          '<a class="vd-brand" href="' + RAIZ + 'index.html" title="Voltar ao início do portal"><span class="vd-dot"></span><span class="vd-brand-txt">' + esc(CFG.NOME_DISCIPLINA || 'Portal') + '</span></a>' +
          (crumb ? '<span class="vd-crumb">' + esc(crumb) + '</span>' : '') +
        '</div>' +
        '<div class="vd-right">' +
          '<button type="button" class="vd-btn vd-btn-claro vd-ajuda" title="Como usar o portal"><span class="vd-ajuda-ico" aria-hidden="true">?</span><span class="vd-ajuda-txt">Como usar</span></button>' +
          '<span class="vd-status" data-estado="local" hidden><span class="vd-status-txt"></span></span>' +
          '<button type="button" class="vd-btn vd-btn-amarelo vd-salvar" data-vd-salvar hidden>Salvar respostas</button>' +
          '<span class="vd-sessao"></span>' +
        '</div>' +
      '</div>';
    document.body.insertBefore(topbar, document.body.firstChild);
    topbar.querySelector('.vd-ajuda').onclick = function () { abrirInstrucoes(); };
    renderSessaoTopbar();
    onSessao(renderSessaoTopbar);
    document.addEventListener('click', function (e) {
      var menu = topbar.querySelector('.vd-menu');
      if (menu && !menu.hidden && !e.target.closest('.vd-right')) menu.hidden = true;
    });
    return topbar;
  }

  function renderSessaoTopbar() {
    if (!topbar) return;
    var alvo = topbar.querySelector('.vd-sessao');
    if (!sessao) {
      alvo.innerHTML = '<button type="button" class="vd-btn vd-btn-amarelo">Entrar</button>';
      alvo.querySelector('button').onclick = function () { abrirLogin(); };
      return;
    }
    alvo.innerHTML =
      '<button type="button" class="vd-user" aria-haspopup="true"><span class="vd-avatar">' + esc(iniciais(sessao.nome)) + '</span><span class="vd-user-nome">' + esc(sessao.nome) + '</span></button>' +
      '<div class="vd-menu" hidden>' +
        '<div class="vd-menu-info"><strong>' + esc(sessao.nome) + '</strong>' +
          (sessao.turma ? 'Turma: ' + esc(sessao.turma) + '<br>' : '') +
          (emPlanilha() ? 'Respostas salvas na planilha da turma.' : 'Modo local: respostas salvas só neste navegador.') +
        '</div>' +
        (emPlanilha() ? '<button type="button" data-a="sync">↻ Buscar a versão mais recente</button>' : '') +
        '<button type="button" data-a="sair">Sair / trocar de estudante</button>' +
      '</div>';
    var menu = alvo.querySelector('.vd-menu');
    alvo.querySelector('.vd-user').onclick = function () { menu.hidden = !menu.hidden; };
    menu.querySelectorAll('button[data-a]').forEach(function (b) {
      b.onclick = function () {
        menu.hidden = true;
        if (b.dataset.a === 'sair') sair();
        if (b.dataset.a === 'sync') sincronizar().then(function (r) { toast(r && r.ok ? 'Pronto: você está com a versão mais recente.' : 'Não foi possível sincronizar agora.'); });
      };
    });
  }

  function setStatusEl(el, estado, texto) {
    if (!el) return;
    el.hidden = false;
    el.dataset.estado = estado;
    var t = el.querySelector('.vd-status-txt') || el;
    t.textContent = texto;
    el.title = texto;
  }

  /* ----- modal de login ----- */
  var modal = null;
  function garantirModal() {
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'vd-modal';
    modal.hidden = true;
    modal.innerHTML = '<div class="vd-modal-box" role="dialog" aria-modal="true"><button type="button" class="vd-modal-x" aria-label="Fechar">✕</button><div class="vd-modal-corpo"></div></div>';
    document.body.appendChild(modal);
    modal.querySelector('.vd-modal-x').onclick = fecharModal;
    modal.addEventListener('click', function (e) { if (e.target === modal) fecharModal(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !modal.hidden) fecharModal(); });
    return modal;
  }
  function fecharModal() { if (modal) modal.hidden = true; }
  function abrirModal(html, largo) {
    garantirModal();
    modal.querySelector('.vd-modal-box').classList.toggle('vd-largo', !!largo);
    modal.querySelector('.vd-modal-corpo').innerHTML = html;
    modal.hidden = false;
    var primeiro = modal.querySelector('input, .vd-acoes .vd-btn');
    if (primeiro) setTimeout(function () { primeiro.focus({ preventScroll: true }); modal.querySelector('.vd-modal-box').scrollTop = 0; }, 30);
    return modal.querySelector('.vd-modal-corpo');
  }

  function abrirLogin(pre) {
    pre = pre || {};
    var corpo = abrirModal(
      '<div class="vd-modal-eyebrow"><span class="vd-dot"></span>Identificação</div>' +
      '<h3>Entre para salvar suas respostas</h3>' +
      '<p>Use o seu nome (ou o nome do grupo) e uma palavra-chave. Com eles você retoma as atividades de qualquer computador, e o professor acompanha o que foi preenchido.</p>' +
      (PLANILHA ? '' : '<div class="vd-aviso">A planilha da turma ainda não foi conectada. Por enquanto, as respostas ficam salvas apenas neste navegador.</div>') +
      '<form class="vd-form" autocomplete="off">' +
        '<div class="vd-campo"><label for="vd-nome">Nome do estudante ou do grupo</label><input id="vd-nome" name="nome" maxlength="80" required value="' + esc(pre.nome || '') + '" placeholder="Ex.: Ana Souza  ou  Grupo Atlas"></div>' +
        (PLANILHA ? '<div class="vd-campo"><label for="vd-chave">Palavra-chave</label><input id="vd-chave" name="chave" maxlength="60" required placeholder="Mínimo de 4 caracteres"><small>Não use uma senha pessoal. Em grupo, todos usam o mesmo nome e a mesma palavra-chave.</small></div>' : '') +
        '<div class="vd-erro" hidden></div>' +
        '<div class="vd-acoes"><button type="submit" class="vd-btn vd-btn-roxo">Entrar</button></div>' +
      '</form>'
    );
    var form = corpo.querySelector('form'), erro = corpo.querySelector('.vd-erro'), btn = form.querySelector('button[type=submit]');
    form.onsubmit = function (e) {
      e.preventDefault();
      erro.hidden = true;
      var nome = form.nome.value, chave = form.chave ? form.chave.value : '';
      btn.disabled = true; btn.textContent = 'Verificando…';
      entrar({ nome: nome, chave: chave }).then(function (res) {
        btn.disabled = false; btn.textContent = 'Entrar';
        if (res.ok) { fecharModal(); toast('Bem-vindo(a), ' + sessao.nome + '!'); return; }
        if (res.naoEncontrado) { abrirCadastro(nome, chave); return; }
        erro.textContent = res.erro || 'Não foi possível entrar.'; erro.hidden = false;
      });
    };
  }

  function abrirCadastro(nome, chave) {
    var corpo = abrirModal(
      '<div class="vd-modal-eyebrow"><span class="vd-dot"></span>Primeiro acesso</div>' +
      '<h3>Criar seu cadastro?</h3>' +
      '<p>Não encontramos <strong>' + esc(limparNome(nome)) + '</strong> na planilha da turma. Se você já entrou antes, volte e confira se o nome está escrito do mesmo jeito. Se é o primeiro acesso, confirme os dados abaixo.</p>' +
      '<form class="vd-form" autocomplete="off">' +
        '<div class="vd-campo"><label for="vd-turma">Turma</label><input id="vd-turma" name="turma" maxlength="60" placeholder="Ex.: Turma 2026.2"></div>' +
        '<div class="vd-campo"><label for="vd-chave2">Confirme a palavra-chave</label><input id="vd-chave2" name="chave2" maxlength="60" required><small>Anote a palavra-chave: você vai precisar dela para voltar às atividades.</small></div>' +
        '<div class="vd-erro" hidden></div>' +
        '<div class="vd-acoes"><button type="button" class="vd-btn vd-btn-ghost" data-a="voltar">Voltar e corrigir</button><button type="submit" class="vd-btn vd-btn-roxo">Criar cadastro</button></div>' +
      '</form>'
    );
    var form = corpo.querySelector('form'), erro = corpo.querySelector('.vd-erro'), btn = form.querySelector('button[type=submit]');
    form.querySelector('[data-a=voltar]').onclick = function () { abrirLogin({ nome: nome }); };
    form.onsubmit = function (e) {
      e.preventDefault();
      if (form.chave2.value.trim() !== String(chave).trim()) { erro.textContent = 'As palavras-chave não conferem.'; erro.hidden = false; return; }
      btn.disabled = true; btn.textContent = 'Criando…';
      entrar({ nome: nome, chave: chave, turma: form.turma.value, criar: true }).then(function (res) {
        btn.disabled = false; btn.textContent = 'Criar cadastro';
        if (res.ok) { fecharModal(); toast('Cadastro criado. Suas respostas agora vão para a planilha da turma.'); return; }
        erro.textContent = res.erro || 'Não foi possível criar o cadastro.'; erro.hidden = false;
      });
    };
  }

  function abrirConflito(f, info, aoCarregar, aoManter) {
    var corpo = abrirModal(
      '<div class="vd-modal-eyebrow"><span class="vd-dot"></span>Versões diferentes</div>' +
      '<h3>Alguém do grupo salvou antes</h3>' +
      '<p>A planilha tem uma versão desta atividade salva ' + esc(fmtHora(info.atualizado)) + ', depois da última vez que você carregou a página. O que você prefere?</p>' +
      '<div class="vd-acoes" style="flex-direction:column">' +
        '<button type="button" class="vd-btn vd-btn-roxo" data-a="carregar">Carregar a versão da planilha</button>' +
        '<button type="button" class="vd-btn vd-btn-ghost" data-a="manter">Manter a minha e substituir a da planilha</button>' +
      '</div>'
    );
    corpo.querySelector('[data-a=carregar]').onclick = function () { fecharModal(); aoCarregar(); };
    corpo.querySelector('[data-a=manter]').onclick = function () { fecharModal(); aoManter(); };
  }

  /* ----- guia de uso ----- */
  function abrirInstrucoes() {
    var item = function (ico, titulo, txt) {
      return '<li class="vd-guia-item"><span class="vd-guia-ico" aria-hidden="true">' + ico + '</span><div><strong>' + titulo + '</strong><p>' + txt + '</p></div></li>';
    };
    var corpo = abrirModal(
      '<div class="vd-modal-eyebrow"><span class="vd-dot"></span>Guia rápido</div>' +
      '<h3>Como usar o portal</h3>' +
      '<p>Cada aula tem um <strong>material de leitura</strong> e/ou uma <strong>atividade</strong> para preencher. As atividades se encadeiam: o que você faz numa aula alimenta a seguinte.</p>' +
      '<ol class="vd-guia">' +
        item('1', 'Entre com nome e palavra-chave',
          'Clique em <em>Entrar</em> e use o seu nome completo — ou o nome do grupo — e uma palavra-chave de pelo menos 4 caracteres. No primeiro acesso, o portal pede para confirmar o cadastro e a turma. Não use uma senha pessoal.') +
        item('2', 'Leia e preencha',
          'Na trilha, os cartões claros com <strong>📖 Leitura</strong> são materiais para ler; os botões roxos com <strong>✎ Atividade</strong> são as ferramentas para preencher. Os materiais <em>Conheça seus vieses</em> são complementares.') +
        item('3', 'O salvamento é automático',
          'Enquanto você escreve, as respostas são guardadas no navegador e enviadas à planilha da turma em poucos segundos. O indicador no topo mostra o estado: <span class="vd-cor ok">●</span> salvo na planilha, <span class="vd-cor pend">●</span> enviando, <span class="vd-cor erro">●</span> sem conexão (fica no navegador e o portal tenta de novo sozinho). O botão <strong>Salvar respostas</strong> envia na hora, se quiser garantir.') +
        item('4', 'Continue de qualquer computador',
          'Entre com o mesmo nome e a mesma palavra-chave: suas respostas voltam exatamente como estavam.') +
        item('5', 'Em grupo',
          'Todos os membros usam o mesmo nome de grupo e a mesma palavra-chave. Combinem quem digita: se duas pessoas editarem a mesma atividade ao mesmo tempo, o portal avisa e pergunta qual versão manter.') +
        item('6', 'Reaproveite o que já fez',
          'Na Aula 2, o botão <em>Trazer da Aula 1</em> traz o comportamento-alvo escolhido. Na Aula 3, <em>Trazer da Aula 2</em> traz a barreira priorizada. Cada atividade também pode ser impressa ou salva em PDF.') +
        item('?', 'Esqueceu a palavra-chave?', 'Fale com o professor: ele pode redefini-la.') +
      '</ol>' +
      '<div class="vd-acoes"><button type="button" class="vd-btn vd-btn-roxo" data-a="ok">Entendi</button></div>',
      true
    );
    corpo.querySelector('[data-a=ok]').onclick = fecharModal;
  }

  /* ---------------- controlador de atividade ---------------- */
  /*
   * cfg = { id, titulo, coletar(): objeto, aplicar(objeto|null), resumo(objeto): [[seção, campo, resposta]],
   *         crumb, topbar (padrão true), statusEl, infoImpressao(): string }
   */
  var controladores = {};
  function ferramenta(cfg) {
    var ultimo = null, tLocal = null, tRemoto = null, tRetry = null, ultimoEnvio = 0;
    var statusEl = cfg.statusEl || null;

    if (cfg.topbar !== false) {
      montarTopbar(cfg.crumb || cfg.titulo);
      statusEl = topbar.querySelector('.vd-status');
    }
    if (cfg.infoImpressao) document.querySelectorAll('.vd-print-id').forEach(function (el) { el._extra = cfg.infoImpressao; });

    function serial() { try { return JSON.stringify(cfg.coletar()); } catch (e) { console.error(e); return null; } }
    function carregarNaTela() {
      var reg = registro(cfg.id);
      try { cfg.aplicar(reg ? reg.data : null); } catch (e) { console.error(e); }
      ultimo = serial();
      atualizarIdentificacaoImpressa();
      mostrarStatus();
      agendarAlturas();
    }
    function salvarLocal() {
      var s = serial();
      if (s === null || s === ultimo) return false;
      ultimo = s;
      var data = JSON.parse(s), anterior = registro(cfg.id) || {}, resumo = [];
      try { resumo = cfg.resumo ? cfg.resumo(data) : []; } catch (e) { console.error(e); }
      gravarRegistro(cfg.id, { data: data, resumo: resumo, titulo: cfg.titulo, atualizado: Date.now(), base: anterior.base == null ? null : anterior.base, pendente: true });
      return true;
    }
    function agendarRemoto() {
      if (!emPlanilha() || tRemoto) return;
      var espera = Math.max(3000, 9000 - (Date.now() - ultimoEnvio));
      tRemoto = setTimeout(function () { tRemoto = null; ultimoEnvio = Date.now(); enviar(cfg.id); }, espera);
    }
    function alterado() {
      clearTimeout(tLocal);
      tLocal = setTimeout(function () {
        if (salvarLocal()) {
          if (emPlanilha()) { setStatusEl(statusEl, 'pendente', 'Alterações a enviar…'); agendarRemoto(); }
          else mostrarStatus();
        }
      }, 700);
    }
    function descarregar() {
      clearTimeout(tLocal);
      salvarLocal();
      var reg = registro(cfg.id);
      if (emPlanilha() && reg && reg.pendente) enviar(cfg.id, { beacon: true });
    }
    function mostrarStatus(estado, info) {
      var reg = registro(cfg.id);
      if (!sessao) { setStatusEl(statusEl, 'local', reg ? 'Salvo só neste navegador' : 'Entre para salvar na planilha'); return; }
      if (!emPlanilha()) { setStatusEl(statusEl, 'local', 'Salvo neste navegador'); return; }
      if (estado === 'salvando') return setStatusEl(statusEl, 'salvando', 'Salvando na planilha…');
      if (estado === 'erro') return setStatusEl(statusEl, 'erro', 'Sem conexão — salvo neste navegador');
      if (reg && reg.pendente) return setStatusEl(statusEl, 'pendente', 'Alterações a enviar…');
      if (reg && reg.base) return setStatusEl(statusEl, 'ok', 'Salvo na planilha ' + fmtHora(reg.base));
      setStatusEl(statusEl, 'ok', 'Conectado à planilha');
    }

    ['input', 'change', 'click'].forEach(function (ev) { document.addEventListener(ev, alterado, true); });
    window.addEventListener('pagehide', descarregar);
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') descarregar(); });
    antesDeTrocar.push(function () { clearTimeout(tLocal); salvarLocal(); });

    onStatus(function (f, estado, info) {
      if (f !== cfg.id) return;
      if (estado === 'conflito') {
        mostrarStatus('erro');
        abrirConflito(f, info, function () {
          gravarRegistro(f, { data: info.data, resumo: [], titulo: cfg.titulo, atualizado: info.atualizado, base: info.atualizado, pendente: false });
          carregarNaTela();
          toast('Versão da planilha carregada.');
        }, function () { enviar(f, { forcar: true }); });
        return;
      }
      mostrarStatus(estado, info);
      if (estado === 'erro') {
        clearTimeout(tRetry);
        tRetry = setTimeout(function () { enviar(cfg.id); }, 20000);
      }
    });
    onSessao(function (s, motivo) {
      if (motivo === 'sincronizado') {
        var reg = registro(cfg.id);
        if (reg && !reg.pendente && JSON.stringify(reg.data) !== ultimo) { carregarNaTela(); toast('Atualizado com a versão mais recente da planilha.'); }
        mostrarStatus();
        return;
      }
      carregarNaTela();
    });

    carregarNaTela();
    if (emPlanilha()) sincronizar();
    if (!sessao && cfg.pedirLogin !== false) setTimeout(function () { if (!sessao) abrirLogin(); }, 400);

    /* "Salvar respostas": usa o mesmo envio do salvamento automático, só que imediatamente */
    function salvarAgora() {
      clearTimeout(tLocal);
      salvarLocal();
      if (!sessao) { abrirLogin(); return Promise.resolve({ ok: false, semSessao: true }); }
      if (!emPlanilha()) { mostrarStatus(); toast('Respostas salvas neste navegador.'); return Promise.resolve({ ok: true, local: true }); }
      var reg = registro(cfg.id);
      if (!reg) { toast('Ainda não há respostas para salvar.'); return Promise.resolve({ ok: true }); }
      if (!reg.pendente) { reg.pendente = true; gravarRegistro(cfg.id, reg); }
      clearTimeout(tRemoto); tRemoto = null; ultimoEnvio = Date.now();
      return enviar(cfg.id).then(function (res) {
        if (res && res.ok) toast('Respostas salvas na planilha ' + fmtHora(res.atualizado) + '.');
        else if (res && !res.conflito && !res.sessaoInvalida) toast('Não foi possível falar com a planilha agora. As respostas estão guardadas neste navegador e serão enviadas automaticamente.');
        return res;
      });
    }
    function ligarBotaoSalvar(b) {
      if (b._vdLigado) return;
      b._vdLigado = true;
      b.hidden = false;
      var original = b.textContent;
      b.addEventListener('click', function () {
        b.disabled = true;
        b.textContent = 'Salvando…';
        salvarAgora().then(function (res) {
          b.textContent = res && res.ok && !res.semSessao ? '✓ Salvo' : original;
          setTimeout(function () { b.textContent = original; b.disabled = false; }, res && res.ok ? 1800 : 0);
        });
      });
    }
    if (cfg.topbar !== false) document.querySelectorAll('[data-vd-salvar]').forEach(ligarBotaoSalvar);

    var api_ = { alterado: alterado, salvarAgora: salvarAgora, recarregar: carregarNaTela };
    controladores[cfg.id] = api_;
    return api_;
  }

  /* ---------- anotações das "Perguntas para a prática" nos materiais ---------- */
  function notas(cfg) {
    var notasEls = Array.prototype.slice.call(document.querySelectorAll('.reflexao-note'));
    if (!notasEls.length) return;
    var grid = document.querySelector('.reflexao-grid');
    var box = document.createElement('div');
    box.className = 'vd-notas';
    box.innerHTML = '<span class="vd-notas-txt"></span><span class="vd-notas-dir"><span class="vd-status" data-estado="local"><span class="vd-status-txt"></span></span></span>';
    grid.parentNode.insertBefore(box, grid);

    function perguntas() {
      return notasEls.map(function (n) {
        var p = n.parentNode.querySelector('.reflexao-top p');
        return p ? p.textContent.trim() : '';
      });
    }
    function renderBox() {
      var txt = box.querySelector('.vd-notas-txt'), dir = box.querySelector('.vd-notas-dir');
      var btn = dir.querySelector('button');
      if (btn) btn.remove();
      if (emPlanilha()) txt.innerHTML = 'Suas respostas são salvas automaticamente na planilha da turma, como <strong>' + esc(sessao.nome) + '</strong>.';
      else if (sessao) txt.innerHTML = 'Suas respostas são salvas neste navegador, como <strong>' + esc(sessao.nome) + '</strong>.';
      else {
        txt.textContent = PLANILHA ? 'Suas respostas ficam salvas neste navegador.' : 'Suas respostas ficam salvas neste navegador.';
        if (PLANILHA) {
          var b = document.createElement('button');
          b.type = 'button'; b.className = 'vd-btn vd-btn-roxo'; b.textContent = 'Entrar para salvar na planilha';
          b.onclick = function () { abrirLogin(); };
          dir.appendChild(b);
        }
      }
    }
    renderBox();
    onSessao(renderBox);

    return ferramenta({
      id: cfg.id, titulo: cfg.titulo, topbar: false, pedirLogin: false,
      statusEl: box.querySelector('.vd-status'),
      coletar: function () { return { respostas: notasEls.map(function (n) { return n.innerText.replace(/\s+$/, ''); }) }; },
      aplicar: function (d) {
        var r = (d && d.respostas) || [];
        notasEls.forEach(function (n, i) { n.innerText = r[i] || ''; });
      },
      resumo: function (d) {
        var ps = perguntas();
        return ((d && d.respostas) || []).map(function (r, i) { return ['Perguntas para a prática', ps[i] || ('Pergunta ' + (i + 1)), r || '—']; });
      }
    });
  }

  /* ---------- página comum (sem atividade) ---------- */
  function iniciarPagina(opts) {
    opts = opts || {};
    montarTopbar(opts.crumb || '');
    if (emPlanilha()) sincronizar();
  }

  function onSessao(f) { ouvSessao.push(f); }
  function onStatus(f) { ouvStatus.push(f); }

  /* ---------- caixas de texto crescem conforme o conteúdo (a altura mínima vem do CSS) ---------- */
  function autoAltura(ta) {
    if (!ta || ta.tagName !== 'TEXTAREA' || ta.closest('.vd-modal')) return;
    if (ta.offsetParent === null && getComputedStyle(ta).display === 'none') return;
    ta.style.height = 'auto';
    ta.style.height = (ta.scrollHeight + 2) + 'px';
  }
  function autoAlturaTodas() { document.querySelectorAll('textarea').forEach(autoAltura); }
  var tAlt = null;
  function agendarAlturas() { cancelAnimationFrame(tAlt); tAlt = requestAnimationFrame(autoAlturaTodas); }
  document.addEventListener('input', function (e) { autoAltura(e.target); }, true);
  window.addEventListener('resize', agendarAlturas);
  window.addEventListener('afterprint', agendarAlturas);
  if (window.MutationObserver) {
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var n = muts[i].addedNodes;
        for (var j = 0; j < n.length; j++) {
          if (n[j].nodeType === 1 && (n[j].tagName === 'TEXTAREA' || (n[j].querySelector && n[j].querySelector('textarea')))) { agendarAlturas(); return; }
        }
      }
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
  document.addEventListener('DOMContentLoaded', agendarAlturas);
  window.addEventListener('load', agendarAlturas);

  window.VD = {
    planilha: PLANILHA,
    raiz: RAIZ,
    esc: esc,
    fmtHora: fmtHora,
    sessao: function () { return sessao; },
    emPlanilha: emPlanilha,
    registro: registro,
    dados: function (f) { var r = registro(f); return r ? r.data : null; },
    entrar: entrar,
    sair: sair,
    sincronizar: sincronizar,
    abrirLogin: abrirLogin,
    abrirInstrucoes: abrirInstrucoes,
    ferramenta: ferramenta,
    notas: notas,
    iniciarPagina: iniciarPagina,
    onSessao: onSessao,
    onStatus: onStatus,
    toast: toast,
    alterado: function () { Object.keys(controladores).forEach(function (k) { controladores[k].alterado(); }); }
  };
  atualizarIdentificacaoImpressa();
})();
