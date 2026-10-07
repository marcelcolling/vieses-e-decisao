"""Servidor de teste: serve o portal e imita o Apps Script (entrar/salvar) em /api.
Usado por rodar_testes.ps1. Mantenha as regras de entrar/salvar iguais às de apps-script/Codigo.gs."""
import hashlib, http.server, json, pathlib, time, unicodedata, sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = pathlib.Path(__file__).parent
ALUNOS, DADOS = {}, {}


def norm(n):
    s = " ".join(str(n or "").split())
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.lower()


def h(i, c):
    return hashlib.sha256(f"sal|{i}|{c.strip().lower()}".encode()).hexdigest()


def entrar(r):
    i = norm(r.get("nome"))
    c = str(r.get("chave", "")).strip()
    if len(c) < 4:
        return {"ok": False, "erro": "chave curta"}
    if i not in ALUNOS:
        if not r.get("criar"):
            return {"ok": False, "naoEncontrado": True}
        ALUNOS[i] = {"nome": " ".join(r["nome"].split()), "turma": r.get("turma", ""), "hash": h(i, c)}
        return {"ok": True, "criado": True, "aluno": {"id": i, "nome": ALUNOS[i]["nome"], "turma": ALUNOS[i]["turma"]}, "dados": {}}
    a = ALUNOS[i]
    if a["hash"] != h(i, c):
        return {"ok": False, "chaveIncorreta": True, "erro": "Palavra-chave incorreta"}
    dados = {f: {"titulo": v["titulo"], "atualizado": v["atualizado"], "data": json.loads(v["json"])}
             for (ii, f), v in DADOS.items() if ii == i}
    return {"ok": True, "aluno": {"id": i, "nome": a["nome"], "turma": a["turma"]}, "dados": dados}


def salvar(r):
    i = norm(r.get("nome"))
    a = ALUNOS.get(i)
    if not a or a["hash"] != h(i, str(r.get("chave", ""))):
        return {"ok": False, "sessaoInvalida": True, "erro": "sessão inválida"}
    f = r["ferramenta"]
    js = json.dumps(r.get("data"), separators=(",", ":"), ensure_ascii=False)
    ex = DADOS.get((i, f))
    if ex:
        if ex["json"] == js:
            return {"ok": True, "atualizado": ex["atualizado"], "semMudanca": True}
        base = r.get("base")
        if not r.get("forcar") and (base is None or ex["atualizado"] > base):
            return {"ok": False, "conflito": True, "atualizado": ex["atualizado"], "data": json.loads(ex["json"])}
    agora = int(time.time() * 1000)
    DADOS[(i, f)] = {"titulo": r.get("titulo"), "atualizado": agora, "json": js, "resumo": r.get("resumo")}
    return {"ok": True, "atualizado": agora}


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def log_message(self, *a):
        pass

    def _json(self, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/assets/js/config.js"):
            b = b"window.VD_CONFIG={APPS_SCRIPT_URL:'/api',NOME_DISCIPLINA:'Vieses e Decis\\u00e3o'};"
            self.send_response(200); self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b); return
        if self.path.startswith("/__teste.html"):
            b = (SCRATCH / "teste_ponta_a_ponta.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b); return
        if self.path.startswith("/__estado"):
            return self._json({"alunos": ALUNOS, "dados": {f"{i}|{f}": v for (i, f), v in DADOS.items()}})
        if self.path.startswith("/__mexer"):  # simula outro membro do grupo salvando
            for (i, f), v in DADOS.items():
                if f == "aula1":
                    d = json.loads(v["json"]); d["equipe"] = "ALTERADO POR OUTRO"
                    v["json"] = json.dumps(d, separators=(",", ":"), ensure_ascii=False)
                    v["atualizado"] = int(time.time() * 1000) + 5000
            return self._json({"ok": True})
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        r = json.loads(self.rfile.read(n) or b"{}")
        if self.path.startswith("/api"):
            return self._json(entrar(r) if r.get("acao") == "entrar" else salvar(r) if r.get("acao") == "salvar" else {"ok": False})
        self.send_response(404); self.end_headers()


http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8766), H).serve_forever()
