# Cenário de teste 3 — Falha/indisponibilidade da IA

**Objetivo:** confirmar que o DocAssist trata graciosamente a indisponibilidade do
serviço de IA local (Ollama), sem travar e com mensagem compreensível ao usuário.

## Como reproduzir

```python
import ollama_client
ollama_client.OLLAMA_HOST = "http://localhost:1"  # porta sem nenhum serviço ouvindo
import rag
r = rag.answer("Qual o padrão de nome para uma branch de hotfix?")
print(r.status, r.answer, r.error)
```

(Na aplicação real, o mesmo efeito ocorre se o comando `ollama serve` não estiver rodando,
ou se o serviço travar/ficar sem resposta.)

## Resultado observado

```
STATUS: erro
RESPOSTA: O serviço de IA local (Ollama) não está disponível no momento. Verifique se ele
está rodando (`ollama serve`) e tente novamente.
ERRO: Não foi possível falar com o Ollama em http://localhost:1/api/embeddings:
<urlopen error [WinError 10061] Nenhuma conexão pôde ser feita porque a máquina de destino
as recusou ativamente>
```

## Avaliação

- O sistema **não trava** nem lança uma exceção não tratada até o usuário.
- A mensagem exibida é em linguagem natural, compreensível por alguém não técnico.
- O detalhe técnico do erro (`error`) é preservado separadamente para fins de
  observabilidade/depuração, mas não é exposto como a resposta principal.
- O evento é registrado no log (`logs/interactions.jsonl`), com `status: "erro"`,
  permitindo auditoria posterior de quantas vezes isso ocorreu.

**Resultado: cenário ATENDIDO.**
