-- Phase 1 market-scoped retrieval view.

CREATE OR REPLACE VIEW app.products_market_de_v1 AS
SELECT *
FROM app.products_canonical
WHERE country = 'Germany';
