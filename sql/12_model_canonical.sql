-- Build deterministic Germany-scoped canonical table.

DELETE FROM app.products_canonical;
DELETE FROM app.product_alias_map;
DELETE FROM app.product_family_map;

WITH germany_source AS (
    SELECT
        r.*,
        regexp_extract_all(coalesce(r.product_measurements, ''), '(\\d+(?:[.,]\\d+)?)') AS dimension_tokens,
        TRY_CAST(NULLIF(r.product_rating, 'none') AS DOUBLE) AS rating_num,
        TRY_CAST(NULLIF(r.product_rating_count, 'none') AS BIGINT) AS rating_count_num,
        ROW_NUMBER() OVER (
            PARTITION BY r.product_id
            ORDER BY
                TRY_CAST(NULLIF(r.product_rating_count, 'none') AS BIGINT) DESC NULLS LAST,
                r.online_sellable DESC,
                r.unique_id ASC
        ) AS dedup_rank
    FROM app.products_raw AS r
    WHERE r.country = 'Germany'
), canonical AS (
    SELECT
        CASE
            WHEN product_id IS NOT NULL THEN CAST(product_id AS VARCHAR) || '-DE'
            ELSE unique_id
        END AS canonical_product_key,
        product_id,
        unique_id,
        country,
        coalesce(product_name, 'UNKNOWN') AS product_name,
        product_type,
        product_description AS description_text,
        main_category,
        sub_category,
        product_measurements AS dimensions_text,
        TRY_CAST(replace(list_extract(dimension_tokens, 1), ',', '.') AS DOUBLE) AS width_cm,
        TRY_CAST(replace(list_extract(dimension_tokens, 2), ',', '.') AS DOUBLE) AS depth_cm,
        TRY_CAST(replace(list_extract(dimension_tokens, 3), ',', '.') AS DOUBLE) AS height_cm,
        CASE WHEN currency = 'EUR' THEN price ELSE NULL END AS price_eur,
        currency,
        rating_num AS rating,
        rating_count_num AS rating_count,
        badge,
        online_sellable,
        url
    FROM germany_source
    WHERE dedup_rank = 1
)
INSERT INTO app.products_canonical (
    canonical_product_key,
    product_id,
    unique_id,
    country,
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
    currency,
    rating,
    rating_count,
    badge,
    online_sellable,
    url,
    source_updated_at
)
SELECT
    canonical_product_key,
    product_id,
    unique_id,
    country,
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
    currency,
    rating,
    rating_count,
    badge,
    online_sellable,
    url,
    now()
FROM canonical;

-- Alias map for deduplicated records.
INSERT INTO app.product_alias_map (
    canonical_product_key,
    alias_unique_id,
    alias_product_id,
    alias_country,
    alias_reason
)
SELECT
    CASE
        WHEN r.product_id IS NOT NULL THEN CAST(r.product_id AS VARCHAR) || '-DE'
        ELSE r.unique_id
    END AS canonical_product_key,
    r.unique_id,
    r.product_id,
    r.country,
    CASE
        WHEN r.country != 'Germany' THEN 'same_product_id_other_market'
        ELSE 'duplicate_in_germany'
    END AS alias_reason
FROM app.products_raw AS r
WHERE r.product_id IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM app.products_canonical AS c
      WHERE c.product_id = r.product_id
  );

-- Family map by normalized product name + product type.
INSERT INTO app.product_family_map (
    family_key,
    canonical_product_key,
    family_reason
)
SELECT
    lower(trim(product_name)) || '|' || lower(trim(coalesce(product_type, 'unknown'))) AS family_key,
    canonical_product_key,
    'name_and_type_match'
FROM app.products_canonical;
