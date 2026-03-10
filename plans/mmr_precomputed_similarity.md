# MMR With Precomputed Similarities

## Goal
Replace round-robin family diversification with MMR selection and precompute embedding similarities once into DuckDB for runtime lookup.

## Approach
1. Extend runtime schema with `app.product_embedding_neighbors` indexed by embedding model + source product key.
2. Add ingest-side batch builder in `src/ingest/` that reads embeddings and writes per-source top-k cosine neighbors.
3. Add repository method to fetch pairwise similarities for current candidate sets.
4. Replace `search_diversity` logic with MMR selection using normalized rerank scores and redundancy penalty lookup.
5. Wire graph/tool path to use MMR output and keep warning metadata contract.
6. Update tests and docs.

## Notes
- Keep tool/result contracts stable where possible.
- Use typed config knobs (`lambda=0.8`, preselect=30), and store all neighbors by default.
