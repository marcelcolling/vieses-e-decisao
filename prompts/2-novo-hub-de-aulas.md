Quero criar um novo portal de disciplina (hub de aulas) no mesmo estilo do portal "Vieses e Decisão", que já construímos e está em uso.

## Referência
Use `C:\Users\LENOVO\vieses-e-decisao` como implementação de referência. Comece lendo o `CLAUDE.md` de lá: ele descreve a arquitetura, o contrato das atividades, a integração com a planilha, as armadilhas já resolvidas e como testar. Reaproveite o núcleo pronto e testado em vez de reescrever:
- `assets/js/portal.js` e `assets/css/portal.css`: sessão com nome + palavra-chave, salvamento automático no navegador e na planilha, conflito em grupo, botão "Salvar respostas", guia "Como usar", caixas de texto que crescem;
- `apps-script/Codigo.gs`: back-end na planilha Google, com Painel, uma aba por estudante e menu de remoção;
- `assets/css/leitura.css`, `assets/js/leitura.js` e `ferramentas/gerar_leitura.py`: leituras geradas a partir de Markdown, com o texto íntegro;
- `ferramentas/testes/`: teste de ponta a ponta com Apps Script simulado;
- `publicar.ps1`: cria o repositório no GitHub e ativa o GitHub Pages (`git` e `gh` já estão instalados e autenticados).
O novo projeto deve ser independente: repositório, planilha e implantação do Apps Script próprios. Não altere nada do portal "Vieses e Decisão".

## O novo projeto
- **Nome da disciplina/projeto:** [ ]
- **Curso/programa e público:** [ex.: MBA em Gestão, turma 2027.1]
- **Nome do repositório e da pasta:** [ex.: gestao-de-projetos → C:\Users\LENOVO\gestao-de-projetos]
- **Estrutura das aulas/etapas:** [quantas, nome e objetivo de cada uma, qual método organiza a trilha (se houver)]
- **Materiais de leitura:** [caminhos dos arquivos .md/.html/.docx/.pdf e em qual aula entra cada um. Manter o texto íntegro? sim/não]
- **Atividades/ferramentas:** [caminhos dos HTML existentes OU descrição do que o estudante preenche em cada aula; se uma atividade aproveita dados da anterior]
- **Material complementar:** [ex.: série de leituras curtas, vídeos, links, e onde destacar]
- **Trabalho individual ou em grupo:** [ ]
- **Identidade visual:** [use a mesma do "Vieses e Decisão" OU descreva/anexe as cores, fontes e um HTML de referência]
- **Arquivos que são só referência (não publicar):** [ ]

## Como quero que você conduza
1. Leia os materiais e me apresente um plano curto (estrutura de páginas, ids das atividades, o que será reaproveitado, o que é novo) antes de construir. Pergunte só o que for decisão minha.
2. Construa reaproveitando o núcleo. Ids de atividade estáveis desde o início (`aula1`, `aula2`...). Todo texto do usuário escapado. Atividades com `coletar`, `aplicar` e `resumo` legível para a planilha.
3. Leituras com texto íntegro: confira por script e me diga o resultado. Página inicial com trilha visual, distinção clara entre leitura e atividade, guia de uso na barra superior e conteúdo aproveitando a largura da tela.
4. Valide antes de publicar: capturas no Edge headless (1366px e cerca de 520px) e o teste de ponta a ponta adaptado às novas atividades, sem falhas.
5. Publique com `publicar.ps1`, confira o site no ar e me passe o passo a passo para eu criar a planilha e implantar o Apps Script (Extensões › Apps Script › colar › executar `configurar` › Implantar como App da Web, "Executar como: Eu", "Qualquer pessoa"). Quando eu enviar a URL `/exec`, atualize o `config.js`, publique e teste contra a planilha real com um usuário "Teste (apagar)", lendo a planilha pelo conector do Drive.
6. Crie um `CLAUDE.md` no novo projeto, no mesmo formato do de referência, e um `README.md` para mim (professor).
