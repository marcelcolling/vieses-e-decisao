/**
 * Portal Vieses e Decisão — back-end na planilha Google (Apps Script).
 *
 * Como instalar (detalhes no README.md do repositório):
 *  1. Crie uma planilha Google vazia.
 *  2. Extensões > Apps Script. Apague o conteúdo e cole este arquivo inteiro.
 *  3. Selecione a função "configurar" e clique em Executar (autorize o acesso).
 *  4. Implantar > Nova implantação > tipo "App da Web":
 *       Executar como: Eu  |  Quem pode acessar: Qualquer pessoa
 *  5. Copie a URL que termina em /exec e cole em assets/js/config.js.
 *
 * Abas criadas:
 *  - "Painel"       visão geral da turma (quem fez o quê e quando), com link para cada aba.
 *  - uma aba por estudante/grupo, com as respostas em formato legível.
 *  - "_alunos" e "_dados" (ocultas): base usada pelo portal. Não edite, exceto para
 *    redefinir uma palavra-chave (apague a célula "hash_chave" da pessoa; a próxima
 *    palavra-chave usada por ela passa a valer).
 *
 * As abas legíveis são atualizadas a cada 5 minutos (gatilho criado em "configurar")
 * ou na hora, pelo menu "Portal da disciplina > Atualizar abas e painel agora".
 */

var ABA_ALUNOS = '_alunos';
var ABA_DADOS = '_dados';
var ABA_PAINEL = 'Painel';
var SAL = 'vieses-e-decisao'; // alterar o sal invalida todas as palavras-chave já cadastradas
var COLS_ALUNOS = ['id', 'nome', 'turma', 'aba', 'hash_chave', 'criado_em', 'ultimo_acesso', 'pendente'];
var COLS_DADOS = ['id', 'ferramenta', 'titulo', 'atualizado_ms', 'json', 'resumo_json'];
var ORDEM = ['aula1', 'aula2', 'aula3', 'aula4'];
var LIMITE_CELULA = 49000;

/* ===================== Web app ===================== */

function doGet() {
  return saida({ ok: true, servico: 'Portal Vieses e Decisão', hora: new Date().toISOString() });
}

function doPost(e) {
  var req;
  try {
    req = JSON.parse(e.postData.contents);
  } catch (err) {
    return saida({ ok: false, erro: 'Requisição inválida.' });
  }
  try {
    if (req.acao === 'entrar') return saida(entrar(req));
    if (req.acao === 'salvar') return saida(salvar(req));
    return saida({ ok: false, erro: 'Ação desconhecida.' });
  } catch (err) {
    return saida({ ok: false, erro: 'Erro no servidor: ' + (err && err.message ? err.message : err) });
  }
}

function saida(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/* ===================== Ações ===================== */

function entrar(req) {
  var nome = limparNome(req.nome);
  var chave = String(req.chave || '').trim();
  if (!nome) return { ok: false, erro: 'Informe o nome.' };
  if (chave.length < 4) return { ok: false, erro: 'A palavra-chave precisa ter pelo menos 4 caracteres.' };
  var id = normalizar(nome);

  var al = lerAlunos();
  var i = acharAluno(al.linhas, id);

  if (i < 0) {
    if (!req.criar) return { ok: false, naoEncontrado: true };
    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      al = lerAlunos();
      i = acharAluno(al.linhas, id);
      if (i < 0) {
        var turma = limparNome(req.turma).slice(0, 60);
        var agora = String(Date.now());
        var linha = [id, nome, turma, nomeDeAbaUnico(nome, al.linhas), hashChave(id, chave), agora, agora, '1'];
        escreverTexto(al.sh.getRange(al.sh.getLastRow() + 1, 1, 1, linha.length), [linha]);
        SpreadsheetApp.flush();
        if (!gatilhoAtivo()) processarPendentes_(true);
        return { ok: true, criado: true, aluno: { id: id, nome: nome, turma: turma }, dados: {} };
      }
    } finally {
      lock.releaseLock();
    }
  }

  var a = alunoDe(al.linhas[i]);
  if (!conferirChave(al, i, a, chave)) {
    return { ok: false, chaveIncorreta: true, erro: 'Palavra-chave incorreta para "' + a.nome + '". Se você esqueceu, peça ao professor para redefini-la.' };
  }
  escreverTexto(al.sh.getRange(i + 2, 7), [[String(Date.now())]]);
  return { ok: true, aluno: { id: a.id, nome: a.nome, turma: a.turma }, dados: lerDadosDo(id) };
}

function salvar(req) {
  var id = normalizar(req.nome);
  var chave = String(req.chave || '').trim();
  var f = String(req.ferramenta || '').replace(/[^a-zA-Z0-9_\-]/g, '').slice(0, 60);
  if (!id || !f) return { ok: false, erro: 'Requisição incompleta.' };

  var json = JSON.stringify(req.data === undefined ? null : req.data);
  if (json.length > LIMITE_CELULA) {
    return { ok: false, erro: 'As respostas desta atividade ficaram grandes demais para a planilha (' + json.length + ' caracteres). Encurte alguns textos.' };
  }
  var resumo = sanitizarResumo(req.resumo);
  var resumoJson = JSON.stringify(resumo);
  if (resumoJson.length > LIMITE_CELULA) {
    resumoJson = JSON.stringify(resumo.map(function (r) { return [r[0], r[1], r[2].slice(0, 1500)]; }));
    if (resumoJson.length > LIMITE_CELULA) resumoJson = '[]';
  }

  var resultado;
  var lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    var al = lerAlunos();
    var i = acharAluno(al.linhas, id);
    if (i < 0) return { ok: false, sessaoInvalida: true, erro: 'Cadastro não encontrado na planilha. Entre novamente.' };
    var a = alunoDe(al.linhas[i]);
    if (!conferirChave(al, i, a, chave)) return { ok: false, sessaoInvalida: true, erro: 'A palavra-chave não confere. Entre novamente.' };

    var sh = aba(ABA_DADOS, COLS_DADOS);
    var n = sh.getLastRow() - 1;
    var linha = -1;
    if (n > 0) {
      var chaves = sh.getRange(2, 1, n, 2).getValues();
      for (var k = 0; k < chaves.length; k++) {
        if (String(chaves[k][0]) === id && String(chaves[k][1]) === f) { linha = k + 2; break; }
      }
    }
    if (linha > 0) {
      var ex = sh.getRange(linha, 4, 1, 2).getValues()[0];
      var atualRemoto = Number(ex[0]) || 0;
      var jsonRemoto = String(ex[1]);
      if (jsonRemoto === json) return { ok: true, atualizado: atualRemoto, semMudanca: true };
      var base = (req.base === null || req.base === undefined) ? null : Number(req.base);
      if (!req.forcar && (base === null || atualRemoto > base)) {
        var dataRemota = null;
        try { dataRemota = JSON.parse(jsonRemoto); } catch (err) {}
        return { ok: false, conflito: true, atualizado: atualRemoto, data: dataRemota };
      }
    }
    var agora = Date.now();
    var titulo = limparNome(req.titulo).slice(0, 120) || f;
    var r = linha > 0 ? linha : sh.getLastRow() + 1;
    escreverTexto(sh.getRange(r, 1, 1, COLS_DADOS.length), [[id, f, titulo, String(agora), json, resumoJson]]);
    escreverTexto(al.sh.getRange(i + 2, 7, 1, 2), [[String(agora), '1']]);
    resultado = { ok: true, atualizado: agora };
  } finally {
    lock.releaseLock();
  }
  if (!gatilhoAtivo()) {
    try { processarPendentes_(false); } catch (err) {}
  }
  return resultado;
}

/* ===================== Abas legíveis ===================== */

/** Executada pelo gatilho a cada 5 minutos. */
function processarPendentes() {
  processarPendentes_(false);
}

function processarPendentes_(jaTemLock) {
  var lock = LockService.getScriptLock();
  var alvos = [];
  if (!jaTemLock && !lock.tryLock(10000)) return;
  try {
    var al = lerAlunos();
    al.linhas.forEach(function (l, i) {
      if (String(l[7]) === '1') alvos.push({ i: i, a: alunoDe(l) });
    });
    alvos.forEach(function (p) { escreverTexto(al.sh.getRange(p.i + 2, 8), [['0']]); });
  } finally {
    if (!jaTemLock) lock.releaseLock();
  }
  if (!alvos.length) return;
  var dados = lerTodosDados();
  alvos.forEach(function (p) { montarAbaAluno(p.a, dados[p.a.id] || []); });
  montarPainel();
}

/** Menu: força a reconstrução de todas as abas. */
function atualizarTudo() {
  var al = lerAlunos();
  if (al.linhas.length) escreverTexto(al.sh.getRange(2, 8, al.linhas.length, 1), al.linhas.map(function () { return ['1']; }));
  processarPendentes_(false);
  montarPainel();
  try { SpreadsheetApp.getActiveSpreadsheet().toast('Abas e painel atualizados.', 'Portal da disciplina', 4); } catch (e) {}
}

function montarAbaAluno(a, regs) {
  var ss = planilha();
  var tz = ss.getSpreadsheetTimeZone();
  var sh = ss.getSheetByName(a.aba) || ss.insertSheet(a.aba);
  sh.clear();
  var L = [], titulos = [], cabecalhos = [];
  L.push([a.nome, a.turma ? 'Turma: ' + a.turma : '', 'Aba gerada pelo portal · atualizada em ' + quando(Date.now(), tz)]);
  L.push(['', '', '']);
  regs.sort(ordenar);
  regs.forEach(function (r) {
    titulos.push(L.length + 1);
    L.push([r.titulo || r.ferramenta, '', 'Salvo em ' + quando(r.atualizado, tz)]);
    cabecalhos.push(L.length + 1);
    L.push(['Seção', 'Campo', 'Resposta']);
    var linhas = (r.resumo && r.resumo.length) ? r.resumo : [['', '(sem resumo disponível)', '']];
    linhas.forEach(function (x) { L.push([texto(x[0]), texto(x[1]), texto(x[2])]); });
    L.push(['', '', '']);
  });
  if (!regs.length) L.push(['Nenhuma atividade salva ainda.', '', '']);

  var rg = sh.getRange(1, 1, L.length, 3);
  rg.setNumberFormat('@');
  rg.setValues(L);
  rg.setWrap(true).setVerticalAlignment('top').setFontFamily('Arial').setFontSize(10);
  sh.getRange(1, 1, 1, 3).setFontWeight('bold').setFontSize(12).setBackground('#2C1E37').setFontColor('#FFFFFF');
  if (titulos.length) sh.getRangeList(titulos.map(function (n) { return 'A' + n + ':C' + n; }))
    .setFontWeight('bold').setFontSize(11).setBackground('#402C4F').setFontColor('#FFFFFF');
  if (cabecalhos.length) sh.getRangeList(cabecalhos.map(function (n) { return 'A' + n + ':C' + n; }))
    .setFontWeight('bold').setBackground('#F2EFEA').setFontColor('#455066');
  sh.setColumnWidth(1, 190);
  sh.setColumnWidth(2, 240);
  sh.setColumnWidth(3, 640);
  sh.setFrozenRows(1);
  sh.setTabColor('#EFB93C');
}

function montarPainel() {
  var ss = planilha();
  var tz = ss.getSpreadsheetTimeZone();
  var al = lerAlunos();
  var dados = lerTodosDados();
  var sh = ss.getSheetByName(ABA_PAINEL);
  if (!sh) sh = ss.insertSheet(ABA_PAINEL, 0);
  sh.clear();

  var cab = ['Estudante / grupo', 'Turma', 'Aula 1 · Comportamento-alvo', 'Aula 2 · Barreiras', 'Aula 3 · Intervenção', 'Anotações nos materiais', 'Último acesso'];
  var alunos = al.linhas.map(function (l) { var a = alunoDe(l); a.ultimo = Number(l[6]) || 0; return a; });
  alunos.sort(function (x, y) { return (x.turma + '|' + x.nome).localeCompare(y.turma + '|' + y.nome, 'pt'); });

  var links = [];
  var corpo = alunos.map(function (a) {
    var por = {};
    (dados[a.id] || []).forEach(function (r) { por[r.ferramenta] = r; });
    var vieses = (dados[a.id] || []).filter(function (r) { return r.ferramenta.indexOf('vies-') === 0; }).length;
    var abaAluno = ss.getSheetByName(a.aba);
    // link de texto (sem fórmula): funciona em planilhas de qualquer idioma
    var rt = SpreadsheetApp.newRichTextValue().setText(a.nome || '—');
    if (abaAluno) rt = rt.setLinkUrl('#gid=' + abaAluno.getSheetId());
    links.push([rt.build()]);
    function q(r) { return r ? '✓ ' + quando(r.atualizado, tz) : '—'; }
    return [texto(a.nome), texto(a.turma || '—'), q(por.aula1), q(por.aula2), q(por.aula3), vieses ? vieses + ' material(is)' : '—', quando(a.ultimo, tz)];
  });

  sh.getRange(1, 1, 1, cab.length).setValues([cab])
    .setFontWeight('bold').setBackground('#2C1E37').setFontColor('#FFFFFF').setWrap(true).setVerticalAlignment('middle');
  if (corpo.length) {
    var rg = sh.getRange(2, 1, corpo.length, cab.length);
    rg.setNumberFormat('@');
    rg.setValues(corpo).setVerticalAlignment('top');
    sh.getRange(2, 1, corpo.length, 1).setRichTextValues(links);
  } else {
    sh.getRange(2, 1).setValue('Nenhum estudante cadastrado ainda.');
  }
  sh.setFrozenRows(1);
  sh.setColumnWidth(1, 220);
  sh.setColumnWidth(2, 130);
  for (var c = 3; c <= 7; c++) sh.setColumnWidth(c, 175);
  sh.setTabColor('#402C4F');
}

/* ===================== Configuração e menu ===================== */

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Portal da disciplina')
    .addItem('Atualizar abas e painel agora', 'atualizarTudo')
    .addItem('Remover um estudante ou grupo…', 'removerEstudante')
    .addSeparator()
    .addItem('Configurar (executar uma vez)', 'configurar')
    .addToUi();
}

/** Menu: apaga o cadastro, as respostas e a aba de um estudante/grupo (ex.: cadastros de teste ou duplicados). */
function removerEstudante() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Remover estudante ou grupo', 'Digite o nome exatamente como aparece no Painel:', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var id = normalizar(r.getResponseText());
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  var nome;
  try {
    var al = lerAlunos();
    var i = acharAluno(al.linhas, id);
    if (i < 0) { ui.alert('Ninguém com esse nome foi encontrado.'); return; }
    var a = alunoDe(al.linhas[i]);
    nome = a.nome;
    if (ui.alert('Remover "' + a.nome + '"?', 'O cadastro, todas as respostas e a aba serão apagados. Não dá para desfazer.', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
    var sd = aba(ABA_DADOS, COLS_DADOS);
    var n = sd.getLastRow() - 1;
    if (n > 0) {
      var ids = sd.getRange(2, 1, n, 1).getValues();
      for (var k = ids.length - 1; k >= 0; k--) if (String(ids[k][0]) === id) sd.deleteRow(k + 2);
    }
    al.sh.deleteRow(i + 2);
    var ss = planilha();
    var abaAluno = ss.getSheetByName(a.aba);
    if (abaAluno) ss.deleteSheet(abaAluno);
  } finally {
    lock.releaseLock();
  }
  montarPainel();
  ss.toast('"' + nome + '" foi removido.', 'Portal da disciplina', 4);
}

/** Execute uma vez, pelo editor do Apps Script, antes de implantar. */
function configurar() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var props = PropertiesService.getScriptProperties();
  props.setProperty('PLANILHA_ID', ss.getId());
  aba(ABA_ALUNOS, COLS_ALUNOS);
  aba(ABA_DADOS, COLS_DADOS);
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'processarPendentes') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('processarPendentes').timeBased().everyMinutes(5).create();
  props.setProperty('GATILHO', '1');
  montarPainel();
  var padrao = ss.getSheetByName('Página1') || ss.getSheetByName('Sheet1') || ss.getSheetByName('Planilha1');
  if (padrao && ss.getSheets().length > 1) {
    try { ss.deleteSheet(padrao); } catch (e) {}
  }
  try { SpreadsheetApp.getUi().alert('Portal configurado. Agora vá em Implantar > Nova implantação > App da Web.'); } catch (e) {}
}

function gatilhoAtivo() {
  return PropertiesService.getScriptProperties().getProperty('GATILHO') === '1';
}

/* ===================== Auxiliares ===================== */

function planilha() {
  var id = PropertiesService.getScriptProperties().getProperty('PLANILHA_ID');
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
}

function aba(nome, cabecalho) {
  var ss = planilha();
  var sh = ss.getSheetByName(nome);
  if (!sh) {
    sh = ss.insertSheet(nome);
    sh.getRange(1, 1, sh.getMaxRows(), cabecalho.length).setNumberFormat('@');
    sh.getRange(1, 1, 1, cabecalho.length).setValues([cabecalho])
      .setFontWeight('bold').setBackground('#2C1E37').setFontColor('#FFFFFF');
    sh.setFrozenRows(1);
    if (nome.charAt(0) === '_') sh.hideSheet();
  }
  return sh;
}

function lerAlunos() {
  var sh = aba(ABA_ALUNOS, COLS_ALUNOS);
  var n = sh.getLastRow() - 1;
  return { sh: sh, linhas: n > 0 ? sh.getRange(2, 1, n, COLS_ALUNOS.length).getValues() : [] };
}

function acharAluno(linhas, id) {
  for (var i = 0; i < linhas.length; i++) if (String(linhas[i][0]) === id) return i;
  return -1;
}

function alunoDe(l) {
  return { id: String(l[0]), nome: String(l[1]), turma: String(l[2]), aba: String(l[3]), hash: String(l[4]) };
}

function conferirChave(al, i, a, chave) {
  var h = hashChave(a.id, chave);
  if (!a.hash) { // palavra-chave redefinida pelo professor: a próxima usada passa a valer
    escreverTexto(al.sh.getRange(i + 2, 5), [[h]]);
    return true;
  }
  return a.hash === h;
}

function lerDadosDo(id) {
  var sh = aba(ABA_DADOS, COLS_DADOS);
  var n = sh.getLastRow() - 1;
  var out = {};
  if (n <= 0) return out;
  sh.getRange(2, 1, n, 5).getValues().forEach(function (l) {
    if (String(l[0]) !== id) return;
    var data = null;
    try { data = JSON.parse(l[4]); } catch (e) {}
    out[String(l[1])] = { titulo: String(l[2]), atualizado: Number(l[3]) || 0, data: data };
  });
  return out;
}

function lerTodosDados() {
  var sh = aba(ABA_DADOS, COLS_DADOS);
  var n = sh.getLastRow() - 1;
  var out = {};
  if (n <= 0) return out;
  sh.getRange(2, 1, n, COLS_DADOS.length).getValues().forEach(function (l) {
    var id = String(l[0]);
    var resumo = [];
    try { resumo = JSON.parse(l[5]) || []; } catch (e) {}
    (out[id] = out[id] || []).push({ ferramenta: String(l[1]), titulo: String(l[2]), atualizado: Number(l[3]) || 0, resumo: resumo });
  });
  return out;
}

function nomeDeAbaUnico(nome, linhas) {
  var base = String(nome).replace(/[\[\]\*\?\/\\:]/g, '-').replace(/^'+|'+$/g, '').trim().slice(0, 90) || 'Estudante';
  if (base.charAt(0) === '_' || base.toLowerCase() === ABA_PAINEL.toLowerCase()) base = 'Estudante ' + base;
  var ss = planilha();
  var usados = linhas.map(function (l) { return String(l[3]).toLowerCase(); });
  var nomeAba = base, k = 2;
  while (ss.getSheetByName(nomeAba) || usados.indexOf(nomeAba.toLowerCase()) >= 0) {
    nomeAba = base + ' (' + (k++) + ')';
  }
  return nomeAba;
}

function hashChave(id, chave) {
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,
    SAL + '|' + id + '|' + String(chave).trim().toLowerCase(), Utilities.Charset.UTF_8);
  var hex = '';
  for (var i = 0; i < bytes.length; i++) {
    var b = bytes[i] < 0 ? bytes[i] + 256 : bytes[i];
    hex += (b < 16 ? '0' : '') + b.toString(16);
  }
  return 'h' + hex;
}

function sanitizarResumo(r) {
  if (!Array.isArray(r)) return [];
  return r.slice(0, 400).map(function (x) {
    x = Array.isArray(x) ? x : [];
    return [String(x[0] == null ? '' : x[0]).slice(0, 200), String(x[1] == null ? '' : x[1]).slice(0, 1000), String(x[2] == null ? '' : x[2]).slice(0, 20000)];
  });
}

function ordenar(x, y) {
  var a = ORDEM.indexOf(x.ferramenta), b = ORDEM.indexOf(y.ferramenta);
  a = a < 0 ? 100 : a; b = b < 0 ? 100 : b;
  if (a !== b) return a - b;
  return String(x.titulo).localeCompare(String(y.titulo), 'pt');
}

function escreverTexto(range, valores) {
  range.setNumberFormat('@');
  range.setValues(valores.map(function (linha) { return linha.map(texto); }));
}

/**
 * Impede que respostas começando com =, +, - ou @ virem fórmulas.
 * (Nos testes, o formato "texto simples" sozinho não impediu a fórmula; o apóstrofo inicial força texto.)
 */
function texto(v) {
  var s = String(v == null ? '' : v);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function quando(ms, tz) {
  ms = Number(ms);
  if (!ms) return '—';
  return Utilities.formatDate(new Date(ms), tz || 'America/Sao_Paulo', 'dd/MM/yyyy HH:mm');
}

function limparNome(s) {
  return String(s == null ? '' : s).trim().replace(/\s+/g, ' ');
}

function normalizar(nome) {
  var s = limparNome(nome);
  if (typeof s.normalize === 'function') s = s.normalize('NFD').replace(/[̀-ͯ]/g, '');
  return s.toLowerCase();
}
