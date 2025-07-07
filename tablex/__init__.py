"""Top-level convenience imports for tablex."""
from pdfplumber.utils.text import WordExtractor

from .lines import ExplicitLineExtractor, extract_explicit_lines
from .scoring import score_tables, search_best_table_settings
from .utils.table_settings import iter_table_settings


__all__ = [
    "extract_explicit_lines",
    "ExplicitLineExtractor",
    "search_best_table_settings",
    "score_tables",
    "iter_table_settings",
]

# —— 1. 备份原始 __init__ ——
WordExtractor._orig_init = WordExtractor.__init__


# —— 2. 定义补丁 init ——
def _patched_init(self, *args, **kwargs):
    # 尝试 pop 出 text_settings，并打印出来
    removed = kwargs.pop("settings", None)
    if removed is not None:
        print(f"[PATCH] Removed settings: {removed!r}")
    # 调用原始 __init__
    return WordExtractor._orig_init(self, *args, **kwargs)


# —— 3. 应用补丁 ——
WordExtractor.__init__ = _patched_init
