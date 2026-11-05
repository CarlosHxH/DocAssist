# DocAssist — assistente de documentação interna de TI (RAG local)

MVP desenvolvido para o projeto final transversal "IA Avançada para Infraestrutura, Dados
e Desenvolvimento de TI" (SESP-MT). Responde perguntas em linguagem natural sobre padrões
internos de TI (deploy, branching, nomenclatura, Docker, migrations, auditoria,
monitoramento, Portal de Acesso) usando **RAG (Retrieval-Augmented Generation) com LLM
100% local via Ollama** — nenhum dado sai da máquina onde o projeto roda.

> **Importante sobre os dados:** a pasta `corpus/` contém documentação **fictícia**,
> escrita para este MVP, inspirada na estrutura típica de um departamento de TI (ela não
> reproduz nenhum documento institucional real). Isso segue a exigência do edital de usar
> apenas dados fictícios, públicos ou expressamente autorizados.

## 1. Problema e resultado esperado

Desenvolvedores — principalmente em onboarding — perdem tempo navegando por múltiplos
documentos de wiki para responder dúvidas operacionais recorrentes ("qual o padrão de nome
de branch de hotfix?", "como funciona o deploy em produção?"). O DocAssist centraliza essas
respostas num assistente de perguntas e respostas que sempre cita a fonte.

**Critério de sucesso observável:** em um conjunto de teste de 20 perguntas
(`eval_questions.json`, 15 dentro do escopo + 5 fora do escopo/casos-limite), o assistente
deve responder corretamente e citar a fonte certa em pelo menos 80% dos casos, e recusar
responder (sem alucinar) quando a pergunta está fora do escopo da base. Rode `python
eval.py` para medir isso — o relatório é salvo em `tests/relatorio_avaliacao.md`.

## 2. Arquitetura

```
[Usuário] → app.py (CLI)
               → pergunta em linguagem natural
          rag.answer()
               1. embed(pergunta)              → ollama_client.py → Ollama /api/embeddings
                                                   (modelo all-minilm)
               2. busca vetorial top-k em memória (cosine similarity, index.json)
               3. se a melhor similaridade < limiar (0.40) → recusa responder
               4. monta prompt = instruções + trechos recuperados + pergunta
               5. generate(prompt)              → ollama_client.py → Ollama /api/generate
                                                   (modelo qwen2.5:3b)
          → resposta + citação da(s) fonte(s)
          → log da interação em logs/interactions.jsonl
```

`ingest.py` é o componente de ingestão: lê os `.md` de `corpus/`, divide em trechos por
seção (e subdivide seções longas, respeitando o limite de contexto do modelo de
embeddings), gera o embedding de cada trecho via Ollama e persiste tudo em `index.json`.

## 3. Uso efetivo de IA

- **Capacidade de IA:** RAG — embeddings para busca semântica + LLM local para gerar a
  resposta final, restrita ("grounded") ao conteúdo recuperado.
- **Por que essa capacidade:** o problema exige busca semântica (a pergunta raramente usa
  as mesmas palavras do documento) e síntese em linguagem natural — busca por palavra-chave
  simples não é suficiente; ao mesmo tempo, geração livre sem grounding poderia inventar
  políticas internas inexistentes, o que é inaceitável nesse domínio.
- **Como a saída é validada:**
  1. Toda resposta bem-sucedida deve citar um documento existente na base — verificável
     automaticamente.
  2. Limiar de similaridade de cosseno (0.40, calibrado empiricamente — ver
     `tests/calibracao_limiar.md`) — abaixo dele, o sistema recusa responder em vez de
     arriscar alucinação.
  3. Conjunto de avaliação com gabarito (`eval_questions.json` + `eval.py`), medindo
     acerto contra a fonte esperada.

## 4. Dados e integração

Corpus fictício: 9 documentos Markdown em `corpus/` (~59 trechos indexados). Nenhuma API
externa é usada — toda comunicação é local, entre o app Python e o serviço Ollama
(`http://localhost:11434`), via HTTP (`urllib`, biblioteca padrão). `rag.py` mostra
explicitamente a chamada a `embed()` e `generate()` como os dois pontos de integração com
o recurso de IA.

## 5. Como rodar

### Pré-requisitos

1. [Ollama](https://ollama.com) instalado e rodando (`ollama serve`, ou já ativo como
   serviço).
2. Baixar os dois modelos usados (uma vez só):
   ```
   ollama pull all-minilm
   ollama pull qwen2.5:3b
   ```
3. Python 3.10+ — **sem nenhuma dependência externa** (ver `requirements.txt`).

### Passo a passo

```bash
cd docassist

# 1. Gera o índice vetorial a partir de corpus/ (roda uma vez, ou de novo se o corpus mudar)
python ingest.py

# 2a. Roda o assistente via linha de comando
python app.py

# 2b. Ou roda o site de chat (abre em http://127.0.0.1:8765)
python web_server.py
```

Exemplo de pergunta: `Qual o padrão de nome para uma branch de hotfix?`

### Site de chat (web_server.py)

Interface web (`static/index.html` + `static/style.css` + `static/app.js`, sem build step
nem CDN) servida por um servidor HTTP próprio (`web_server.py`, biblioteca padrão do
Python — sem Flask/FastAPI), reaproveitando o mesmo `rag.py` usado pela CLI. O visual segue
o mesmo estilo editorial de outro projeto de referência (`mini-chat-rag`): barra lateral
fixa com a base de conhecimento e o status do modelo, área principal com sugestões de
pergunta e a conversa, fontes recuperadas em `<details>` expansíveis com o trecho completo.

Endpoints JSON: `POST /api/ask` (pergunta → resposta, fontes e latência) e `GET
/api/health` (disponibilidade real do Ollama — via um ping leve a `/api/tags`, modelos em
uso, documentos e trechos indexados). Cada resposta mostra as fontes recuperadas (título
do documento, seção e o trecho completo, expansível), a latência e um link para copiar a
resposta; perguntas sem contexto suficiente ou com falha de IA aparecem com estilo de aviso
distinto, sem alucinar. A conversa é persistida no navegador (`localStorage`), sobrevive a
recarregar a página, e pode ser limpa pelo botão "Nova conversa". A indisponibilidade do
backend/Ollama é tratada com mensagem clara em vez de travar. Interações feitas pela
interface web são gravadas no mesmo `logs/interactions.jsonl` usado pela CLI.

### Rodar a avaliação automatizada

```bash
python eval.py
```

Gera `tests/relatorio_avaliacao.md` com o resultado linha a linha e o percentual de
acerto comparado ao critério de sucesso (80%).

## 6. Cenários de teste (requisito 06)

Documentados e com evidência em `tests/`:

1. **Funcionamento esperado** — pergunta cuja resposta está no corpus → resposta correta
   com citação da fonte certa. Ex.: perguntas #1-15 de `eval_questions.json`.
2. **Caso-limite / entrada inválida** — pergunta fora do escopo do corpus, vazia ou vaga
   (perguntas #16-20) → o sistema reconhece a ausência de contexto relevante e recusa
   responder, sem alucinar.
3. **Falha/indisponibilidade da IA** — serviço Ollama fora do ar ou inacessível → o
   sistema captura o erro, mostra uma mensagem compreensível ao usuário e registra o
   evento no log, sem travar. Reproduzível apontando `ollama_client.OLLAMA_HOST` para uma
   porta inválida (ver `tests/cenario_falha_ollama.md`).

## 7. Segurança e privacidade

- Corpus 100% fictício — nenhum hostname, nome de time ou credencial reais.
- Nenhuma senha/token no código.
- Execução inteiramente local: nenhum dado sai da máquina do desenvolvedor.
- A ferramenta é somente leitura/resposta a perguntas (não executa ações sobre sistemas
  reais), portanto não há necessidade de aprovação humana para "ações" — mas a resposta
  deixa claro que é uma referência e não substitui a documentação oficial.

## 8. Erros e observabilidade

Cada interação é registrada em `logs/interactions.jsonl` com timestamp, pergunta, status
(`ok` / `sem_contexto` / `erro`), fontes citadas, scores de similaridade recuperados,
latência e mensagem de erro (quando houver). Mensagens de erro na interface são sempre em
linguagem natural compreensível, nunca um stacktrace cru.

## 9. Limitações conhecidas e próximos passos

- Corpus pequeno e fictício; não escala para documentação real sem reprocessamento e sem
  camadas adicionais de tratamento de dados sensíveis.
- Modelo local pequeno (`qwen2.5:3b`) tem qualidade de geração inferior a LLMs maiores via
  API, podendo errar nuances de fraseado mesmo com grounding; a geração também é lenta
  (dezenas de segundos por resposta em hardware sem GPU dedicada).
- RAG reduz mas não elimina o risco de alucinação; não há avaliação contínua automatizada
  (ex. métricas tipo RAGAS) além do conjunto de teste fixo incluído.
- Sem atualização incremental do índice (é preciso reexecutar `ingest.py` quando o corpus
  muda) e sem autenticação/controle de acesso — não deve ser usado com documentação
  institucional real sem essas camadas.
- Próximos passos: avaliação automatizada de qualidade de resposta, atualização
  incremental do índice, suporte a mais formatos de origem (PDF, export direto de wiki) e
  conversa multi-turno com memória (hoje cada pergunta no site/CLI é independente, sem
  histórico de conversa).

## Estrutura do projeto

```
docassist/
  corpus/                  documentação fictícia (.md) usada como base de conhecimento
  ollama_client.py         cliente HTTP mínimo para a API local do Ollama
  ingest.py                chunking + geração de embeddings + index.json
  rag.py                   núcleo do pipeline RAG (retrieval + geração + logging)
  app.py                   interface de linha de comando
  web_server.py            servidor HTTP do site de chat (stdlib, sem Flask/FastAPI)
  static/index.html        site de chat — estrutura (sem build step)
  static/style.css         site de chat — estilo
  static/app.js            site de chat — lógica (fetch, histórico, status)
  eval.py                  roda eval_questions.json e gera o relatório de validação
  eval_questions.json      conjunto de perguntas de teste com gabarito
  index.json               índice vetorial gerado por ingest.py (não versionar se o corpus mudar)
  logs/interactions.jsonl  log de cada interação (observabilidade)
  tests/                   evidências dos cenários de teste e da avaliação
```
