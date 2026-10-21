"""
Gera a página HTML da leitura a partir do arquivo Markdown original.

Uso (na pasta do repositório):
    python ferramentas/gerar_leitura.py

O texto do Markdown é mantido na íntegra: o script só converte a marcação
(títulos, tabelas, listas, negrito, itálico) e organiza visualmente o conteúdo
(sumário lateral, partes, exemplos recolhíveis, destaques). Para corrigir ou
atualizar o texto, edite o .md em conteudo/ e rode o script de novo.
Não precisa instalar nada além do Python 3.

Leituras com "recursos_comb": True (Aula 2) ganham também: siglas do COM-B
coloridas e clicáveis, mapa dos seis componentes, fichas dos componentes,
frases de corredor para revelar, escada de evidência, os quatro movimentos
em cartões e o "cartão de bolso" (resumo que abre numa gaveta lateral).
Esses recursos só mudam a apresentação; o texto continua o do .md.
"""
import html
import json
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
    {
        "fonte": RAIZ / "conteudo" / "material-passo-2-explorar-o-comportamento.md",
        "destino": RAIZ / "leituras" / "passo-2-explorar-o-comportamento.html",
        "selo": "Leitura · Aula 2",
        "titulo_curto": "Explorar e compreender o comportamento",
        "tag": "Aula 2 · Explore · Material de leitura",
        "base": "TESTS (BIT) · COM-B",
        "aula": "2 · Explore",
        "atividade": ("../atividades/aula-2-barreiras.html", "Levantamento, triangulação e priorização de barreiras"),
        "cta_texto": "Leve os quatro movimentos para o seu comportamento-alvo na atividade da aula. Suas respostas são salvas automaticamente.",
        "pratica": ("../atividades/aula-2-clinica.html", "Clínica de diagnóstico",
                    "A Parte E: treino em grupo com casos prontos (mini-casos e dossiês), antes da atividade principal."),
        "recursos_comb": True,
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
    "Regra da sala": "chave",
    "O que o mapa já mostra": "nota",
    "Regras de campo": "nota",
}
LENTES = {"A5.1": "🛒", "A5.2": "🏢", "A5.3": "👥", "A5.4": "👤"}

# Estado da leitura em geração (preenchido por gerar(); vazio = sem recursos COM-B).
CTX = {}

# Recursos COM-B (só com "recursos_comb"): rótulos que viram campos nas fichas dos componentes.
CAMPOS = {
    "O que é": "def",
    "O que inclui": "inclui",
    "O que inclui, em três camadas": "inclui",
    "Por que importa tanto": "importa",
    "Com o que se confunde": "confunde",
    "Como aparece na prática": "aparece",
    "Como confirmar": "confirmar",
    "Exemplo": "exemplo",
    "Atenção": "atencao",
}
SIGLAS_COMB = ("CF", "CP", "OF", "OS", "MR", "MA")
MARCAS = {  # marcações de evidência que não são barreiras: nome, explicação curta, seção
    "F": ("facilitador", "Algo que já funciona.", "b3-quanto-confiar-em-cada-evidencia"),
    "L": ("localizador", "Diz onde, quando ou para quem; não explica por quê.", "b2-localizar-nao-e-explicar"),
    "RUÍDO": ("ruído", "Não fala deste comportamento.", "b3-quanto-confiar-em-cada-evidencia"),
}


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


def inline(texto, chips=True):
    s = html.escape(texto, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    if chips and CTX.get("siglas"):
        s = re.sub(r"<strong>(F|L|RUÍDO)</strong>", lambda m: "<strong>" + chip(m.group(1)) + "</strong>", s)
        s = re.sub(r"(<[^>]+>)|(?<!\w)(CF|CP|OF|OS|MR|MA)(?!\w)", lambda m: m.group(1) or chip(m.group(2)), s)
    if CTX.get("cartao"):
        s = s.replace("cartão de bolso", f'<a class="link-cartao" href="#{CTX["cartao"]}">cartão de bolso</a>')
    return s


def familia(sigla):
    if sigla in SIGLAS_COMB:
        return {"C": "c", "O": "o", "M": "m"}[sigla[0]]
    return {"F": "f", "L": "l"}.get(sigla, "r")


def chip(sigla, interativo=True):
    """Sigla colorida. Clicável (abre a explicação curta) quando interativa."""
    nome = CTX["siglas"][sigla]["nome"] if sigla in SIGLAS_COMB else MARCAS[sigla][0]
    cls = f"sigla s-{familia(sigla)}"
    if not interativo:
        return f'<span class="{cls}">{sigla}</span>'
    return f'<abbr class="{cls}" data-sigla="{sigla}" title="{html.escape(nome)}" tabindex="0" role="button">{sigla}</abbr>'


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
INICIO_BLOCO = re.compile(r"^(#{1,6}\s|\||- |\* |\d+\.\s|---\s*$|>)")


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
        if s.startswith(">"):
            partes = []
            while i < n and linhas[i].strip().startswith(">"):
                partes.append(linhas[i].strip()[1:].strip())
                i += 1
            yield ("quote", " ".join(partes))
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
    if CTX.get("siglas"):
        if cab[:2] == ["#", "Movimento"]:
            return render_movimentos(cab, corpo)
        if cab[0] == "Frase":
            return render_revelar(cab, corpo)
        if cab[0] == "Degrau":
            return render_escada(cab, corpo)
        if not any(cab):  # tabela sem cabeçalho: vira ficha de dois campos
            out = ['<div class="tabela-wrap"><table class="tabela tabela-ficha tabela-sem-cab"><tbody>']
            for linha in corpo:
                out.append("<tr>" + "".join(f"<td>{celula(c)}</td>" for c in linha) + "</tr>")
            out.append("</tbody></table></div>")
            return "".join(out)
    classes = ["tabela"]
    if len(cab) == 2 and cab[0] in ("Campo", "Parte"):
        classes.append("tabela-ficha")
    if len(cab) >= 3:
        classes.append("tabela-cards")
    compacta = bool(CTX.get("siglas")) and len(cab) >= 3  # no celular, células curtas lado a lado
    if compacta:
        classes.append("tabela-compacta")
    out = [f'<div class="tabela-wrap"><table class="{" ".join(classes)}"><thead><tr>']
    out += [f"<th>{inline(c)}</th>" for c in cab]
    out.append("</tr></thead><tbody>")
    for linha in corpo:
        out.append("<tr>")
        for j, c in enumerate(linha):
            rotulo = html.escape(texto_puro(cab[j]) if j < len(cab) else "", quote=True)
            curta = ' class="curta"' if compacta and (j > 0 or cab[0] == "#") and len(texto_puro(c)) <= 22 else ""
            out.append(f'<td data-label="{rotulo}"{curta}>{celula(c)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def celula(c):
    if CTX.get("siglas") and c.strip() in MARCAS:
        return chip(c.strip())
    return inline(c)


def render_movimentos(cab, corpo):
    """Os quatro movimentos em cartões numerados, cada um ligado à sua seção da Parte C."""
    out = ['<ol class="movimentos">']
    for i, linha in enumerate(corpo):
        alvo = CTX["movimentos"][i][2] if i < len(CTX["movimentos"]) else ""
        out.append(
            f'<li class="movimento"><a href="#{alvo}"><span class="mov-topo"><span class="mov-n">{html.escape(linha[0])}</span>'
            f'<span class="mov-rot">{inline(cab[1])}</span></span>'
            f'<span class="mov-nome">{inline(linha[1])}</span>'
            f'<span class="mov-campo"><span class="mov-rot">{inline(cab[2])}</span>{inline(linha[2])}</span>'
            f'<span class="mov-campo"><span class="mov-rot">{inline(cab[3])}</span>{inline(linha[3])}</span></a></li>'
        )
    out.append("</ol>")
    return "".join(out)


def render_revelar(cab, corpo):
    """Tabela de frases em cartões: a frase fica à vista e o restante abre com um toque."""
    out = [
        '<div class="revelar"><div class="revelar-acoes"><span class="revelar-dica">Antes de abrir cada frase, '
        'pense no que ela pode esconder. Depois, toque para conferir.</span>'
        '<button type="button" class="revelar-todas">Revelar todas</button></div><div class="revelar-grade">'
    ]
    for linha in corpo:
        out.append(
            f'<details class="revela"><summary><span class="revela-rot">{inline(cab[0])}</span>'
            f'<span class="revela-frase">{inline(linha[0])}</span><span class="revela-ico" aria-hidden="true">+</span></summary>'
            '<div class="revela-corpo">'
        )
        for j in range(1, len(cab)):
            out.append(f'<p><span class="revela-campo">{inline(cab[j])}</span>{inline(linha[j])}</p>')
        out.append("</div></details>")
    out.append("</div></div>")
    return "".join(out)


def render_escada(cab, corpo):
    """Escada de evidência: do degrau mais confiável ao menos confiável."""
    n = len(corpo)
    out = [
        '<div class="escada-wrap"><div class="escada-eixo" aria-hidden="true"><span>Mais confiança</span>'
        '<span>Menos confiança</span></div><ol class="escada">'
    ]
    for i, linha in enumerate(corpo):
        nivel = n - i
        barras = "".join(f'<i class="{"on" if k < nivel else ""}"></i>' for k in range(n))
        campos = "".join(
            f'<p class="degrau-campo"><span class="degrau-rot">{inline(cab[j])}</span>{inline(linha[j])}</p>'
            for j in range(1, len(cab))
        )
        out.append(
            f'<li class="degrau" style="--i:{i}"><div class="degrau-topo"><span class="degrau-rot">{inline(cab[0])} {i + 1}</span>'
            f'<span class="degrau-nome">{inline(linha[0])}</span>'
            f'<span class="degrau-conf" role="img" aria-label="confiança {nivel} de {n}">{barras}</span></div>{campos}</li>'
        )
    out.append("</ol></div>")
    return "".join(out)


def render_mapa():
    """Mapa interativo dos seis componentes (entra no fim da seção A1)."""
    cols = []
    for letra, sigs in (("C", ("CF", "CP")), ("O", ("OF", "OS")), ("M", ("MR", "MA"))):
        fam = CTX["familias"].get(letra, {})
        itens = "".join(
            f'<a class="mapa-item" href="#{CTX["siglas"][s]["id"]}">{chip(s, False)}'
            f'<span class="mapa-item-txt"><strong>{html.escape(CTX["siglas"][s]["nome"])}</strong>'
            f'<span>{html.escape(CTX["siglas"][s]["pergunta"])}</span></span><span class="mapa-seta" aria-hidden="true">→</span></a>'
            for s in sigs
        )
        cols.append(
            f'<div class="mapa-familia fam-{letra.lower()}"><div class="mapa-fam-cab"><span class="mapa-letra">{letra}</span>'
            f'<div><strong>{html.escape(fam.get("nome", ""))}</strong><small>{html.escape(fam.get("pergunta", ""))}</small></div></div>{itens}</div>'
        )
    return (
        '<div class="mapa-comb" aria-label="Mapa dos seis componentes do COM-B">'
        '<div class="mapa-topo"><span class="mapa-eyebrow">Mapa do COM-B</span>'
        '<span>Toque num componente para ir direto à explicação.</span></div>'
        f'<div class="mapa-grade">{"".join(cols)}</div>'
        '<div class="mapa-b"><span class="mapa-letra">B</span><div><strong>Comportamento</strong>'
        '<small>C + O + M, ao mesmo tempo, naquele momento</small></div></div></div>'
    )


def render_comp_nav(atual):
    itens = []
    for s in SIGLAS_COMB:
        extra = ' class="atual" aria-current="true"' if s == atual else ""
        itens.append(f'<a href="#{CTX["siglas"][s]["id"]}"{extra}>{chip(s, False)}</a>')
    return f'<nav class="comp-nav" aria-label="Componentes">{"".join(itens)}</nav>'


def render_stepper(cod):
    itens = []
    atual = next((k for k, m in enumerate(CTX["movimentos"]) if m[3] == cod), -1)
    for k, (num, nome, alvo, _) in enumerate(CTX["movimentos"]):
        cls = "atual" if k == atual else ("feito" if k < atual else "")
        itens.append(
            f'<li class="{cls}"><a href="#{alvo}"><span class="st-n">{html.escape(num)}</span>'
            f'<span class="st-nome">{html.escape(nome)}</span></a></li>'
        )
    return f'<ol class="stepper" aria-label="Os quatro movimentos">{"".join(itens)}</ol>'


def preparar_comb(linhas):
    """Lê do próprio .md os nomes, perguntas e âncoras usados pelos recursos COM-B."""
    siglas, familias, movimentos, secoes_c = {}, {}, [], {}
    antes_da_parte_a = True
    for l in linhas:
        s = l.strip()
        if s.startswith("# PARTE"):
            antes_da_parte_a = False
        # linha da tabela-resumo: "| **CF** capacidade física | pergunta |" (só duas colunas, primeira ocorrência)
        m = re.match(r"^\|\s*\*\*(CF|CP|OF|OS|MR|MA)\*\*\s+([^|]+?)\s*\|\s*([^|]+?)\s*\|$", s)
        if m and "nome" not in siglas.get(m.group(1), {}):
            siglas.setdefault(m.group(1), {}).update(nome=m.group(2), pergunta=texto_puro(m.group(3)))
        m = re.match(r"^\|\s*\*\*([COM]): (.+?)\*\*\s*\|\s*(.+?)\s*\|", s)
        if m:
            familias[m.group(1)] = {"nome": m.group(2), "pergunta": texto_puro(m.group(3))}
        m = re.match(r"^##\s+((A\d)\.\s+(CF|CP|OF|OS|MR|MA):\s+.+)$", s)
        if m:
            siglas.setdefault(m.group(3), {}).update(id=slug(m.group(1), set()), cod=m.group(2))
        m = re.match(r"^##\s+((C\d)\.\s+.+)$", s)
        if m:
            secoes_c[m.group(2)] = slug(m.group(1), set())
        m = re.match(r"^\|\s*(\d)\s*\|\s*\*\*(.+?)\*\*\s*\|", s)
        if m and antes_da_parte_a:
            movimentos.append((m.group(1), m.group(2)))
    movimentos = [(n, nome, secoes_c.get(f"C{n}", ""), f"C{n}") for n, nome in movimentos]
    faltando = [s for s in SIGLAS_COMB if not {"nome", "pergunta", "id"} <= set(siglas.get(s, {}))]
    assert not faltando, f"recursos_comb: não achei nome, pergunta ou seção de {faltando}"
    return {"siglas": siglas, "familias": familias, "movimentos": movimentos}


def render_paragrafo(texto):
    m = re.match(r"^\*\*(.+?)[.:]?\*\*", texto)
    if m:
        rotulo = m.group(1).rstrip(".:")
        tipo = CALLOUTS.get(rotulo)
        if tipo:
            return f'<div class="callout callout-{tipo}"><p>{inline(texto)}</p></div>'
        return f'<p class="p-rotulo">{inline(texto)}</p>'
    return f"<p>{inline(texto)}</p>"


CTA_PADRAO = "Use a Ficha do Desafio como guia para preencher a atividade da aula. Suas respostas são salvas automaticamente."


def gerar(cfg):
    md = cfg["fonte"].read_text(encoding="utf-8")
    linhas = md.splitlines()
    CTX.clear()
    comb = bool(cfg.get("recursos_comb"))
    if comb:
        CTX.update(preparar_comb(linhas))
        CTX["cartao"] = slug("O passo em uma página", set())
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
    campo_aberto = False      # campo da ficha de um componente (recursos COM-B)
    caso_aberto = False       # caixa "Exemplo completo" (recursos COM-B)
    em_componente = False
    mapa_feito = False
    chk = 0

    def fechar_campo():
        nonlocal campo_aberto
        if campo_aberto:
            corpo.append("</div>")
            campo_aberto = False

    def fechar_exemplo():
        nonlocal exemplo_aberto
        if exemplo_aberto:
            corpo.append("</div></details>")
            exemplo_aberto = False

    def fechar_secao():
        nonlocal secao_aberta, caso_aberto, em_componente
        fechar_campo()
        if caso_aberto:
            corpo.append("</div>")
            caso_aberto = False
        em_componente = False
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
                    f'<div><span class="parte-eyebrow">Parte {letra}</span><h2 class="parte-titulo">{inline(nome, chips=False)}</h2></div></header>'
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
                m_comp = re.match(r"^(A\d)\.\s+(CF|CP|OF|OS|MR|MA):\s+(.+)$", txt) if comb else None
                if m_comp and not mapa_feito:
                    corpo.append(render_mapa())
                    mapa_feito = True
                fechar_secao()
                sid = slug(txt, usados)
                m_cod = re.match(r"^([A-Z]\d+)\.\s+(.+)$", txt)
                toc.append((2 if parte_aberta else 1, sid, texto_puro(txt)))
                if m_comp:
                    cod, sig, nome = m_comp.groups()
                    assert sid == CTX["siglas"][sig]["id"], (sid, sig)
                    fam = CTX["familias"].get(sig[0], {}).get("nome", "")
                    corpo.append(
                        f'<section class="secao componente comp-{familia(sig)}" id="{sid}">'
                        f'<header class="comp-cab"><span class="comp-sigla" aria-hidden="true">{sig}</span><div>'
                        f'<span class="comp-familia">{html.escape(fam)}</span>'
                        f'<h3 class="secao-titulo"><span class="secao-cod">{cod}</span>{inline(sig + ": " + nome, chips=False)}</h3>'
                        f'<p class="comp-pergunta">{html.escape(CTX["siglas"][sig]["pergunta"])}</p></div></header>'
                        + render_comp_nav(sig)
                    )
                    secao_aberta = True
                    em_componente = True
                    continue
                if comb and sid == CTX["cartao"]:
                    corpo.append(
                        f'<section class="secao secao-cartao" id="{sid}"><h2 class="secao-titulo">{inline(txt)}</h2>'
                        '<p class="cartao-dica">Este resumo também fica no botão <strong>Cartão de bolso</strong>, '
                        'no canto da tela, para consultar durante a leitura.</p>'
                    )
                    secao_aberta = True
                    continue
                if m_cod:
                    h = f'<h3 class="secao-titulo"><span class="secao-cod">{m_cod.group(1)}</span>{inline(m_cod.group(2), chips=False)}</h3>'
                else:
                    h = f'<h3 class="secao-titulo">{inline(txt)}</h3>' if parte_aberta else f'<h2 class="secao-titulo">{inline(txt)}</h2>'
                corpo.append(f'<section class="secao" id="{sid}">{h}')
                if comb and m_cod and any(m[3] == m_cod.group(1) for m in CTX["movimentos"]):
                    corpo.append(render_stepper(m_cod.group(1)))
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
            elif comb and txt == "Exemplo completo" and secao_aberta:
                fechar_campo()
                sid = slug(txt, usados)
                corpo.append(f'<div class="caso" id="{sid}"><h4 class="caso-titulo">{inline(txt)}</h4>')
                caso_aberto = True
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
            if comb:
                m_rot = re.match(r"^\*\*(.+?)[.:]?\*\*", texto)
                rotulo = m_rot.group(1).rstrip(".:") if m_rot else None
                if em_componente and rotulo in CAMPOS:
                    fechar_campo()
                    corpo.append(f'<div class="campo campo-{CAMPOS[rotulo]}"><p>{inline(texto)}</p>')
                    campo_aberto = True
                    continue
                m_num = re.match(r"^\*\*(\d+)\.\s+(.*)$", texto)
                if m_num:
                    corpo.append(
                        f'<div class="p-passo"><span class="passo-n">{m_num.group(1)}</span>'
                        f'{render_paragrafo("**" + m_num.group(2))}</div>'
                    )
                    continue
                if re.fullmatch(r"\*\*[^*]+\*\*(\s*\([^)]*\))?", texto):  # rótulo sozinho: vira subtítulo
                    corpo.append(f'<p class="p-titulo">{inline(texto)}</p>')
                    continue
            corpo.append(render_paragrafo(texto))
        elif tipo == "quote":
            classe = "hipotese" if b[1].startswith("Acreditamos") else "citacao"
            corpo.append(f'<blockquote class="{classe}"><p>{inline(b[1])}</p></blockquote>')
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
        f'<p>{html.escape(cfg.get("cta_texto", CTA_PADRAO))}</p></div>'
        f'<a class="cta-btn" href="{url_ativ}">Abrir a atividade →</a></aside>'
    )
    if cfg.get("pratica"):
        url_p, nome_p, texto_p = cfg["pratica"]
        cta = (
            '<aside class="cta-atividade cta-pratica">'
            '<div><span class="cta-eyebrow">Em sala · prática em grupo</span>'
            f'<h3>{html.escape(nome_p)}</h3><p>{html.escape(texto_p)}</p></div>'
            f'<a class="cta-btn" href="{url_p}">Abrir a Clínica →</a></aside>'
        ) + cta
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
        nav_pratica=(f'<a class="nav-item nav-atividade nav-pratica" href="{cfg["pratica"][0]}">✎ {html.escape(cfg["pratica"][1])}</a>\n  '
                     if cfg.get("pratica") else ""),
        chave=cfg["destino"].stem,
        extras=extras_comb() if comb else "",
    )
    cfg["destino"].parent.mkdir(parents=True, exist_ok=True)
    cfg["destino"].write_text(pagina, encoding="utf-8")
    print(f"OK  {cfg['destino'].relative_to(RAIZ)}  ({palavras} palavras, ~{minutos} min)")


def extras_comb():
    """Cartão de bolso (gaveta) e dados das siglas para a explicação curta."""
    dados = {
        s: {"nome": d["nome"], "familia": CTX["familias"].get(s[0], {}).get("nome", ""), "pergunta": d["pergunta"],
            "id": d["id"], "cod": d["cod"], "classe": familia(s)}
        for s, d in CTX["siglas"].items() if s in SIGLAS_COMB
    }
    for s, (nome, desc, alvo) in MARCAS.items():
        dados[s] = {"nome": nome, "familia": "Marcação de evidência", "pergunta": desc, "id": alvo,
                    "cod": alvo[:2].upper(), "classe": familia(s)}
    js = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    return (
        '\n<button type="button" id="btn-cartao" aria-controls="cartao" aria-expanded="false">'
        '<span aria-hidden="true">▤</span> Cartão de bolso</button>'
        '\n<div id="cartao-fundo" hidden></div>'
        '\n<aside id="cartao" class="cartao-gaveta" role="dialog" aria-modal="true" aria-label="Cartão de bolso" hidden>'
        '<div class="cartao-cab"><div><span class="cartao-eyebrow">Cartão de bolso</span><strong>O passo em uma página</strong></div>'
        '<button type="button" class="cartao-fechar" aria-label="Fechar o cartão">×</button></div>'
        f'<div class="cartao-corpo" data-origem="{CTX["cartao"]}"></div></aside>'
        f'\n<script type="application/json" id="dados-siglas">{js}</script>'
    )


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
  <a class="nav-item nav-ajuda" href="../index.html#ajuda">? Como usar o portal</a>
  <a class="nav-item" href="#intro">Início</a>
  {nav}
  {nav_pratica}<a class="nav-item nav-atividade" href="{url_ativ}">✎ Ir para a atividade</a>
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

<button id="back-to-top" title="Voltar ao topo" aria-label="Voltar ao topo">&#8593;</button>{extras}
<script src="../assets/js/leitura.js"></script>
</body>
</html>
"""


if __name__ == "__main__":
    for cfg in LEITURAS:
        gerar(cfg)
