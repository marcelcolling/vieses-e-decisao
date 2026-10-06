# Portal da disciplina Vieses e Decisão

Site estático (GitHub Pages) com os conteúdos e as atividades da disciplina. As respostas dos estudantes são salvas automaticamente numa **planilha Google** do professor, por meio de um pequeno script (Google Apps Script).

## Como funciona para o estudante

1. Entra com o **nome (ou o nome do grupo)** e uma **palavra-chave**. No primeiro acesso, o portal pede para confirmar o cadastro (evita duplicatas por erro de digitação).
2. Preenche as atividades. Tudo é salvo no navegador na hora e enviado à planilha alguns segundos depois. O indicador no topo mostra "Salvo na planilha às 14:32".
3. Pode fechar e voltar de qualquer computador: entrando de novo, as respostas voltam.
4. Em grupo, todos usam o mesmo nome e a mesma palavra-chave. Se dois membros editarem a mesma atividade ao mesmo tempo, o portal avisa e pergunta qual versão manter.
5. A Aula 2 traz o comportamento-alvo da Aula 1 com um clique, e a Aula 3 traz a hipótese da Aula 2.

## O que o professor vê na planilha

| Aba | Conteúdo |
|---|---|
| **Painel** | Uma linha por estudante/grupo: turma, quando salvou cada atividade, último acesso. O nome é um link para a aba da pessoa. |
| **Uma aba por estudante/grupo** | As respostas de todas as atividades em formato legível (seção · campo · resposta). |
| `_alunos`, `_dados` (ocultas) | Base usada pelo portal. Não edite, exceto para redefinir palavra-chave (abaixo). |

As abas legíveis são atualizadas **a cada 5 minutos**. Para atualizar na hora: menu **Portal da disciplina › Atualizar abas e painel agora**.

---

## Configuração (uma vez só, cerca de 10 minutos)

### 1. Criar a planilha e o script

1. Crie uma planilha Google vazia (ex.: "Vieses e Decisão — Respostas 2026.2").
2. Menu **Extensões › Apps Script**.
3. Apague o conteúdo do arquivo `Código.gs` e cole todo o conteúdo de [`apps-script/Codigo.gs`](apps-script/Codigo.gs). Salve (ícone de disquete).
4. No seletor de funções (ao lado de "Depurar"), escolha **`configurar`** e clique em **Executar**. O Google pedirá autorização: escolha sua conta › *Avançado* › *Acessar projeto (não seguro)* › *Permitir*. (O aviso aparece porque o script é seu e não passou por verificação do Google; ele só acessa esta planilha.)

### 2. Publicar como app da Web

1. **Implantar › Nova implantação**.
2. Em "Selecionar tipo" (engrenagem), escolha **App da Web**.
3. **Executar como:** *Eu*. **Quem pode acessar:** *Qualquer pessoa*.
4. Clique em **Implantar** e copie a **URL do app da Web** (termina em `/exec`).

### 3. Ligar o portal à planilha

Abra [`assets/js/config.js`](assets/js/config.js) e cole a URL:

```js
APPS_SCRIPT_URL: 'https://script.google.com/macros/s/AKfy.../exec',
```

Publique a alteração no GitHub (pela interface web do GitHub, editando o arquivo, ou com `git commit` + `git push`). Em 1 ou 2 minutos o site já salva na planilha.

> **Se alterar o código do Apps Script depois:** use **Implantar › Gerenciar implantações › (lápis) › Versão: Nova versão**. Assim a URL continua a mesma. Uma "Nova implantação" gera outra URL.

---

## Tarefas do dia a dia

- **Estudante esqueceu a palavra-chave:** na planilha, menu *Exibir abas ocultas* › `_alunos`; apague a célula `hash_chave` da pessoa. A próxima palavra-chave que ela usar passa a valer.
- **Nova turma no mesmo semestre:** use a mesma planilha; o campo "Turma" aparece no Painel. Para separar por completo, crie outra planilha + implantação e outro repositório/pasta.
- **Sem planilha configurada:** o portal funciona em "modo local", com as respostas salvas só no navegador. Os botões "Baixar cópia (.json)" continuam disponíveis como backup em todas as atividades.

## Atualizar conteúdos

- **Leitura da Aula 1:** edite [`conteudo/material-passo-1-objetivos-e-indicadores.md`](conteudo/material-passo-1-objetivos-e-indicadores.md) e rode `python ferramentas/gerar_leitura.py`. A página em `leituras/` é regenerada com o texto integral. Para incluir outra leitura (ex.: Aula 2), acrescente uma entrada na lista `LEITURAS` do script e um link no `index.html`.
- **Conheça seus vieses:** as páginas em `vieses/` são cópias integrais dos HTML originais. Ao atualizar um original, rode `python ferramentas/preparar_vieses.py "<pasta dos originais>"` (apague antes o arquivo correspondente em `vieses/`).
- **Atividades:** `atividades/*.html`. Cada uma declara `coletar()` (o que salvar), `aplicar()` (como restaurar) e `resumo()` (como aparece na aba do estudante).

## Estrutura

```
index.html                 página inicial (trilha, vieses, login)
atividades/                ferramentas das Aulas 1, 2 e 3
leituras/                  leitura da Aula 1 (gerada a partir de conteudo/)
vieses/                    série "Conheça seus vieses"
assets/js/portal.js        sessão, salvamento automático, sincronização
assets/js/config.js        URL do Apps Script e nome da disciplina
apps-script/Codigo.gs      back-end na planilha Google
ferramentas/               scripts Python (sem dependências) para gerar páginas
```

## Privacidade

A palavra-chave é guardada na planilha apenas como *hash*, mas não é uma senha forte: oriente a turma a não usar senhas pessoais. Os dados ficam na sua conta Google. A URL do Apps Script aceita requisições de qualquer pessoa que a conheça, e cada gravação exige nome e palavra-chave corretos.
