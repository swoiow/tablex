"""
Table Settings – Case‑Optimised (v2025‑07‑01)
============================================

This file **supersedes** the draft “Table Settings Final”.
It merges insights from **Table Settings Old**, **Table Settings Latest** and the
newly‑supplied **case screenshots** (3‑column tables with blank edge cells,
narrow‑width big tables, right‑top blank cell, etc.).

Key take‑aways from the cases
-----------------------------
1. **Narrow big tables** – the table may only span ~35‑55 % of the page width,
   but is still the primary structure.  Relying solely on longest horizontal
   line ≥60 % page width (H_BIG) misses these.
2. **Blank edge columns** – the first or last column can contain *no words*,
   so a *min_words_vertical* ≥1 will break detection.
3. **Missing top horizontal line** – page break causes the first horizontal
   line to be absent.  Variants must cope with h‑line count = 0/1.
4. **Sub‑tables inside cells** – treat inner lines as noise; keep *edge_min_length*
   relatively high so that only outer borders are considered during the first
   pass.

Design decisions
----------------
* Keep the **strong → relaxed** ordering, but inject three new variants **before
  the generic fallbacks**.  They explicitly target the corner‑cases above.
* Lower the *big‑table* heuristics: H_BIG 0.60 → 0.50,  WIDTH_RATIO 0.30 → 0.25.
* Allow *min_words_vertical = 0* for the new “edge‑blank” variant – this is
  safe because we still require long vertical lines & an outer bbox check.
* Re‑export everything via a single helper `iter_table_settings()` so that
  external code does *not* change.
"""

from typing import Any, Dict, Iterator, List, Tuple


# ---------------------------------------------------------------------------
# 1.  **CORE VARIANT LIST**  – extended & re‑ordered
# ---------------------------------------------------------------------------

TABLE_SETTINGS_VARIANTS: List[Tuple[str, Dict[str, Any]]] = [
    # --- ❶ 基础强规则 ------------------------------------------------------
    ("lines-lines-strong", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 1,
        "intersection_tolerance": 1,
        "join_tolerance": 4,
        "edge_min_length": 80,
        "min_words_horizontal": 4,
    }),
    # --- ❷ 框线完整但略有噪声 ----------------------------------------------
    ("lines-lines", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 6,
        "edge_min_length": 70,
    }),
    # === ★ 新增：针对窄幅大表 (case #1/#3/#4) =============================
    ("lines-lines-narrowbig", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 4,
        "intersection_tolerance": 3,
        "join_tolerance": 6,
        "edge_min_length": 70,
        "bbox_width_ratio_override": 0.25,  # see helper below
    }),
    # === ★ 新增：左右空白列 (case #1/#2/#6) ===============================
    ("lines-lines-edgeblank", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 6,
        "edge_min_length": 70,
        "min_words_vertical": 0,  # allow truly blank cols
        "min_words_horizontal": 2,
    }),
    # === ★ 新增：缺顶横线，竖线清晰 (case #3) ============================
    ("explicit-text-missingtop", {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 8,
        "text_x_tolerance": 3,
        "text_y_tolerance": 6,
        "min_words_horizontal": 2,
        "require_top_hline": False,  # helper flag only
    }),
    # --- ❸ 旧版 variants (低风险原样保留，顺序略后移) -----------------------
    ("lines-lines-lowword", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "intersection_tolerance": 2,
        "join_tolerance": 6,
        "min_words_horizontal": 2,
        "min_words_vertical": 1,
    }),
    ("lines-lines-narrow", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 2,
        "intersection_tolerance": 2,
        "join_tolerance": 6,
        "min_words_vertical": 1,
        "min_words_horizontal": 5,
    }),
    ("lines-lines-thick", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "intersection_tolerance": 1,
        "join_tolerance": 5,
        "edge_min_length": 70,
    }),
    ("lines-lines-relaxed", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 6,
        "edge_min_length": 100,
        "min_words_horizontal": 1,
        "min_words_vertical": 1,
    }),
    ("explicit-explicit", {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "explicit",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 8,
    }),
    ("explicit-lines", {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "lines",
        "snap_tolerance": 4,
        "intersection_tolerance": 2,
        "join_tolerance": 6,
        "min_words_horizontal": 4,
    }),
    ("explicit-text", {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 8,
        "text_x_tolerance": 3,
        "text_y_tolerance": 5,
        "min_words_horizontal": 5,
    }),
    ("lines-text-wide", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "text_x_tolerance": 8,
        "text_y_tolerance": 6,
        "min_words_vertical": 2,
    }),
    ("lines-text-fallback", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "intersection_tolerance": 3,
        "join_tolerance": 8,
        "text_x_tolerance": 5,
        "text_y_tolerance": 5,
        "min_words_vertical": 2,
    }),
    ("lines-text", {
        "vertical_strategy": "lines",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "text_x_tolerance": 6,
        "text_y_tolerance": 6,
        "min_words_vertical": 3,
    }),
    ("text-text", {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "text_x_tolerance": 6,
        "text_y_tolerance": 6,
        "min_words_vertical": 5,
        "min_words_horizontal": 5,
    }),
]


# ---------------------------------------------------------------------------
# 2. **ITERATOR** – keep public contract stable
# ---------------------------------------------------------------------------

def iter_table_settings() -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Yield (name, settings) in priority order.

    Consumers iterate until they find *the* variant that produces the best
    table candidate (based on their own scoring logic).  This preserves
    backward compatibility with existing extraction pipelines.
    """
    for name, cfg in TABLE_SETTINGS_VARIANTS:
        yield name, cfg


# ---------------------------------------------------------------------------
# 3. **OPTIONAL HELPER** – adaptive override flags
# ---------------------------------------------------------------------------

ADAPTIVE_OVERRIDES = dict(
    H_BIG=0.50,  # page‑width ratio – lower to catch narrow big tables
    WIDTH_RATIO=0.25,  # classify as possible big table even if bbox narrow
)


# A tiny stub showing how a caller could utilise the per‑variant extra keys.
# Actual scoring/selection lives outside this module!

def _apply_variant_overrides(variant_cfg: Dict[str, Any], page) -> Dict[str, Any]:
    """Return a copy of *variant_cfg* with any `*_override` keys resolved.

    Currently supports only **bbox_width_ratio_override** which replaces the
    default WIDTH_RATIO threshold on a per‑variant basis.
    """
    cfg = variant_cfg.copy()
    override = cfg.pop("bbox_width_ratio_override", None)
    require_top = cfg.pop("require_top_hline", None)

    # 1) narrow‑big override – cached as an attribute for external use
    if override is not None:
        cfg["_bbox_width_ratio_override"] = override
    # 2) missing top‑hline flag for downstream explicit checks
    if require_top is not None:
        cfg["_require_top_hline"] = require_top

    return cfg

# End of file – happy extracting! 🎉
