"""Top-level convenience imports for tablex."""

from .lines import ExplicitLineExtractor, extract_explicit_lines
from .scoring import search_best_table_settings, score_tables
from .utils.table_settings import iter_table_settings

__all__ = [
    "extract_explicit_lines",
    "ExplicitLineExtractor",
    "search_best_table_settings",
    "score_tables",
    "iter_table_settings",
]
