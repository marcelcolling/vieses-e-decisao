"""
Gera a página HTML da leitura a partir do arquivo Markdown original.

Uso (na pasta do repositório):
    python ferramentas/gerar_leitura.py

O texto do Markdown é mantido na íntegra: o script só converte a marcação
(títulos, tabelas, listas, negrito, itálico) e organiza visualmente o conteúdo
(sumário lateral, partes, exemplos recolhíveis, destaques). Para corrigir ou
atualizar o texto, edite o .md em conteudo/ e rode o script de novo.
Não precisa instalar nada além do Python 3.
"""
import html
import math
import pathlib
import re
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent

LEITURAS = [
    {
        "fonte": RAIZ / "conteudo" / "material-passo-1-objetivos-e-indicadores.md",
        "destino": RAIZ / "leituras" / "passo-1-objetivos-e-indicadores.html",
        "selo": "Leitura · Aula 1",
        "titulo_curto": "Objetivos e indicadores",
        "tag": "Aula 1 · Target · Material de leitura",
        "base": "TESTS · Behavioural Insights Team",
        "aula": "1 · Target",
        "atividade": ("../atividades/aula-1-comportamento-alvo.html", "Do objetivo ao comportamento-alvo"),
    },
]

# Parágrafos que começam com estes rótulos em negrito viram caixas de destaque.
CALLOUTS = {
    "Consequência prática": "chave",
    "Frase final": "frase",
    "Observação": "nota",
    "Nota": "nota",
    "Por que este exemplo importa": "nota",
    "Por que abrir por grupo": "nota",
    "Lição do caso": "nota",
    "Base": "nota",
    "Por que este exemplo existe": "nota",
    "O que se pode ler dessa tabela, com cuidado": "chave",
    "Fora da literatura citada": "nota",
}
LENTES = {"A5.1": "🛒", "A5.2": "🏢", "A5.3": "👥", "A5.4": "👤"}


# ---------------------------------------------------------------- utilidades
def slug(texto, usados):
    s = unicodedata.normalize("NFD", texto)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "secao"
    base, n = s, 2
    while s in usados:
        s = f"{base}-{n}"
        n += 1
    usados.add(s)
    return s


def inline(texto):
    s = html.escape(texto, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def texto_puro(texto):
    return re.sub(r"\*+", "", texto)


def celulas(linha):
    linha = linha.strip()
    if linha.startswith("|"):
        linha = linha[1:]
    if linha.endswith("|"):
        linha = linha[:-1]
    return [c.strip() for c in linha.split("|")]


# ---------------------------------------------------------------- leitura dos blocos
INICIO_BLOCO = re.compile(r"^(#{1,6}\s|\||- |\* |\d+\.\s|---\s*$)")


def blocos(linhas):
    i, n = 0, len(linhas)
    while i < n:
        s = linhas[i].strip()
        if not s:
            i += 1
            continue
        if re.fullmatch(r"-{3,}", s):
            yield ("hr",)
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            yield ("h", len(m.group(1)), m.group(2).strip())
            i += 1
            continue
        if s.startswith("|"):
            linhas_tab = []
            while i < n and linhas[i].strip().startswith("|"):
                linhas_tab.append(linhas[i].strip())
                i += 1
            yield ("table", linhas_tab)
            continue
        if re.match(r"^- \[[ xX]\] ", s):
            itens = []
            while i < n and re.match(r"^- \[[ xX]\] ", linhas[i].strip()):
                itens.append(re.sub(r"^- \[[ xX]\] ", "", linhas[i].strip()))
                i += 1
            yield ("check", itens)
            continue
        if re.match(r"^[-*] ", s):
            itens = []
            while i < n and re.match(r"^[-*] ", linhas[i].strip()):
                itens.append(linhas[i].strip()[2:])
                i += 1
            yield ("ul", itens)
            continue
        if re.match(r"^\d+\.\s", s):
            itens = []
            while i < n and re.match(r"^\d+\.\s", linhas[i].strip()):
                itens.append(re.sub(r"^\d+\.\s+", "", linhas[i].strip()))
                i += 1
            yield ("ol", itens)
            continue
        par = [s]
        i += 1
        while i < n and linhas[i].strip() and not INICIO_BLOCO.match(linhas[i].strip()):
            par.append(linhas[i].strip())
            i += 1
        yield ("p", " ".join(par))


# ---------------------------------------------------------------- renderização
def render_tabela(linhas_tab):
    cab = celulas(linhas_tab[0])
    corpo = [celulas(l) for l in linhas_tab[1:] if not re.fullmatch(r"\|?[\s:\-|]+\|?", l)]
    classes = ["tabela"]
    if len(cab) == 2 and cab[0] in ("Campo", "Parte"):
        classes.append("tabela-ficha")
    if len(cab) >= 3:
        classes.append("tabela-cards")
    out = [f'<div class="tabela-wrap"><table class="{" ".join(classes)}"><thead><tr>']
    out += [f"<th>{inline(c)}</th>" for c in cab]
    out.append("</tr></thead><tbody>")
    for linha in corpo:
        out.append("<tr>")
        for j, c in enumerate(linha):
            rotulo = html.escape(texto_puro(cab[j]) if j < len(cab) else "", quote=True)
            out.append(f'<td data-label="{rotulo}">{inline(c)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def render_paragrafo(texto):
    m = re.match(r"^\*\*(.+?)[.:]?\*\*", texto)
    if m:
        rotulo = m.group(1).rstrip(".:")
        tipo = CALLOUTS.get(rotulo)
        if tipo:
            return f'<div class="callout callout-{tipo}"><p>{inline(texto)}</p></div>'
        return f'<p class="p-rotulo">{inline(texto)}</p>'
    return f"<p>{inline(texto)}</p>"


def gerar(cfg):
    md = cfg["fonte"].read_text(encoding="utf-8")
    linhas = md.splitlines()
    palavras = len(re.findall(r"\w+", md))
    minutos = max(1, math.ceil(palavras / 210))

    usados = set()
    titulo = ""
    subtitulo = ""
    toc = []          # (nivel, id, rotulo)
    corpo = []
    parte_aberta = False
    secao_aberta = False
    exemplo_aberto = False
    chk = 0

    def fechar_exemplo():
        nonlocal exemplo_aberto
        if exemplo_aberto:
            corpo.append("</div></details>")
            exemplo_aberto = False

    def fechar_secao():
        nonlocal secao_aberta
        fechar_exemplo()
        if secao_aberta:
            corpo.append("</section>")
            secao_aberta = False

    def fechar_parte():
        nonlocal parte_aberta
        fechar_secao()
        if parte_aberta:
            corpo.append("</div>")
            parte_aberta = False

    for b in blocos(linhas):
        tipo = b[0]
        if tipo == "hr":
            continue

        if tipo == "h":
            nivel, txt = b[1], b[2]
            if nivel == 1 and not titulo:
                titulo = txt
                continue
            m_parte = re.match(r"^PARTE\s+([A-Z])\s*:\s*(.+)$", txt)
            if nivel == 1 and m_parte:
                fechar_parte()
                letra, nome = m_parte.group(1), m_parte.group(2)
                pid = slug("parte-" + letra, usados)
                toc.append((1, pid, f"Parte {letra} · {texto_puro(nome)}"))
                corpo.append(
                    f'<div class="parte" id="{pid}">'
                    f'<header class="parte-cab"><span class="parte-letra">{letra}</span>'
                    f'<div><span class="parte-eyebrow">Parte {letra}</span><h2 class="parte-titulo">{inline(nome)}</h2></div></header>'
                )
                parte_aberta = True
                continue
            if nivel == 1:
                fechar_parte()
                sid = slug(txt, usados)
                toc.append((1, sid, texto_puro(txt)))
                corpo.append(f'<section class="secao" id="{sid}"><h2 class="secao-titulo">{inline(txt)}</h2>')
                secao_aberta = True
                continue
            if nivel == 2:
                if txt == "Fontes":
                    fechar_parte()
                    sid = slug(txt, usados)
                    toc.append((1, sid, "Fontes"))
                    corpo.append(f'<section class="secao secao-fontes" id="{sid}"><h2 class="secao-titulo">{inline(txt)}</h2>')
                    secao_aberta = True
                    continue
                m_ex = re.match(r"^(Exemplo\s+\d+)\s*:\s*(.+)$", txt)
                if m_ex and parte_aberta:
                    fechar_exemplo()
                    if not secao_aberta:
                        corpo.append('<section class="secao secao-exemplos">')
                        secao_aberta = True
                    eid = slug(txt, usados)
                    toc.append((2, eid, f"{m_ex.group(1)}: {texto_puro(m_ex.group(2))}"))
                    corpo.append(
                        f'<details class="exemplo" id="{eid}"><summary>'
                        f'<span class="exemplo-num">{inline(m_ex.group(1))}</span>'
                        f'<span class="exemplo-titulo">{inline(m_ex.group(2))}</span>'
                        f'<span class="exemplo-ico" aria-hidden="true">+</span></summary><div class="exemplo-corpo">'
                    )
                    exemplo_aberto = True
                    continue
                fechar_secao()
                sid = slug(txt, usados)
                m_cod = re.match(r"^([A-Z]\d+)\.\s+(.+)$", txt)
                toc.append((2 if parte_aberta else 1, sid, texto_puro(txt)))
                if m_cod:
                    h = f'<h3 class="secao-titulo"><span class="secao-cod">{m_cod.group(1)}</span>{inline(m_cod.group(2))}</h3>'
                else:
                    h = f'<h3 class="secao-titulo">{inline(txt)}</h3>' if parte_aberta else f'<h2 class="secao-titulo">{inline(txt)}</h2>'
                corpo.append(f'<section class="secao" id="{sid}">{h}')
                secao_aberta = True
                continue
            # nível 3 ou mais
            m_lente = re.match(r"^(A5\.\d)\s+(.+)$", txt)
            if m_lente and m_lente.group(1) in LENTES:
                sid = slug(txt, usados)
                corpo.append(
                    f'<h4 class="lente" id="{sid}"><span class="lente-ico" aria-hidden="true">{LENTES[m_lente.group(1)]}</span>'
                    f'<span><span class="lente-cod">{m_lente.group(1)}</span>{inline(m_lente.group(2))}</span></h4>'
                )
            else:
                corpo.append(f'<h4 class="sub">{inline(txt)}</h4>')
            continue

        if tipo == "p":
            texto = b[1]
            if titulo and not subtitulo and not corpo and re.fullmatch(r"\*\*.+\*\*", texto):
                subtitulo = texto.strip("*")
                continue
            if not secao_aberta and not parte_aberta and not corpo:
                pass
            corpo.append(render_paragrafo(texto))
        elif tipo == "table":
            corpo.append(render_tabela(b[1]))
        elif tipo == "ul":
            corpo.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + "</ul>")
        elif tipo == "ol":
            corpo.append('<ol class="numerada">' + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + "</ol>")
        elif tipo == "check":
            itens = []
            for x in b[1]:
                itens.append(
                    f'<li><label><input type="checkbox" data-chk="{chk}"><span class="chk-caixa" aria-hidden="true"></span>'
                    f"<span>{inline(x)}</span></label></li>"
                )
                chk += 1
            corpo.append('<ul class="checklist">' + "".join(itens) + "</ul>")

    fechar_parte()

    # ----- sumário lateral
    nav = []
    for nivel, sid, rot in toc:
        classe = "nav-item" + (" sub" if nivel == 2 else "")
        nav.append(f'<a class="{classe}" href="#{sid}">{html.escape(rot)}</a>')

    url_ativ, nome_ativ = cfg["atividade"]
    cta = (
        '<aside class="cta-atividade">'
        '<div><span class="cta-eyebrow">Hora de praticar</span>'
        f'<h3>{html.escape(nome_ativ)}</h3>'
        '<p>Use a Ficha do Desafio como guia para preencher a atividade da aula. Suas respostas são salvas automaticamente.</p></div>'
        f'<a class="cta-btn" href="{url_ativ}">Abrir a atividade →</a></aside>'
    )
    # coloca o convite à atividade antes das Fontes
    corpo_html = "\n".join(corpo)
    marcador = '<section class="secao secao-fontes"'
    if marcador in corpo_html:
        corpo_html = corpo_html.replace(marcador, cta + "\n" + marcador, 1)
    else:
        corpo_html += cta

    pagina = MODELO.format(
        titulo=html.escape(texto_puro(titulo)),
        titulo_h1=inline(titulo),
        subtitulo=html.escape(subtitulo),
        selo=html.escape(cfg["selo"]),
        titulo_curto=html.escape(cfg["titulo_curto"]),
        tag=html.escape(cfg["tag"]),
        minutos=minutos,
        base=html.escape(cfg["base"]),
        aula=html.escape(cfg["aula"]),
        nav="\n  ".join(nav),
        corpo=corpo_html,
        url_ativ=url_ativ,
        chave=cfg["destino"].stem,
    )
    cfg["destino"].parent.mkdir(parents=True, exist_ok=True)
    cfg["destino"].write_text(pagina, encoding="utf-8")
    print(f"OK  {cfg['destino'].relative_to(RAIZ)}  ({palavras} palavras, ~{minutos} min)")


MODELO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
<!-- Página gerada por ferramentas/gerar_leitura.py a partir do Markdown em conteudo/. Não edite à mão. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400;1,9..144,500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/css/portal.css">
<link rel="stylesheet" href="../assets/css/leitura.css">
</head>
<body data-chave="{chave}">

<div id="progress-bar"></div>
<button id="sidebar-toggle" aria-label="Abrir sumário"><span></span><span></span><span></span></button>
<div id="overlay"></div>

<nav id="sidebar" aria-label="Sumário">
  <div class="sidebar-badge"><span class="dot"></span><span>{selo}</span></div>
  <div class="sidebar-title">{titulo_curto}</div>
  <a class="nav-item nav-voltar" href="../index.html">← Voltar ao portal</a>
  <a class="nav-item" href="#intro">Início</a>
  {nav}
  <a class="nav-item nav-atividade" href="{url_ativ}">✎ Ir para a atividade</a>
</nav>

<main class="wrapper">

  <section class="hero" id="intro">
    <div class="hero-tag"><span class="dot"></span>{tag}</div>
    <h1>{titulo_h1}</h1>
    <p class="hero-sub">{subtitulo}</p>
    <div class="hero-meta">
      <div class="meta-item"><span class="meta-label">Tempo de leitura</span><span class="meta-value">{minutos} min</span></div>
      <div class="meta-item"><span class="meta-label">Base</span><span class="meta-value">{base}</span></div>
      <div class="meta-item"><span class="meta-label">Aula</span><span class="meta-value">{aula}</span></div>
    </div>
    <div class="hero-acoes">
      <a class="hero-btn" href="{url_ativ}">Abrir a atividade da aula</a>
      <button type="button" class="hero-btn hero-btn-ghost" onclick="window.print()">Imprimir / salvar PDF</button>
    </div>
  </section>

{corpo}

</main>

<button id="back-to-top" title="Voltar ao topo" aria-label="Voltar ao topo">&#8593;</button>
<script src="../assets/js/leitura.js"></script>
</body>
</html>
"""


if __name__ == "__main__":
    for cfg in LEITURAS:
        gerar(cfg)
