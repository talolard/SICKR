"""Compatibility wrapper for the search eval dataset package.

The search eval cases now live in `evals.search.datasets.*` modules so authors can add
or revise scenario groups without reopening one large file. Keep importing
`build_search_eval_dataset` from here or from `evals.search` if you only need the
assembled dataset object.
"""

from evals.search.datasets import build_search_eval_dataset

__all__ = ["build_search_eval_dataset"]
