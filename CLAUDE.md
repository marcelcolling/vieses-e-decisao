# Portal "Vieses e Decisão": guia para sessões do Claude

Portal de uma disciplina de pós-graduação (Pós em Liderança, Biopark). Os estudantes leem materiais e preenchem atividades, e as respostas vão para uma planilha Google do professor. **O portal está em uso por uma turma real:** não quebre o salvamento nem os dados já gravados.

## Onde está cada coisa

| Item | Local |
|---|---|
| Repositório local | `C:\Users\LENOVO\vieses-e-decisao` (git, branch `main`) |
| GitHub | https://github.com/marcelcolling/vieses-e-decisao (público) |
| Site (GitHub Pages) | https://marcelcolling.github.io/vieses-e-decisao/ (publica sozinho a cada `git push`, cerca de 1 min) |
| Planilha de respostas | "PÓS ECONOMIA COMPORTAMENTAL (BPK)", id `16SWOxzkKOjpWdomdBhvd7ZH7pXJy8QRQFTHz6EMit0g` (dá para ler pelo conector do Google Drive) |
| URL do Apps Script | em `assets/js/config.js` |
| Originais do professor (md, html, pptx) | `C:\Users\LENOVO\OneDrive - Biopark Educação\Documentos\BIOPARK\[2026.2] PÓS LIDERANÇA` |

## Arquitetura (site estático, sem build de JS)

```
index.html                    home: hero + cartão de sessão, faixa "Conheça seus vieses", trilha de 5 etapas
atividades/aula-N-*.html      uma ferramenta por aula (CSS e JS próprios + portal.js)
leituras/*.html               GERADO por ferramentas/gerar_leitura.py a partir de conteudo/*.md (não editar à mão)
vieses/*.html                 GERADO por ferramentas/preparar_vieses.py a partir dos HTML originais (conteúdo íntegro)
assets/js/portal.js           núcleo: sessão, login, salvamento automático, sincronização, conflito, barra superior, guia de uso, auto-altura de textarea
assets/js/config.js           APPS_SCRIPT_URL, NOME_DISCIPLINA, PROGRAMA
assets/css/portal.css         componentes compartilhados (prefixo vd-, variável --vd-largura: 1200px)
assets/css/leitura.css        layout das leituras (sidebar + texto)
apps-script/Codigo.gs         back-end na planilha (doPost entrar/salvar, abas legíveis, Painel, menu)
ferramentas/testes/           teste de ponta a ponta com Apps Script simulado (rodar_testes.ps1)
README.md                     instruções para o professor
```

## Como funciona o salvamento (não alterar sem necessidade)

- O estudante entra com **nome + palavra-chave** (`VD.entrar`). O id é o nome normalizado (minúsculas, sem acento). A palavra-chave é guardada como hash.
- Cada página de atividade chama `VD.ferramenta({ id, titulo, crumb, coletar, aplicar, resumo, infoImpressao })`:
  - `coletar()` devolve o estado da página como objeto JSON. O salvamento automático compara esse resultado com a última versão para saber se algo mudou.
  - `aplicar(dados|null)` restaura a tela a partir dos dados (com `null`, deixa o estado inicial vazio).
  - `resumo(dados)` devolve `[[seção, campo, resposta], ...]`, o formato que aparece legível na aba do estudante na planilha.
- O portal grava no `localStorage` na hora e envia para o Apps Script (`acao: 'salvar'`) alguns segundos depois. Há detecção de conflito por timestamp (`base`) para grupos.
- Qualquer elemento com o atributo `data-vd-salvar` vira o botão "Salvar respostas" (envio imediato).
- As anotações das "Perguntas para a prática" dos vieses usam `VD.notas({ id: 'vies-<slug>', titulo })`.
- **Ids existentes não podem mudar** (`aula1`, `aula2`, `aula3`, `vies-ancoragem`, `vies-confirmacao`, `vies-aversao-a-perda`, `vies-dunning-kruger`, `vies-enquadramento`). Também não podem mudar as chaves já usadas em `coletar()`. As respostas já salvas dependem disso. Para mudar a estrutura de uma atividade, mantenha `aplicar()` compatível com os dados antigos.
- O JSON de exportação/importação foi removido de propósito. Não reintroduzir.

## Receitas

### Nova leitura (a partir de Markdown)
1. Copie o `.md` para `conteudo/`.
2. Acrescente uma entrada em `LEITURAS` no `ferramentas/gerar_leitura.py` (selo, título curto, tag, base, aula, atividade relacionada). Se o documento tiver estruturas novas (rótulos de destaque, partes, exemplos), ajuste `CALLOUTS` ou o parser.
3. Rode `python ferramentas/gerar_leitura.py`.
4. **Confira a integridade:** compare as palavras do `.md` com o texto visível do HTML (difflib sobre tokens `\w+`). Só podem faltar os números das listas numeradas, que viram estilo visual.
5. Coloque o cartão `rec rec-leitura` na etapa certa da trilha, em `index.html`.

### Nova atividade (ex.: Aula 4)
1. Crie `atividades/aula-4-*.html` partindo de uma atividade existente. Mantenha o padrão visual (hero roxo, `passo` numerado, callouts, `hipotese-box`), o CSS extra do portal (`.page` com `--vd-largura`, `.btn-salvar`) e a barra de ações (`[data-vd-salvar]` + Imprimir).
2. Implemente `coletar`, `aplicar` e `resumo`. Escape todo texto do usuário que entrar em `innerHTML` com `VD.esc`. Use o id `aula4`.
3. Se a atividade continua a anterior, crie um botão "Trazer da Aula N" lendo `VD.dados('aulaN')` (ver Aulas 2 e 3).
4. Na home: troque a etapa "futura" por um cartão ativo com `rec rec-atividade` e `data-ferramenta="aula4"`, e inclua a aula no array `ATIVIDADES` do script da home.
5. No `Codigo.gs`, `montarPainel()` tem colunas fixas para as Aulas 1 a 3: acrescente a coluna da nova aula (`q(por.aula4)`). A ordem das abas por estudante vem de `ORDEM`.
6. Acrescente verificações da nova atividade em `ferramentas/testes/teste_ponta_a_ponta.html`.

### Novo material "Conheça seus vieses"
O HTML original fica na pasta do OneDrive. Acrescente o arquivo em `ARQUIVOS` no `ferramentas/preparar_vieses.py` e rode `python ferramentas/preparar_vieses.py "<pasta dos originais>"` (o script pula páginas já preparadas: apague antes o `.html` correspondente em `vieses/` para regenerar). Depois, inclua o cartão na `.vieses-linha` da home. O conteúdo deve continuar idêntico ao original: confira com o mesmo teste de integridade.

### Mudanças no Apps Script
Não há como publicar o Apps Script por aqui: o professor precisa colar o `Codigo.gs` novo no editor (Extensões › Apps Script), salvar e ir em **Implantar › Gerenciar implantações › lápis › Versão: Nova versão**. Assim a URL se mantém. Se ele criar uma implantação nova, a URL muda: atualize `config.js` e publique. Funções executadas pelo gatilho de 5 minutos (abas legíveis e Painel) usam o código salvo mesmo sem nova versão; `doPost` só muda com nova versão.

## Armadilhas já encontradas

- **Planilha em pt-BR:** fórmulas gravadas por `setValues` falham (o separador é `;`). Não gravar fórmulas; para links, usar `RichTextValue`. Todo texto passa por `texto()`, que prefixa `'` em valores que começam com `= + - @`. Só o formato `@` não basta.
- **Edge headless** (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`): rode com `Start-Process ... -PassThru` e `WaitForExit(40000)`, porque às vezes trava. A largura mínima real é cerca de 500px: capturas com `--window-size` menor saem cortadas, não é bug do layout. Use `--virtual-time-budget` e `--screenshot` ou `--dump-dom`.
- **PowerShell 5.1:** depois de instalar algo, recarregue o PATH com `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")`. O `git` e o `gh` já estão instalados e autenticados (`gh auth setup-git` feito).
- Logo depois de uma implantação nova, o Apps Script pode devolver 404 ou uma página HTML por alguns minutos. O portal trata isso: guarda no navegador e tenta de novo.
- Arquivos sem BOM: gravar com `New-Object Text.UTF8Encoding $false`.

## Como validar antes de publicar

1. `python -m http.server 8765` na raiz e capturas com o Edge headless em 1366px e 520px: home, a página alterada e o celular.
2. `.\ferramentas\testes\rodar_testes.ps1`: precisa terminar com `FAIL/ERRO: 0`. Ele usa um Apps Script simulado (`servidor_simulado.py`), que precisa seguir as mesmas regras de `Codigo.gs`.
3. Se mexeu no back-end ou na URL: teste contra o Apps Script real com um usuário chamado "Teste ... (apagar)" e leia a planilha pelo conector do Drive para conferir as abas. Depois, peça ao professor para remover o usuário de teste pelo menu **Portal da disciplina › Remover um estudante ou grupo…**.
4. `git add -A; git commit -m "..."; git push` e confirme no site publicado (cache: `?x=aleatório`).

## Identidade visual

Roxo `#402C4F` / roxo escuro `#2C1E37`, azul `#455066`, papel `#FCFCFA` / `#F2EFEA` / `#EFEEE7`, amarelo `#EFB93C` (tinta `#5B4212`), texto `#2A2432`. Títulos em **Fraunces** (com itálico nos subtítulos), corpo em **Inter**. Elementos recorrentes: selo-pílula com borda amarela, eyebrow em caixa alta com ponto amarelo, cartões arredondados (14 a 20px), círculos decorativos com borda amarela translúcida, leitura em cartão claro e atividade em roxo sólido. O professor quer o texto aproveitando a largura da tela (não estreito) e caixas de texto grandes.

## Pendências conhecidas

- A Aula 2 tem uma leitura pronta em Markdown (`aula-2-leitura-com-b-diagnostico-barreiras.md`) e em HTML (`AULA 02 - MATERIAL DE LEITURA.html`) na pasta do OneDrive, ainda não publicada no portal.
- A Aula 4 (plano de aplicação) e as mentorias aparecem como "Em breve".
- Erros de digitação nos originais dos vieses, mantidos por fidelidade: "não não vai te proteger" e "Esse é o contexto é um contexto" (Ancoragem).
