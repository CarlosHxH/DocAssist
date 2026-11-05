# Roteiro de demonstração — DocAssist

Segue o roteiro mínimo exigido pelo edital do MVP.

## 1. Problema e público-alvo

Desenvolvedores do time de TI (especialmente em onboarding) gastam tempo procurando em
múltiplos documentos de wiki a resposta para dúvidas operacionais recorrentes. O DocAssist
centraliza isso num assistente de perguntas e respostas.

## 2. Fluxo completo funcionando

```
python ingest.py      # gera index.json a partir de corpus/ (uma vez)
python app.py          # abre a CLI interativa
Pergunta> Qual o padrão de nome para uma branch de hotfix?
```

Saída esperada: resposta objetiva citando `branching-commits-versionamento.md` e/ou
`padroes-de-nomenclatura.md` como fonte.

## 3. Onde a IA participa vs. o que é determinístico

- **Determinístico:** leitura dos arquivos `.md`, chunking por seção, cálculo de
  similaridade de cosseno (matemática pura, sem IA), decisão de recusar responder quando o
  melhor score fica abaixo do limiar (0.40), log da interação.
- **IA:** geração do embedding da pergunta e dos trechos (modelo `all-minilm`) e a síntese
  da resposta final em linguagem natural (modelo `qwen2.5:3b`), sempre restrita ao
  conteúdo recuperado.

## 4. Teste de erro/falha/entrada inadequada

Mostrar, ao vivo:
- Uma pergunta fora do escopo (`Qual a capital da França?`) → sistema recusa responder em
  vez de inventar.
- Derrubar o Ollama (ou apontar `OLLAMA_HOST` para uma porta inválida) e repetir uma
  pergunta → mensagem de erro compreensível, sem travar (ver
  `tests/cenario_falha_ollama.md`).

## 5. Decisões de arquitetura, limites de segurança e limitações

- RAG com LLM local (Ollama) em vez de API externa: nenhum dado sai da máquina, alinhado
  ao tipo de órgão modelado (setor público) — trade-off: menor qualidade de geração e
  maior latência que um LLM maior via API.
- Sem framework de orquestração (ex. LangChain): pipeline direto em ~200 linhas de Python
  puro, mais fácil de explicar e depurar; o edital não exige grafos/roteamento.
- Corpus fictício, nunca dados institucionais reais — ver seção "Segurança e privacidade"
  do README.
- Limitações: corpus pequeno, modelo local lento, sem avaliação contínua automatizada, sem
  atualização incremental do índice, sem autenticação — detalhadas no README.
