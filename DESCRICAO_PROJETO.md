# DocAssist — Descrição resumida do projeto

## Problema

Desenvolvedores de TI — especialmente em onboarding — gastam tempo procurando, em
múltiplos documentos de wiki interno, a resposta para dúvidas operacionais recorrentes:
qual o padrão de nome de uma branch, como funciona o processo de deploy em produção, qual
o checklist de uma migration de banco, etc. A informação existe, mas está espalhada e
exige busca manual.

## Público-alvo

Desenvolvedores e analistas de TI do órgão fictício modelado neste MVP, com foco especial
em pessoas em processo de onboarding.

## Resultado esperado / critério de sucesso

Um assistente de perguntas e respostas que, dada uma pergunta em linguagem natural,
responde corretamente citando a fonte, ou recusa responder quando a informação não está na
base (evitando alucinação). Critério observável: >= 80% de acerto em um conjunto de 20
perguntas de teste com gabarito. **Resultado medido: 20/20 (100%)** — ver
`tests/relatorio_avaliacao.md`.

## Requisitos priorizados

1. Responder perguntas sobre os padrões documentados no corpus, citando a fonte.
2. Recusar responder (sem alucinar) quando a pergunta está fora do escopo da base.
3. Rodar inteiramente local (sem enviar dados para serviços externos).
4. Registrar cada interação para fins de auditoria/observabilidade.
5. Tratar com clareza a indisponibilidade do serviço de IA.

## Arquitetura (resumo)

Pipeline RAG local: `ingest.py` converte os documentos fictícios de `corpus/` em um índice
vetorial (`index.json`, via embeddings do Ollama); `rag.py` faz a busca por similaridade de
cosseno, decide se há contexto suficiente (limiar calibrado em 0.40) e gera a resposta
final via LLM local; `app.py` é a interface de linha de comando e `web_server.py` +
`static/index.html` formam o site de chat (servidor HTTP da biblioteca padrão, sem
Flask/FastAPI); `eval.py` mede a qualidade do sistema contra um gabarito. Ver diagrama
completo e detalhes em `README.md`.

## Justificativa do uso de IA

O problema exige busca semântica (a pergunta normalmente não usa as mesmas palavras do
documento-fonte) e síntese em linguagem natural — por isso RAG (embeddings + LLM) foi
escolhido em vez de busca por palavra-chave. O LLM roda localmente (Ollama) em vez de via
API externa, para que nenhum dado saia do ambiente — decisão alinhada ao tipo de órgão que
o MVP modela (setor público), ao custo de maior latência e menor qualidade de geração que
um LLM maior via API (ver limitações no README).
