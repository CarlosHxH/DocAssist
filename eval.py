"""Roda o conjunto de perguntas de avaliação (eval_questions.json) contra o pipeline RAG
e gera um relatório de validação (requisito 06 do edital: cenários de teste documentados,
e requisito 01: critério observável de sucesso).

Uso:
    python eval.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import rag

QUESTIONS_PATH = Path(__file__).parent / "eval_questions.json"
REPORT_PATH = Path(__file__).parent / "tests" / "relatorio_avaliacao.md"
SUCCESS_THRESHOLD = 0.80  # critério de sucesso do requisito 01: >= 80% de acerto


def grade(item: dict, result: rag.AnswerResult) -> bool:
    if item["type"] == "esperado":
        if result.status != "ok":
            return False
        expected = item["expected_source"].lower()
        return any(expected in source.lower() for source in result.sources)
    # "fora_de_escopo" e "limite": o comportamento correto é recusar (sem alucinar)
    return result.status == "sem_contexto"


def main() -> None:
    chunks = rag.load_index()
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    rows = []
    passed = 0
    start = time.monotonic()
    for item in questions:
        result = rag.answer(item["question"], chunks=chunks)
        ok = grade(item, result)
        passed += int(ok)
        rows.append((item, result, ok))
        mark = "PASSOU" if ok else "FALHOU"
        print(f"[{mark}] #{item['id']:>2} ({item['type']:>13}) {item['question'][:60]!r}")

    total = len(questions)
    accuracy = passed / total if total else 0.0
    elapsed = time.monotonic() - start

    print(f"\nResultado: {passed}/{total} ({accuracy:.0%}) — critério de sucesso: >= {SUCCESS_THRESHOLD:.0%}")
    print("Critério ATINGIDO" if accuracy >= SUCCESS_THRESHOLD else "Critério NÃO atingido")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Relatório de avaliação — DocAssist",
        "",
        f"Executado em {time.strftime('%Y-%m-%d %H:%M:%S')}, {total} perguntas, "
        f"tempo total {elapsed:.1f}s.",
        "",
        f"**Resultado: {passed}/{total} ({accuracy:.0%})** — critério de sucesso do MVP: "
        f">= {SUCCESS_THRESHOLD:.0%} de acerto. "
        f"{'Critério ATINGIDO.' if accuracy >= SUCCESS_THRESHOLD else 'Critério NÃO atingido.'}",
        "",
        "| # | Tipo | Pergunta | Status | Fontes citadas | Esperado | Resultado |",
        "|---|------|----------|--------|-----------------|----------|-----------|",
    ]
    for item, result, ok in rows:
        question_display = item["question"] if item["question"] else "*(vazia)*"
        lines.append(
            f"| {item['id']} | {item['type']} | {question_display} | {result.status} | "
            f"{', '.join(result.sources) or '-'} | {item['expected_source'] or '-'} | "
            f"{'PASSOU' if ok else 'FALHOU'} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRelatório salvo em {REPORT_PATH}")


if __name__ == "__main__":
    main()
