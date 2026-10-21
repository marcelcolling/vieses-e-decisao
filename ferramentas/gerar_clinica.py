"""
Gera os dados da Clínica de diagnóstico (Aula 2) e, se pedido, o gabarito cifrado.

Uso (na pasta do repositório):
    python ferramentas/gerar_clinica.py
        Lê conteudo/clinica-aula-2.md (Parte E do material do Passo 2) e grava
        atividades/clinica-dados.js. O gabarito já existente não é tocado.

    python ferramentas/gerar_clinica.py --gabarito "<guia do professor.md>" --chave <palavra>
        Também lê as seções 4, 5 e 6 do guia do professor (fora do repositório)
        e grava atividades/clinica-gabarito.js, cifrado com AES-GCM a partir da
        palavra-chave (PBKDF2-SHA256). O texto do gabarito e a palavra-chave
        NUNCA entram no repositório: o site é público.
        Requer o pacote "cryptography" (python -m pip install --user cryptography).

O texto do .md é mantido na íntegra: o script só separa as partes (casos,
dossiês, cartas) para a página montar abas e cartões.
"""
import argparse
import base64
import html
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gerar_leitura as gl  # noqa: E402  (reaproveita o leitor de blocos e a conversão de negrito/itálico)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / "conteudo" / "clinica-aula-2.md"
DESTINO_DADOS = RAIZ / "atividades" / "clinica-dados.js"
DESTINO_GABARITO = RAIZ / "atividades" / "clinica-gabarito.js"
ITERACOES = 250000

inline = gl.inline


# ---------------------------------------------------------------- utilidades
def secoes(linhas, padrao):
    """Divide as linhas em {chave: [linhas]} a cada título que casa com o padrão."""
    out, atual = {}, None
    for l in linhas:
        m = re.match(padrao, l.strip())
        if m:
            atual = m.group(1)
            out[atual] = {"titulo": m.group(2).strip(), "linhas": []}
            continue
        if atual:
            out[atual]["linhas"].append(l)
    return out


def lista_blocos(linhas):
    return [b for b in gl.blocos(linhas) if b[0] != "hr"]


def tabela(linhas_tab):
    cab = gl.celulas(linhas_tab[0])
    corpo = [gl.celulas(l) for l in linhas_tab[1:] if not re.fullmatch(r"\|?[\s:\-|]+\|?", l)]
    return cab, corpo


def html_tabela(linhas_tab, classe="tab"):
    cab, corpo = tabela(linhas_tab)
    out = [f'<div class="tab-wrap"><table class="{classe}">']
    if any(cab):
        out.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cab) + "</tr></thead>")
    out.append("<tbody>")
    for linha in corpo:
        out.append("<tr>" + "".join(
            f'<td data-label="{html.escape(gl.texto_puro(cab[j]) if j < len(cab) else "", quote=True)}">{inline(c)}</td>'
            for j, c in enumerate(linha)) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def html_bloco(b):
    tipo = b[0]
    if tipo == "p":
        return f"<p>{inline(b[1])}</p>"
    if tipo == "ul":
        return "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + "</ul>"
    if tipo == "ol":
        return '<ol class="num">' + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + "</ol>"
    if tipo == "quote":
        return f'<blockquote class="citacao"><p>{inline(b[1])}</p></blockquote>'
    if tipo == "table":
        return html_tabela(b[1])
    if tipo == "h":
        return f"<h4>{inline(b[2])}</h4>"
    raise ValueError(f"bloco inesperado: {b}")


def html_blocos(bs):
    return "".join(html_bloco(b) for b in bs)


def exigir(cond, msg):
    if not cond:
        sys.exit("ERRO: " + msg + " (o formato do .md mudou?)")


# ---------------------------------------------------------------- material do estudante (Parte E)
def ler_material():
    md = FONTE.read_text(encoding="utf-8")
    linhas = md.splitlines()
    titulo = re.match(r"^# PARTE E:\s*(.+)$", linhas[0].strip())
    exigir(titulo, "primeira linha deve ser '# PARTE E: ...'")
    sec = secoes(linhas, r"^## (E\d)\.\s+(.+)$")
    exigir(sorted(sec) == [f"E{i}" for i in range(1, 8)], "seções E1 a E7")
    dados = {"titulo": titulo.group(1), "secoes": {k: v["titulo"] for k, v in sec.items()}}

    # E1
    b = lista_blocos(sec["E1"]["linhas"])
    exigir([x[0] for x in b] == ["p", "table", "p"], "E1: parágrafo, tabela, parágrafo")
    cab, corpo = tabela(b[1][1])
    dados["e1"] = {"intro": html_bloco(b[0]), "cab": [inline(c) for c in cab],
                   "rodadas": [[inline(c) for c in l] for l in corpo], "papeis": html_bloco(b[2])}

    # E2
    b = lista_blocos(sec["E2"]["linhas"])
    exigir(len(b) == 1 and b[0][0] == "ol", "E2: lista numerada")
    dados["regras"] = [inline(x) for x in b[0][1]]

    # E3
    b = lista_blocos(sec["E3"]["linhas"])
    casos = []
    for x in b[1:]:
        if x[0] != "p":
            continue
        m = re.match(r"^\*\*Caso (\d)\.\*\*\s+\*(.+?)\*\s+(.+)$", x[1])
        exigir(m, "E3: caso no formato '**Caso N.** *comportamento.* texto'")
        casos.append({"n": int(m.group(1)), "comportamento": inline(m.group(2)), "texto": inline(m.group(3))})
    exigir(len(casos) == 6 and b[-1][0] == "table", "E3: seis casos e a tabela de votos")
    cab, _ = tabela(b[-1][1])
    dados["r1"] = {"intro": html_bloco(b[0]), "casos": casos, "cab": [inline(c) for c in cab]}

    # E4: parte geral e dossiês
    linhas_e4 = sec["E4"]["linhas"]
    i_dos = next(i for i, l in enumerate(linhas_e4) if l.startswith("### Dossiê"))
    b = lista_blocos(linhas_e4[:i_dos])
    exigir([x[0] for x in b] == ["p", "ol", "p", "p", "ol", "quote", "p"], "E4: estrutura da parte geral")
    dados["r2"] = {
        "intro": html_bloco(b[0]), "estrutura": [inline(x) for x in b[1][1]], "mural": html_bloco(b[2]),
        "passo_a_passo": html_bloco(b[3]), "etapas": [inline(x) for x in b[4][1]],
        "aviso": inline(b[5][1]), "fechamento": html_bloco(b[6]), "dossies": [],
    }
    for n, d in sorted(secoes(linhas_e4[i_dos:], r"^### Dossiê (\d):\s+(.+)$").items()):
        m = re.match(r"^(.+?)\s+\((.+)\)$", d["titulo"])
        b = lista_blocos(d["linhas"])
        exigir(b[0][0] == "p" and b[1][0] == "table" and b[3][0] == "ol", f"Dossiê {n}: caso, cabeçalho e passos")
        _, linhas_cab = tabela(b[1][1])
        exigir(gl.texto_puro(b[2][1]).startswith("Os passos") and gl.texto_puro(b[4][1]).startswith("Os dados"), f"Dossiê {n}: rótulos")
        # cartas: linha de cabeçalho "**1A** · `TIPO` · fonte" seguida do texto (sem linha em branco entre eles)
        cartas, ls = [], d["linhas"]
        for i, l in enumerate(ls):
            mh = re.match(r"^\*\*(\d[A-Z])\*\* · `([^`]+)`(?: · (.+))?$", l.strip())
            if not mh:
                continue
            texto = []
            for l2 in ls[i + 1:]:
                if not l2.strip():
                    break
                texto.append(l2.strip())
            exigir(texto, f"Dossiê {n}: texto da carta {mh.group(1)}")
            cartas.append({"id": mh.group(1), "tipo": mh.group(2), "fonte": inline(mh.group(3) or ""),
                           "texto": inline(" ".join(texto))})
        exigir(len(cartas) == 5, f"Dossiê {n}: cinco cartas")
        exigir(len(b[3][1]) == 5, f"Dossiê {n}: cinco passos")
        dados["r2"]["dossies"].append({
            "n": int(n), "titulo": inline(m.group(1) if m else d["titulo"]), "publico": inline(m.group(2)) if m else "",
            "caso": html_bloco(b[0]), "cabecalho": [[inline(c) for c in l] for l in linhas_cab],
            "rotulo_passos": inline(b[2][1]), "passos": [inline(x) for x in b[3][1]],
            "rotulo_dados": inline(b[4][1]), "cartas": cartas,
        })
    exigir(len(dados["r2"]["dossies"]) == 4, "quatro dossiês")

    # E5, E6, E7
    b = lista_blocos(sec["E5"]["linhas"])
    exigir(all(x[0] == "p" for x in b) and len(b) == 4, "E5: quatro parágrafos")
    dados["r3"] = [inline(x[1]) for x in b]
    b = lista_blocos(sec["E6"]["linhas"])
    exigir([x[0] for x in b] == ["p", "ol", "p"], "E6: parágrafo, lista, parágrafo")
    dados["r4"] = {"intro": html_bloco(b[0]), "itens": [inline(x) for x in b[1][1]], "fim": html_bloco(b[2])}
    b = lista_blocos(sec["E7"]["linhas"])
    exigir([x[0] for x in b] == ["p", "table"], "E7: parágrafo e tabela")
    cab, corpo = tabela(b[1][1])
    dados["ficha"] = {"cabecalho": inline(b[0][1]), "cab": [inline(c) for c in cab],
                      "linhas": [[inline(c) for c in l] for l in corpo]}
    return dados


# ---------------------------------------------------------------- gabarito (guia do professor)
SIGLAS = ("CF", "CP", "OF", "OS", "MR", "MA", "F", "L", "RUÍDO")


def ler_passos(txt):
    t = gl.texto_puro(txt).strip().lower()
    if t in ("—", "-", ""):  # carta que fica no baralho: não tem passo
        return []
    if t.startswith("todo"):
        return ["todo"]
    if t.startswith("fora"):
        return ["fora"]
    m = re.fullmatch(r"(\d+) a (\d+)", t)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    nums = [int(x) for x in re.findall(r"\d+", t)]
    exigir(nums, f"passo do gabarito não reconhecido: {txt}")
    return nums


def ler_marca(txt):
    t = gl.texto_puro(txt)
    m = re.fullmatch(r"\s*(CF|CP|OF|OS|MR|MA|F|L|RUÍDO)\s*(?:/\s*○\s*(CF|CP|OF|OS|MR|MA|F|L|RUÍDO))?\s*", t)
    exigir(m, f"marcação do gabarito não reconhecida: {txt}")
    return m.group(1), m.group(2) or ""


def ler_degrau(txt):
    t = gl.texto_puro(txt).lower()
    for chave, prefixo in (("terceiros", "ouvi de terceiros"), ("quem", "ouvi de quem"), ("suponho", "suponho"), ("vi", "vi")):
        if t.startswith(prefixo):
            return chave
    sys.exit(f"ERRO: degrau não reconhecido: {txt}")


def ler_gabarito(caminho):
    md = pathlib.Path(caminho).read_text(encoding="utf-8")
    sec = secoes(md.splitlines(), r"^## (\d+)\.\s+(.+)$")
    exigir({"4", "5", "6"} <= set(sec), "guia com as seções 4, 5 e 6")
    g = {"titulos": {k: sec[k]["titulo"] for k in ("4", "5", "6")}}

    # 4. Rodada 1
    b = lista_blocos(sec["4"]["linhas"])
    exigir(b[0][0] == "table", "seção 4 começa pela tabela")
    cab, corpo = tabela(b[0][1])
    casos = []
    for l in corpo:
        n = int(re.match(r"\*\*(\d)\.", l[0]).group(1))
        casos.append({"n": n, "principal": gl.texto_puro(l[1]).strip(), "celulas": [inline(c) for c in l]})
    g["r1"] = {"cab": [inline(c) for c in cab], "casos": casos, "depois": html_blocos(b[1:])}

    # 5. Rodada 2
    linhas5 = sec["5"]["linhas"]
    i_dos = next(i for i, l in enumerate(linhas5) if l.startswith("### Dossiê"))
    g["r2"] = {"intro": html_blocos(lista_blocos(linhas5[:i_dos])), "dossies": []}
    for n, d in sorted(secoes(linhas5[i_dos:], r"^### Dossiê (\d):\s+(.+)$").items()):
        b = lista_blocos(d["linhas"])
        i_tab = next(i for i, x in enumerate(b) if x[0] == "table")
        cab, corpo = tabela(b[i_tab][1])
        exigir(gl.texto_puro(cab[0]) == "Carta", f"gabarito do Dossiê {n}: tabela de cartas")
        # colunas pelo nome: Carta | Mural? | Passo | Barreira | Degrau | Por que é essa barreira
        nomes = [gl.texto_puro(c).strip().lower() for c in cab]
        col = lambda inicio: next((j for j, c in enumerate(nomes) if c.startswith(inicio)), None)
        jm, jp, jb, jd, jq = col("mural"), col("passo"), col("barreira"), col("degrau"), col("por que")
        exigir(None not in (jm, jp, jb, jd, jq), f"gabarito do Dossiê {n}: colunas Mural?, Passo, Barreira, Degrau e Por que")
        cartas = []
        for l in corpo:
            b1, b2 = ler_marca(l[jb])
            cartas.append({"id": gl.texto_puro(l[0]).strip(), "sobe": gl.texto_puro(l[jm]).strip().lower().startswith("sobe"),
                           "passo": inline(l[jp]), "passos": ler_passos(l[jp]), "b1": b1, "b2": b2,
                           "degrau": ler_degrau(l[jd]), "degrau_txt": inline(l[jd]), "porque": inline(l[jq]),
                           "celulas": [inline(c) for c in l]})
        exigir(len(cartas) == 5 and sum(c["sobe"] for c in cartas) == 3, f"gabarito do Dossiê {n}: 5 cartas, 3 sobem ao mural")
        resto = b[i_tab + 1:]
        i_dec = next(i for i, x in enumerate(resto) if x[0] == "table")
        _, dec = tabela(resto[i_dec][1])
        decisao = {}
        for l in dec:
            rot = gl.texto_puro(l[-1]).strip().lower()
            if rot in ("principal", "secundária"):
                decisao[rot] = gl.texto_puro(l[0]).strip()
        i_hip = next(i for i, x in enumerate(resto) if x[0] == "p" and gl.texto_puro(x[1]).startswith("Hipótese-modelo"))
        exigir(resto[i_hip + 1][0] == "quote", f"gabarito do Dossiê {n}: hipótese-modelo em citação")
        depois = resto[i_hip + 2:]
        g["r2"]["dossies"].append({
            "n": int(n), "titulo": inline(d["titulo"]), "antes": html_blocos(b[:i_tab]), "cab": [inline(c) for c in cab],
            "cartas": cartas, "resultado": html_blocos(resto[:i_dec]), "decisao_tabela": html_bloco(resto[i_dec]),
            "decisao": decisao, "apos_decisao": html_blocos(resto[i_dec + 1:i_hip]),
            "hipotese": inline(resto[i_hip + 1][1]), "rotulo_hipotese": inline(resto[i_hip][1]),
            "depois": html_blocos(depois),
        })
    exigir(len(g["r2"]["dossies"]) == 4, "gabarito com quatro dossiês")

    # 6. Pontuação e erros
    g["pontuacao"] = html_blocos(lista_blocos(sec["6"]["linhas"]))
    return g


def cifrar(dados, chave):
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        sys.exit("ERRO: instale o pacote: python -m pip install --user cryptography")
    sal, iv = os.urandom(16), os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITERACOES)
    k = kdf.derive(chave.strip().lower().encode("utf-8"))
    ct = AESGCM(k).encrypt(iv, json.dumps(dados, ensure_ascii=False).encode("utf-8"), None)
    b64 = lambda x: base64.b64encode(x).decode("ascii")
    return {"v": 1, "iter": ITERACOES, "sal": b64(sal), "iv": b64(iv), "dados": b64(ct)}


def gravar_js(destino, nome, obj, comentario):
    js = json.dumps(obj, ensure_ascii=False, indent=None, separators=(",", ":")).replace("</", "<\\/")
    destino.write_text(f"/* {comentario} */\nwindow.{nome} = {js};\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gabarito", help="caminho do guia do professor (.md), fora do repositório")
    ap.add_argument("--chave", help="palavra-chave que abre o gabarito (não fica registrada)")
    a = ap.parse_args()

    dados = ler_material()
    gravar_js(DESTINO_DADOS, "CLINICA", dados,
              "Gerado por ferramentas/gerar_clinica.py a partir de conteudo/clinica-aula-2.md. Não edite à mão.")
    print(f"OK  {DESTINO_DADOS.relative_to(RAIZ)}")

    if a.gabarito:
        exigir(a.chave, "informe --chave junto com --gabarito")
        exigir(RAIZ not in pathlib.Path(a.gabarito).resolve().parents, "o guia do professor deve ficar fora do repositório")
        gab = ler_gabarito(a.gabarito)
        gravar_js(DESTINO_GABARITO, "CLINICA_GABARITO", cifrar(gab, a.chave),
                  "Gabarito da Clínica, cifrado (AES-GCM). Gerado por ferramentas/gerar_clinica.py. Não edite à mão.")
        print(f"OK  {DESTINO_GABARITO.relative_to(RAIZ)}  (cifrado)")
