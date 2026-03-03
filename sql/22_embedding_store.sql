-- Embedding storage helpers.

-- Latest embedding per product for strategy/model.
CREATE OR REPLACE VIEW app.product_embeddings_latest AS
SELECT
    canonical_product_key,
    embedding_model,
    strategy_version,
    run_id,
    embedding_vector,
    embedded_text,
    embedded_at
FROM app.product_embeddings;
