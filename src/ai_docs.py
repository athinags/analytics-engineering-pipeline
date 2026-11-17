"""Gera o catálogo de dados (docs/data_catalog.md) a partir do schema.yml + warehouse.

Modo padrão (offline): monta o catálogo com descrições do schema.yml e tipos reais das colunas.
Modo --ai: pede a um LLM (Claude) um resumo de negócio e ideias de análise para cada modelo,
usando um prompt estruturado. Requer: pip install anthropic e a variável ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb
import yaml

from src.pipeline import DB_PATH, MODELS_DIR, ROOT, discover_models

OUTPUT = ROOT / "docs" / "data_catalog.md"
MODEL_NAME = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

# Prompt engineering: papel + contexto + tarefa + formato + restrições (anti-alucinação).
PROMPT_TEMPLATE = """Você é um Analytics Engineer sênior documentando um data warehouse.

CONTEXTO
Tabela: {table}
Descrição técnica: {description}
Colunas (nome: tipo): {columns}
Amostra (até 3 linhas): {sample}

TAREFA
Escreva para um público de negócio (não técnico):
1. "Para que serve": 1 frase.
2. "Perguntas que responde": 3 bullets.

REGRAS
- Use SOMENTE informações presentes no contexto acima; não invente colunas ou métricas.
- Português do Brasil, no máximo 90 palavras no total.
- Responda em Markdown, sem títulos."""


def ai_summary(prompt: str) -> str:
    try:
        import anthropic
    except ImportError as exc:  # dependência opcional
        raise SystemExit("Instale a dependência: pip install anthropic") from exc
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Defina a variável de ambiente ANTHROPIC_API_KEY para usar --ai")
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL_NAME, max_tokens=400, messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def build_catalog(use_ai: bool) -> str:
    models = discover_models()
    schema = yaml.safe_load((MODELS_DIR / "schema.yml").read_text(encoding="utf-8"))
    con = duckdb.connect(str(DB_PATH), read_only=True)
    lines = ["# 📚 Catálogo de Dados", "", "_Gerado automaticamente por `src/ai_docs.py`._", ""]

    for model in schema["models"]:
        table = f"{models[model['name']].layer}.{model['name']}"
        cols = con.execute(f"select column_name, data_type from information_schema.columns "
                           f"where table_schema || '.' || table_name = '{table}' order by ordinal_position").fetchall()
        col_docs = {c["name"]: c.get("description", "") for c in model.get("columns", [])}
        lines += [f"## `{table}`", "", model["description"], ""]

        if use_ai:
            sample = con.execute(f"select * from {table} limit 3").fetchall()
            prompt = PROMPT_TEMPLATE.format(
                table=table, description=model["description"],
                columns=", ".join(f"{n}: {t}" for n, t in cols), sample=sample)
            lines += ["**Resumo de negócio (IA):**", "", ai_summary(prompt), ""]

        lines += ["| Coluna | Tipo | Descrição |", "|---|---|---|"]
        lines += [f"| `{n}` | {t} | {col_docs.get(n, '—')} |" for n, t in cols]
        lines.append("")
    con.close()
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai", action="store_true", help="enriquece o catálogo com resumos gerados por IA")
    args = parser.parse_args()
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build_catalog(args.ai), encoding="utf-8")
    print(f"✔ Catálogo gerado em {OUTPUT}")


if __name__ == "__main__":
    main()
