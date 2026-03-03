-- Retrieve hydrated semantic candidates with structured filters.

WITH scored AS (
    SELECT
        c.canonical_product_key,
        c.product_name,
        c.product_type,
        c.description_text,
        c.main_category,
        c.sub_category,
        c.dimensions_text,
        c.width_cm,
        c.depth_cm,
        c.height_cm,
        c.price_eur,
        c.url,
        list_cosine_similarity(e.embedding_vector, ?) AS semantic_score
    FROM app.products_market_de_v1 AS c
    JOIN app.product_embeddings_latest AS e
      ON e.canonical_product_key = c.canonical_product_key
    WHERE e.embedding_model = ?
      AND e.strategy_version = ?
)
SELECT
    canonical_product_key,
    product_name,
    product_type,
    description_text,
    main_category,
    sub_category,
    dimensions_text,
    width_cm,
    depth_cm,
    height_cm,
    price_eur,
    url,
    semantic_score
FROM scored
WHERE
    (? IS NULL OR main_category = ?)
    AND (? IS NULL OR price_eur IS NOT NULL AND price_eur >= ?)
    AND (? IS NULL OR price_eur IS NOT NULL AND price_eur <= ?)
    AND (? IS NULL OR width_cm = ?)
    AND (? IS NULL OR depth_cm = ?)
    AND (? IS NULL OR height_cm = ?)
    AND (? IS NULL OR width_cm IS NOT NULL AND width_cm >= ?)
    AND (? IS NULL OR width_cm IS NOT NULL AND width_cm <= ?)
    AND (? IS NULL OR depth_cm IS NOT NULL AND depth_cm >= ?)
    AND (? IS NULL OR depth_cm IS NOT NULL AND depth_cm <= ?)
    AND (? IS NULL OR height_cm IS NOT NULL AND height_cm >= ?)
    AND (? IS NULL OR height_cm IS NOT NULL AND height_cm <= ?)
ORDER BY semantic_score DESC
LIMIT ?;
