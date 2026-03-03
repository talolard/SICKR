-- Retrieve hydrated semantic candidates with structured filters.

WITH nearest AS (
    SELECT
        e.canonical_product_key,
        array_cosine_distance(
            e.embedding_vector,
            CAST(? AS FLOAT[__VECTOR_DIMENSIONS__])
        ) AS cosine_distance
    FROM app.product_embeddings_latest AS e
    WHERE e.embedding_model = ?
    ORDER BY cosine_distance ASC
    LIMIT ?
), scored AS (
    SELECT
        c.canonical_product_key,
        c.product_name,
        c.product_type,
        c.description_text,
        e.embedded_text,
        c.main_category,
        c.sub_category,
        c.dimensions_text,
        c.width_cm,
        c.depth_cm,
        c.height_cm,
        c.price_eur,
        c.url,
        n.cosine_distance
FROM app.products_market_de_v1 AS c
JOIN nearest AS n
  ON n.canonical_product_key = c.canonical_product_key
JOIN app.product_embeddings_latest AS e
  ON e.canonical_product_key = c.canonical_product_key
 AND e.embedding_model = ?
)
SELECT
    canonical_product_key,
    product_name,
    product_type,
    description_text,
    embedded_text,
    main_category,
    sub_category,
    dimensions_text,
    width_cm,
    depth_cm,
    height_cm,
    price_eur,
    url,
    1.0 - cosine_distance AS semantic_score
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
ORDER BY
    CASE WHEN ? = 'price_asc' THEN price_eur END ASC NULLS LAST,
    CASE WHEN ? = 'price_desc' THEN price_eur END DESC NULLS LAST,
    CASE WHEN ? = 'size' THEN (coalesce(width_cm, 0) * coalesce(depth_cm, 0) * coalesce(height_cm, 0)) END DESC NULLS LAST,
    cosine_distance ASC,
    canonical_product_key ASC
LIMIT ?;
