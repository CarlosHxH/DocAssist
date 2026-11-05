"""Interface de linha de comando do DocAssist: pergunte sobre os padrões internos de TI
(documentação fictícia em corpus/) e receba uma resposta grounded, com citação da fonte.

Uso:
    python app.py
"""

from __future__ import annotations

import sys

import rag


def main() -> None:
    try:
        chunks = rag.load_index()
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)

    print("DocAssist — assistente de documentação interna de TI (digite 'sair' para encerrar)")
    print(f"Base carregada: {len(chunks)} trechos de documentação.\n")

    while True:
        try:
            question = input("Pergunta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break

        if question.lower() in {"sair", "exit", "quit"}:
            print("Até mais!")
            break
        if not question:
            continue

        result = rag.answer(question, chunks=chunks)
        print(f"\n{result.answer}\n")
        if result.status == "ok":
            print(f"(status: ok | fontes: {', '.join(result.sources)} | {result.latency_seconds:.1f}s)\n")
        else:
            print(f"(status: {result.status} | {result.latency_seconds:.1f}s)\n")


if __name__ == "__main__":
    main()
