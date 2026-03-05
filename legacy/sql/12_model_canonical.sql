-- Build deterministic Germany-scoped canonical table.

DELETE FROM app.products_canonical;
DELETE FROM app.product_alias_map;
DELETE FROM app.product_family_map;

WITH germany_source AS (
    SELECT
        r.*,
        lower(trim(coalesce(r.product_measurements, ''))) AS measurements_normalized,
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
), typed_source AS (
    SELECT
        gs.*,
        CASE
            WHEN gs.measurements_normalized = '' OR gs.measurements_normalized = 'none'
                THEN 'missing'
            WHEN regexp_matches(gs.measurements_normalized, '^[0-9]+(?:[.,][0-9]+)?[ ]*cm$')
                THEN 'cm_single'
            WHEN regexp_matches(gs.measurements_normalized, '^[0-9]+(?:[.,][0-9]+)?[ ]*x[ ]*[0-9]+(?:[.,][0-9]+)?[ ]*cm$')
                THEN 'cm_double'
            WHEN regexp_matches(gs.measurements_normalized, '^[0-9]+(?:[.,][0-9]+)?[ ]*x[ ]*[0-9]+(?:[.,][0-9]+)?[ ]*x[ ]*[0-9]+(?:[.,][0-9]+)?[ ]*cm$')
                THEN 'cm_triple'
            WHEN strpos(gs.measurements_normalized, '(') > 0 AND regexp_matches(gs.measurements_normalized, 'cm')
                THEN 'cm_with_parenthetical'
            WHEN regexp_matches(gs.measurements_normalized, '/') AND regexp_matches(gs.measurements_normalized, 'cm')
                THEN 'cm_with_alternatives'
            WHEN regexp_matches(gs.measurements_normalized, 'm²') AND regexp_matches(gs.measurements_normalized, 'cm')
                THEN 'area_with_height'
            WHEN regexp_matches(gs.measurements_normalized, 'cm')
                THEN 'cm_other'
            ELSE 'non_cm_or_unknown'
        END AS dimensions_type,
        CASE
            WHEN strpos(gs.measurements_normalized, '(') > 0
                THEN trim(split_part(gs.measurements_normalized, '(', 1))
            ELSE gs.measurements_normalized
        END AS parse_source_text
    FROM germany_source AS gs
), parsed_source AS (
    SELECT
        ts.*,
        regexp_extract_all(ts.parse_source_text, '([0-9]+(?:[.,][0-9]+)?)') AS dimension_tokens
    FROM typed_source AS ts
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
        dimensions_type,
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
    FROM parsed_source
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
    dimensions_type,
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
    dimensions_type,
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

-- Defensive backfill: ensure numeric dimension fields are hydrated from stored
-- dimensions text if initial parse left gaps.
UPDATE app.products_canonical
SET
    width_cm = coalesce(
        width_cm,
        TRY_CAST(
            replace(
                list_extract(
                    regexp_extract_all(lower(trim(coalesce(dimensions_text, ''))), '([0-9]+(?:[.,][0-9]+)?)'),
                    1
                ),
                ',',
                '.'
            ) AS DOUBLE
        )
    ),
    depth_cm = coalesce(
        depth_cm,
        TRY_CAST(
            replace(
                list_extract(
                    regexp_extract_all(lower(trim(coalesce(dimensions_text, ''))), '([0-9]+(?:[.,][0-9]+)?)'),
                    2
                ),
                ',',
                '.'
            ) AS DOUBLE
        )
    ),
    height_cm = coalesce(
        height_cm,
        TRY_CAST(
            replace(
                list_extract(
                    regexp_extract_all(lower(trim(coalesce(dimensions_text, ''))), '([0-9]+(?:[.,][0-9]+)?)'),
                    3
                ),
                ',',
                '.'
            ) AS DOUBLE
        )
    );

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
