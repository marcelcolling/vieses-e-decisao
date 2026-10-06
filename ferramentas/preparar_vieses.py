"""
Copia os materiais "Conheça seus vieses" para a pasta vieses/ do portal.

O conteúdo de cada página é mantido na íntegra. O script só acrescenta:
  - o link "Voltar ao portal" no sumário lateral;
  - o salvamento automático das "Perguntas para a prática" (planilha da turma ou navegador);
  - um ajuste de impressão (as seções com animação de entrada saíam em branco no PDF);
  - a correção de uma tag </main> duplicada que existia em alguns arquivos.

Uso:
    python ferramentas/preparar_vieses.py "C:/caminho/da/pasta/com/os/html/originais"
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "vieses"

ARQUIVOS = {
    "CONHEÇA SEUS VIESES (ANCORAGEM).html": ("ancoragem", "Conheça seus vieses · Ancoragem"),
    "CONHEÇA SEUS VIESES (CONFIRMAÇÃO).html": ("confirmacao", "Conheça seus vieses · Confirmação"),
    "CONHEÇA SEUS VIESES (AVERSÃO À PERDA).html": ("aversao-a-perda", "Conheça seus vieses · Aversão à perda"),
    "CONHEÇA SEUS VIESES (DUNNING-KRUGER).html": ("dunning-kruger", "Conheça seus vieses · Dunning-Kruger"),
    "CONHEÇA SEUS VIESES (ENQUADRAMENTO).html": ("enquadramento", "Conheça seus vieses · Enquadramento"),
}

MARCA = "<!-- portal-vd -->"

CABECA = MARCA + """
<link rel="stylesheet" href="../assets/css/portal.css">
<style>
  .nav-item.vd-voltar{ color:var(--amber); font-weight:600; }
  @media print{
    .section{ opacity:1 !important; transform:none !important; }
    #sidebar, #sidebar-toggle, #overlay, #progress-bar, #back-to-top{ display:none !important; }
    .wrapper{ margin:0 auto !important; }
    .lens-panel{ display:block !important; }
    .reveal-result{ max-height:none !important; opacity:1 !important; }
  }
</style>
"""

VOLTAR = '\n  <a class="nav-item vd-voltar" href="../index.html">← Voltar ao portal</a>'


def preparar(origem: pathlib.Path):
    DESTINO.mkdir(exist_ok=True)
    for nome, (slug, titulo) in ARQUIVOS.items():
        src = origem / nome
        if not src.exists():
            print(f"!! não encontrado: {src}")
            continue
        s = src.read_text(encoding="utf-8")
        if MARCA in s:
            print(f"-- já preparado: {nome}")
            continue
        s = s.replace("</main></main>", "</main>")
        s = s.replace("</head>", CABECA + "</head>", 1)
        # link de volta logo depois do título do sumário
        i = s.find('<div class="sidebar-title">')
        j = s.find("</div>", i) + len("</div>")
        s = s[:j] + VOLTAR + s[j:]
        rodape = (
            '<script src="../assets/js/config.js"></script>\n'
            '<script src="../assets/js/portal.js"></script>\n'
            f"<script>VD.notas({{ id: 'vies-{slug}', titulo: '{titulo}' }});</script>\n"
        )
        k = s.rfind("</body>")
        s = s[:k] + rodape + s[k:]
        (DESTINO / f"{slug}.html").write_text(s, encoding="utf-8")
        print(f"OK  vieses/{slug}.html")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    preparar(pathlib.Path(sys.argv[1]))
