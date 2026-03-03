-- Embedding text materialization strategies.

CREATE OR REPLACE VIEW app.embedding_input_v1_baseline AS
SELECT
    canonical_product_key,
    concat_ws(' ', product_name, coalesce(description_text, '')) AS embedding_text,
    'v1_baseline' AS strategy_version
FROM app.products_market_de_v1;

CREATE OR REPLACE VIEW app.embedding_input_v2_metadata_first AS
SELECT
    canonical_product_key,
    concat(
        'name: ', product_name, '\n',
        'type: ', coalesce(product_type, 'unknown'), '\n',
        'main_category: ', coalesce(main_category, 'unknown'), '\n',
        'sub_category: ', coalesce(sub_category, 'unknown'), '\n',
        'dimensions_cm: width=', coalesce(CAST(width_cm AS VARCHAR), 'na'),
        ', depth=', coalesce(CAST(depth_cm AS VARCHAR), 'na'),
        ', height=', coalesce(CAST(height_cm AS VARCHAR), 'na'), '\n',
        'price_eur: ', coalesce(CAST(price_eur AS VARCHAR), 'na'), '\n',
        'badge: ', coalesce(badge, 'none'), '\n',
        'description: ', coalesce(description_text, '')
    ) AS embedding_text,
    'v2_metadata_first' AS strategy_version
FROM app.products_market_de_v1;
