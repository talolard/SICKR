-- Single embedding text materialization view (Phase 2).

CREATE OR REPLACE VIEW app.embedding_input AS
WITH germany_rows AS (
    SELECT
        c.canonical_product_key,
        c.product_id,
        c.country,
        c.product_name,
        c.product_type,
        c.main_category,
        c.sub_category,
        c.width_cm,
        c.depth_cm,
        c.height_cm,
        c.price_eur,
        c.badge,
        c.rating,
        c.rating_count,
        c.description_text
    FROM app.products_market_de_v1 AS c
), description_lines AS (
    SELECT
        r.product_id,
        string_agg(
            concat(
                'description_by_market: [',
                array_to_string(r.countries, ', '),
                '] ',
                r.description_text
            ),
            '\n'
            ORDER BY r.country_count DESC, array_to_string(r.countries, ', '), r.description_hash
        ) AS description_block
    FROM app.product_description_country_rollup AS r
    GROUP BY r.product_id
)
SELECT
    g.canonical_product_key,
    concat_ws(
        '\n',
        concat('name: ', g.product_name),
        CASE WHEN g.product_type IS NOT NULL AND trim(g.product_type) != '' THEN concat('type: ', g.product_type) END,
        CASE WHEN g.main_category IS NOT NULL AND trim(g.main_category) != '' THEN concat('main_category: ', g.main_category) END,
        CASE WHEN g.sub_category IS NOT NULL AND trim(g.sub_category) != '' THEN concat('sub_category: ', g.sub_category) END,
        CASE
            WHEN g.width_cm IS NOT NULL OR g.depth_cm IS NOT NULL OR g.height_cm IS NOT NULL THEN
                concat(
                    'dimensions_cm: width=', coalesce(CAST(g.width_cm AS VARCHAR), '?'),
                    ', depth=', coalesce(CAST(g.depth_cm AS VARCHAR), '?'),
                    ', height=', coalesce(CAST(g.height_cm AS VARCHAR), '?')
                )
        END,
        CASE WHEN g.price_eur IS NOT NULL THEN concat('price_eur: ', CAST(g.price_eur AS VARCHAR)) END,
        CASE WHEN g.badge IS NOT NULL AND trim(g.badge) != '' AND lower(trim(g.badge)) != 'none' THEN concat('badge: ', g.badge) END,
        concat('country: ', g.country),
        CASE WHEN g.rating IS NOT NULL THEN concat('rating: ', CAST(g.rating AS VARCHAR)) END,
        CASE WHEN g.rating_count IS NOT NULL THEN concat('rating_count: ', CAST(g.rating_count AS VARCHAR)) END,
        CASE
            WHEN dl.description_block IS NOT NULL AND trim(dl.description_block) != '' THEN dl.description_block
            WHEN g.description_text IS NOT NULL AND trim(g.description_text) != '' THEN concat('description: ', g.description_text)
        END
    ) AS embedding_text
FROM germany_rows AS g
LEFT JOIN description_lines AS dl
    ON dl.product_id = g.product_id;
