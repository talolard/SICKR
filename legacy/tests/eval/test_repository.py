from __future__ import annotations

from pathlib import Path

import duckdb
from ikea_agent.eval.repository import EvalRepository


def test_insert_and_read_labeled_queries() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute(Path("sql/10_schema.sql").read_text(encoding="utf-8"))

    repository = EvalRepository(connection)
    repository.upsert_prompt("v1", "prompt", "hash")
    repository.upsert_subset("subset-1", "definition", "subset-hash")
    repository.insert_generated_queries("v1", "subset-1", [("q-1", "black frame", None, None)])
    assert repository.count_generated_queries() == 1
    assert repository.count_labeled_queries() == 0

    connection.execute(
        "INSERT INTO app.eval_labels "
        "(eval_query_id, canonical_product_key, relevance_rank) "
        "VALUES ('q-1', '1-DE', 1)"
    )
    assert repository.count_labeled_queries() == 1

    rows = repository.get_labeled_queries()
    assert rows == [("q-1", "black frame", ["1-DE"])]


def test_list_generated_queries_and_upsert_eval_labels() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute(Path("sql/10_schema.sql").read_text(encoding="utf-8"))

    repository = EvalRepository(connection)
    repository.insert_generated_queries(
        "p1",
        "subset-1",
        [
            ("q-1", "desk for small room", "tables-desks", "search"),
            ("q-2", "wardrobe with mirror", "storage", "search"),
        ],
    )

    queries = repository.list_generated_queries(subset_id="subset-1", prompt_version="p1")
    assert queries == [("q-1", "desk for small room"), ("q-2", "wardrobe with mirror")]

    repository.upsert_eval_labels(
        [
            ("q-1", "1-DE", 1),
            ("q-1", "2-DE", 2),
            ("q-2", "3-DE", 1),
        ]
    )

    assert repository.count_labeled_queries() == 2
