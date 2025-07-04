"""
score_and_search_updated.py
===========================

Re‑implementation of **score_tables** and **search_best_table_settings**
that aligns with the _Table Settings Case Optimized_ presets and the
latest heuristics we defined for “大表” detection.

Key changes
-----------
1. **Table‑aware scoring** – combines structure metrics (rows × cols),
   page‑relative geometry (width / area ratio) and text density.
2. **Config‑driven thresholds** – pulls `AREA_RATIO` & `WIDTH_RATIO`
   from a `CONFIG` dict so they stay in sync with build_explicit_lines.
3. **Auto‑filter of small tables** – candidate settings producing only
   “小表” (< area or width ratio) are discarded early.
4. **Graceful fallback** – still iterates over `iter_table_settings()` so
   new presets from _Case Optimized_ are naturally tested.
5. **API unchanged** – signatures & return types are **100 % backward
   compatible** with legacy code.
"""

import copy
from typing import Any, Dict, List, Optional, Tuple

from tablex.lines import explicit as _extractor  # noqa: E402
from tablex.utils.table_settings import iter_table_settings  # updated list


# NB: keep a local reference, avoids re‑import cost per page
extract_explicit_lines = _extractor.extract_explicit_lines

# ------------------------------------------------------------------- #
# Configuration (must mirror CONFIG in smart_settings.py)
# ------------------------------------------------------------------- #
CONFIG: Dict[str, float] = {
    "AREA_RATIO": 0.12,  # same as CFG["AREA_RATIO"]
    "WIDTH_RATIO": 0.30,  # same as CFG["WIDTH_RATIO"]
}


def _single_table_score(tbl, page) -> float:
    """Compute a quality score for one pdfplumber Table object."""
    rows = tbl.extract()
    n_rows = len(rows)
    n_cols = max((len(r) for r in rows), default=0)

    # Structural score – encourage 3‑col grids specifically
    struct_score = n_rows * n_cols * 1.0
    if n_cols == 3:
        struct_score += 60.0  # bonus for target layout
    elif n_cols >= 4:
        struct_score += 30.0  # still a plus, but lower

    # Geometry score – based on width / area relative to page
    page_w, page_h = page.width, page.height
    x0, top, x1, bottom = tbl.bbox  # type: ignore
    width_ratio = (x1 - x0) / page_w
    area_ratio = ((x1 - x0) * (bottom - top)) / (page_w * page_h)

    geo_score = 0.0
    if width_ratio >= CONFIG["WIDTH_RATIO"]:
        geo_score += width_ratio * 120  # wide tables dominate
    if area_ratio >= CONFIG["AREA_RATIO"]:
        geo_score += area_ratio * 100

    # Text density (light weight – avoids biasing very dense paragraphs)
    text_amt = sum(len(str(c)) for r in rows for c in r)
    text_score = text_amt * 0.05

    # Oversize penalty (≥ 8×8 is usually mis‑detection of paragraphs)
    oversize = max(n_rows - 8, 0) + max(n_cols - 8, 0)
    penalty = oversize * 15.0

    return struct_score + geo_score + text_score - penalty


def score_tables(tables: List[Any], page) -> float:
    """Aggregate score for a list of tables on *one* page."""
    return round(sum(_single_table_score(tbl, page) for tbl in tables), 2)


# ------------------------------------------------------------------- #
# 2.   Search best settings for *one* page
# ------------------------------------------------------------------- #

def search_best_table_settings(
    page,
    first_page_explicit_v: Optional[List[float]] = None,
    first_page_explicit_h: Optional[List[float]] = None,
    debug: bool = 1,
) -> Tuple[
    Optional[str],
    Tuple[Optional[str], Optional[str]],
    Optional[Dict[str, Any]],
    List[Any],
    List[float],
    List[float],
]:
    """Try all preset table settings & returns the best‑scoring one.

    Returns
    -------
    (preset_name, (v_strategy, h_strategy), cfg_dict,
     tables, explicit_v, explicit_h_img)
    """
    # ––––– 1. pre‑analyse explicit lines once –––––
    explicit_v, explicit_h_img = extract_explicit_lines(page, dump_rects_log=False)
    if debug:
        print(
            f"[search] Page {page.page_number}: explicit_v={len(explicit_v)}, explicit_h_img={len(explicit_h_img)}"
        )

    best: Tuple[str, Tuple[str, str], Dict[str, Any], List[Any], List[float], List[float], float] | None = None

    # ––––– 2. enumerate presets –––––
    for name, base_cfg in iter_table_settings():

        cfg = copy.deepcopy(base_cfg)  # avoid mutating global presets
        used_v: List[float] = []
        used_h: List[float] = []

        # Inject explicit verticals if required/available
        if cfg["vertical_strategy"] == "explicit":
            if len(explicit_v) >= 2:
                used_v = explicit_v.copy()
            elif first_page_explicit_v and len(first_page_explicit_v) >= 2:
                used_v = first_page_explicit_v.copy()
            else:
                if debug:
                    print(f"[skip] {name}: need explicit_v but not found")
                continue  # cannot satisfy explicit requirement
            cfg["explicit_vertical_lines"] = used_v

        # Inject explicit horizontals (img‑coords → pdf‑coords)
        if cfg["horizontal_strategy"] == "explicit":
            if explicit_h_img:
                used_h = [page.height - y for y in explicit_h_img]
            elif first_page_explicit_h:
                used_h = first_page_explicit_h.copy()
            else:
                # downgrade to text when horizontals are missing
                cfg["horizontal_strategy"] = "text"
                cfg.setdefault("text_x_tolerance", 3)
                cfg.setdefault("text_y_tolerance", 12)
                cfg.setdefault("min_words_horizontal", 4)
            cfg["explicit_horizontal_lines"] = used_h

        # ––– 3. run detection –––
        tables = page.find_tables(table_settings=cfg)

        # filter out pages that only yield small tables
        if tables:
            biggest = max(tables, key=lambda t: (t.bbox[2] - t.bbox[0]))
            x0, top, x1, bottom = biggest.bbox  # type: ignore
            width_ratio = (x1 - x0) / page.width
            area_ratio = ((x1 - x0) * (bottom - top)) / (page.width * page.height)
            if width_ratio < CONFIG["WIDTH_RATIO"] and area_ratio < CONFIG["AREA_RATIO"]:
                if debug:
                    print(f"[skip] {name}: all tables too small (w={width_ratio:.2f}, a={area_ratio:.2f})")
                continue

        sc = score_tables(tables, page)
        if debug:
            print(f"[score] {name:25s} -> {sc:7.2f}  (v={cfg['vertical_strategy']}, h={cfg['horizontal_strategy']})")

        if best is None or sc > best[-1]:
            best = (name, (cfg["vertical_strategy"], cfg["horizontal_strategy"]), cfg, tables, used_v, used_h, sc)

    if best is None:  # no tables at all
        return None, (None, None), None, [], [], []

    name, strat, cfg, tables, ev, eh, sc = best
    if debug:
        print(f"[best] {name} – score {sc:.2f}  strategy={strat}")
    return name, strat, cfg, tables, ev, eh
