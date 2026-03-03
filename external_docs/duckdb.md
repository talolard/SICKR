    ---

title: DuckDB docs
original-url: <https://duckdb.org/llms.txt>
---
>
> DuckDB is an in-process analytical database management system. DuckDB supports SQL and offers clients in popular programming languages such as Python, Java, Node.js, Rust and Go. DuckDB is used as a universal data wrangling tool for data science and data engineering use cases. DuckDB is highly portable and it also runs in web browsers, on smartphones, etc.

Things to remember when using DuckDB:

- DuckDB uses a PostgreSQL-compatible SQL language. All DuckDB clients use the same SQL language.
- DuckDB can load data from popular formats, including CSV, JSON and Parquet. DuckDB can also directly run queries on CSV, JSON and Parquet files.
- DuckDB supports persistent storage but can also run in in-memory mode. The in-memory mode is useful when analyzing small data sets or doing data transformation steps.
- When loading large chunks of data, use the [`SET preserve_insertion_order = false;` configuration setting](https://duckdb.org/docs/stable/sql/dialect/order_preservation) to speed up the loading process and reduce the memory load. When using DuckDB in combination with dataframe libraries such as pandas, turn this mode back on after loading by issuing `SET preserve_insertion_order = false;`.
- DuckDB supports data lake formats such as [Delta Lake](https://duckdb.org/docs/stable/core_extensions/delta), [Iceberg](https://duckdb.org/docs/stable/core_extensions/iceberg/overview) and [DuckLake](https://duckdb.org/docs/stable/core_extensions/ducklake).
- If a workload requires concurrent write access by multiple DuckDB clients, consider using [DuckLake](https://duckdb.org/docs/stable/core_extensions/ducklake).

## Clients

- [Command Line Interface](https://duckdb.org/docs/stable/clients/cli/overview)
- [Node.js](https://duckdb.org/docs/stable/clients/node_neo/overview)
- [Python](https://duckdb.org/docs/stable/clients/python/overview)

## Extensions

- DuckDB has a powerful [extension mechanism](https://duckdb.org/docs/stable/core_extensions/overview) that allows loading additional features to DuckDB.
    