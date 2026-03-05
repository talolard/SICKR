The project’s ultimate goal is to allow users to update, upload, or specify a 2D floor plan and the dimensions, and then find relevant IKEA furniture. In phase two, it would also fit in the apartment.

In phase one, we would have a web UI. The user would ask questions in natural language, like:

- Find me an L-shaped couch.
- Find me a ceiling-mounted light fixture that’s good for a hallway.
- Show me black picture frames.

The user would get the results based on the data we have in DuckDB and the semantic query. We’re expecting the user to ask a question in text, and then we would use an API called the Gemini embedding, mentioning whatever the relevant task type is for the query. We would have already pre-indexed our IKEA table.

The rough structure is:

- The web app with the database connection and the ability to do queries.
- We should use Django, the latest version of Django, with its default HTML templates for the actual user request/response, because we’re just going to be running this locally.
- We’re going to want to have an embeddings utility or job that can consume and embed the whole file, do that in segments, and use the batch API from Gemini, but only if we can get an ETA of when it will be complete.
- That module should be able to create our vectors, and it should be independent of the web app.

A few important things:

1. Being able to do a subset.
2. Generating enriched or more structured text to be embedded.

For example, we should have all of the metadata from the database at the top, and then the description as the key text. We’d want to have some class or function that lets us experiment with or define how exactly that is created, and then evaluate it against a handful of queries.

For that stream of work, we also need to look at the data and create an eval set: maybe a few hundred queries where we know what the answer should be from the data, like what are the best two or three items. Then we’d want to evaluate that those are there.

As a pre-task in that line of work, we should explore the data: how it breaks down by country. We’re focused on Germany, so we can narrow most of the work onto that. There will still be duplicate products, product families, and things that need to be merged. You can go ahead and create analytics tables, mapping tables, or similar-items tables, and whatever else needs to be done so that:

1. We’re able to enrich the embeddings with additional metadata.
2. We have a queryable map of our data. 