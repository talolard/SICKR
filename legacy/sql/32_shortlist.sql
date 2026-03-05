-- Global shortlist hydration query.

SELECT
    s.canonical_product_key,
    p.product_name,
    p.product_type,
    p.main_category,
    p.sub_category,
    p.dimensions_text,
    p.price_eur,
    p.url,
    s.added_at,
    s.note
FROM app.shortlist_global AS s
JOIN app.products_market_de_v1 AS p
  ON p.canonical_product_key = s.canonical_product_key
ORDER BY s.added_at DESC;
