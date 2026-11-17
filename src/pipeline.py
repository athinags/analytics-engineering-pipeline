"""Mini-framework ELT inspirado no dbt, executado sobre DuckDB.

Fluxo:  raw (CSV)  ->  staging (limpeza)  ->  marts (negócio)  ->  testes  ->  export (CSV p/ BI)

Conceitos reproduzidos do dbt/Dataform:
  * {{ source('raw','tabela') }}  -> referência a uma tabela de origem
  * {{ ref('modelo') }}           -> referência a outro modelo (cria o grafo de dependências - DAG)
  * schema.yml                    -> documentação + testes declarativos
  * tests/*.sql                   -> testes "singulares": retornam as linhas que violam a regra
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "warehouse.duckdb"
RAW_DIR = ROOT / "data" / "raw"
MODELS_DIR = ROOT / "models"
TESTS_DIR = ROOT / "tests"
EXPORT_DIR = ROOT / "output"

REF_RE = re.compile(r"\{\{\s*ref\(\s*'(\w+)'\s*\)\s*\}\}")
SOURCE_RE = re.compile(r"\{\{\s*source\(\s*'(\w+)'\s*,\s*'(\w+)'\s*\)\s*\}\}")


@dataclass
class Model:
    name: str
    layer: str  # nome da pasta = schema onde a tabela será criada (staging, marts)
    sql: str
    deps: set[str] = field(default_factory=set)


# --------------------------------------------------------------------------- descoberta e compilação
def discover_models(models_dir: Path = MODELS_DIR) -> dict[str, Model]:
    """Lê todos os .sql de models/ e extrai as dependências via {{ ref() }}."""
    models: dict[str, Model] = {}
    for path in sorted(models_dir.rglob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        models[path.stem] = Model(path.stem, path.parent.name, sql, set(REF_RE.findall(sql)))
    return models


def execution_order(models: dict[str, Model]) -> list[str]:
    """Ordenação topológica: garante que cada modelo rode depois de suas dependências."""
    graph = {name: m.deps for name, m in models.items()}
    return list(TopologicalSorter(graph).static_order())


def compile_sql(sql: str, models: dict[str, Model]) -> str:
    """Troca {{ ref('x') }} por schema.x e {{ source('raw','y') }} por raw.y."""

    def _ref(match: re.Match) -> str:
        name = match.group(1)
        if name not in models:
            raise KeyError(f"ref('{name}') aponta para um modelo inexistente")
        return f"{models[name].layer}.{name}"

    sql = REF_RE.sub(_ref, sql)
    return SOURCE_RE.sub(lambda m: f"{m.group(1)}.{m.group(2)}", sql)


# --------------------------------------------------------------------------- E (extract/load)
def load_raw(con: duckdb.DuckDBPyConnection) -> None:
    """Carrega os CSVs como tabelas no schema raw, sem alterar nada (princípio ELT)."""
    con.execute("create schema if not exists raw")
    csvs = sorted(RAW_DIR.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"Nenhum CSV em {RAW_DIR}. Rode: python -m src.generate_data")
    for csv_path in csvs:
        # all_varchar: a tipagem é responsabilidade da camada staging, não da carga.
        con.execute(
            f"create or replace table raw.{csv_path.stem} as "
            f"select * from read_csv('{csv_path.as_posix()}', header=true, all_varchar=true)"
        )
        n = con.execute(f"select count(*) from raw.{csv_path.stem}").fetchone()[0]
        print(f"  raw.{csv_path.stem:<14} {n:>6} linhas")


# --------------------------------------------------------------------------- T (transform)
def run_models(con: duckdb.DuckDBPyConnection, models: dict[str, Model]) -> None:
    for layer in sorted({m.layer for m in models.values()}):
        con.execute(f"create schema if not exists {layer}")
    for name in execution_order(models):
        m = models[name]
        started = time.perf_counter()
        con.execute(f"create or replace table {m.layer}.{name} as {compile_sql(m.sql, models)}")
        n = con.execute(f"select count(*) from {m.layer}.{name}").fetchone()[0]
        print(f"  {m.layer}.{name:<28} {n:>6} linhas  ({time.perf_counter() - started:.2f}s)")


# --------------------------------------------------------------------------- testes de qualidade
def _generic_test_sql(kind: str, table: str, column: str, cfg: dict | None, models: dict[str, Model]) -> str:
    """Devolve um SELECT que conta quantas linhas VIOLAM a regra (0 = teste passou)."""
    if kind == "not_null":
        return f"select count(*) from {table} where {column} is null"
    if kind == "unique":
        return f"select count(*) from (select {column} from {table} group by {column} having count(*) > 1)"
    if kind == "accepted_values":
        values = ", ".join(f"'{v}'" for v in cfg["values"])
        return f"select count(*) from {table} where {column} is not null and {column} not in ({values})"
    if kind == "relationships":
        target = f"{models[cfg['to']].layer}.{cfg['to']}"
        return (f"select count(*) from {table} where {column} is not null "
                f"and {column} not in (select {cfg['field']} from {target})")
    raise ValueError(f"Teste desconhecido: {kind}")


def run_tests(con: duckdb.DuckDBPyConnection, models: dict[str, Model]) -> tuple[int, int]:
    """Executa testes do schema.yml (genéricos) e de tests/*.sql (singulares)."""
    passed = failed = 0

    def report(label: str, failures: int) -> None:
        nonlocal passed, failed
        ok = failures == 0
        passed, failed = passed + ok, failed + (not ok)
        print(f"  {'✔ PASS' if ok else '✘ FAIL'}  {label}" + ("" if ok else f"  -> {failures} linhas violam"))

    schema = yaml.safe_load((MODELS_DIR / "schema.yml").read_text(encoding="utf-8"))
    for model in schema["models"]:
        table = f"{models[model['name']].layer}.{model['name']}"
        for col in model.get("columns", []):
            for test in col.get("tests", []):
                kind, cfg = (test, None) if isinstance(test, str) else next(iter(test.items()))
                sql = _generic_test_sql(kind, table, col["name"], cfg, models)
                report(f"{kind}({table}.{col['name']})", con.execute(sql).fetchone()[0])

    for path in sorted(TESTS_DIR.glob("*.sql")):
        sql = compile_sql(path.read_text(encoding="utf-8"), models)
        failures = con.execute(f"select count(*) from ({sql})").fetchone()[0]
        report(f"singular: {path.stem}", failures)

    return passed, failed


# --------------------------------------------------------------------------- export + resumo
def export_marts(con: duckdb.DuckDBPyConnection, models: dict[str, Model]) -> None:
    """Exporta os marts em CSV: prontos para Looker Studio / Power BI."""
    EXPORT_DIR.mkdir(exist_ok=True)
    for name, m in models.items():
        if m.layer == "marts":
            out = EXPORT_DIR / f"{name}.csv"
            con.execute(f"copy {m.layer}.{name} to '{out.as_posix()}' (header, delimiter ',')")
    print(f"  CSVs exportados em {EXPORT_DIR}")


def print_insights(con: duckdb.DuckDBPyConnection) -> None:
    print("\n📊 Insights rápidos")
    total, orders = con.execute(
        "select sum(revenue), sum(orders) from marts.mart_monthly_revenue").fetchone()
    print(f"  Receita total: R$ {total:,.2f} em {orders:,} pedidos")
    cat = con.execute("select category, revenue from marts.mart_category_performance limit 1").fetchone()
    print(f"  Categoria líder: {cat[0]} (R$ {cat[1]:,.2f})")
    print("  Segmentos RFM:")
    for seg, n in con.execute(
            "select segment, count(*) from marts.mart_customer_rfm group by 1 order by 2 desc").fetchall():
        print(f"    - {seg:<12} {n} clientes")


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline ELT de Analytics Engineering (DuckDB)")
    parser.add_argument("--skip-tests", action="store_true", help="não executa os testes de qualidade")
    args = parser.parse_args(argv)

    models = discover_models()
    con = duckdb.connect(str(DB_PATH))

    print("1/4  Carga (raw)")
    load_raw(con)
    print("\n2/4  Transformação (staging -> marts)")
    run_models(con, models)

    failed = 0
    if not args.skip_tests:
        print("\n3/4  Testes de qualidade")
        passed, failed = run_tests(con, models)
        print(f"  Resultado: {passed} passaram, {failed} falharam")

    print("\n4/4  Export")
    export_marts(con, models)
    print_insights(con)
    con.close()
    return 1 if failed else 0  # código de saída != 0 permite quebrar um CI/CD


if __name__ == "__main__":
    sys.exit(main())
