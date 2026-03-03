-- Candidate retrieval query scaffold used before reranking.

SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.description,
    p.dimensions_text,
    p.price_text
FROM app.products AS p
WHERE
    (? IS NULL OR p.category = ?)
ORDER BY p.updated_at DESC
LIMIT ?;
