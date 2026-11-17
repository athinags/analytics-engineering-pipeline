"""Testes unitários do próprio framework + teste de ponta a ponta."""
import duckdb

from src import generate_data, pipeline


def test_compile_sql_resolves_ref_and_source():
    models = {"a": pipeline.Model("a", "staging", "select 1")}
    sql = "select * from {{ ref('a') }} join {{ source('raw', 't') }} using (id)"
    assert pipeline.compile_sql(sql, models) == "select * from staging.a join raw.t using (id)"


def test_execution_order_respects_dependencies():
    models = pipeline.discover_models()
    order = pipeline.execution_order(models)
    for name, model in models.items():
        for dep in model.deps:
            assert order.index(dep) < order.index(name)


def test_end_to_end_pipeline_passes_all_quality_tests(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_data, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(pipeline, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(pipeline, "EXPORT_DIR", tmp_path / "out")
    generate_data.generate(n_customers=100, n_products=10, n_orders=400)

    models = pipeline.discover_models()
    con = duckdb.connect(":memory:")
    pipeline.load_raw(con)
    pipeline.run_models(con, models)
    _, failed = pipeline.run_tests(con, models)
    assert failed == 0
    # a limpeza removeu as duplicatas de pedidos:
    raw_n = con.execute("select count(*) from raw.orders").fetchone()[0]
    stg_n = con.execute("select count(*) from staging.stg_orders").fetchone()[0]
    assert stg_n < raw_n
