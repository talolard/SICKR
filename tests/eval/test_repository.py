from __future__ import annotations

from pathlib import Path

import duckdb

from tal_maria_ikea.eval.repository import EvalRepository


def test_insert_and_read_labeled_queries() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute(Path("sql/10_schema.sql").read_text(encoding="utf-8"))

    repository = EvalRepository(connection)
    repository.upsert_prompt("v1", "prompt", "hash")
    repository.upsert_subset("subset-1", "definition", "subset-hash")
    repository.insert_generated_queries("v1", "subset-1", [("q-1", "black frame", None, None)])

    connection.execute(
        "INSERT INTO app.eval_labels "
        "(eval_query_id, canonical_product_key, relevance_rank) "
        "VALUES ('q-1', '1-DE', 1)"
    )

    rows = repository.get_labeled_queries()
    assert rows == [("q-1", "black frame", ["1-DE"])]
