-- Evaluation registry helper views.

CREATE OR REPLACE VIEW app.eval_queries_with_labels AS
SELECT
    q.eval_query_id,
    q.query_text,
    q.category_hint,
    q.intent_kind,
    q.prompt_version,
    q.subset_id,
    l.canonical_product_key,
    l.relevance_rank
FROM app.eval_queries_generated AS q
LEFT JOIN app.eval_labels AS l
  ON l.eval_query_id = q.eval_query_id;
