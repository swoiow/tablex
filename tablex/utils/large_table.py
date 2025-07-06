# ── 比例与容差 ─────────────────────────────────────────────
from tablex.utils.cluster import cluster
from tablex.utils.color import is_dark_and_greyscale_like


TOP_BOUNDS = (0.10, 0.18)  # 顶部判定区：10%~18%
SIDE_BOUNDS = (0.10, 0.90)  # 左右边界：10%~90%
BOTTOM_BOUNDS = (0.80, 0.92)  # 底部判定区：80%~92%
DEFAULT_TOL_RATIO = 0.015  # 容差：±1.5%


# ── 判定辅助 ─────────────────────────────────────────────
def _in_range(val: float, target: float, tol: float) -> bool:
    return abs(val - target) <= tol


def _has_dark_footer(page, left_x: float, right_x: float, tol_x: float) -> bool:
    exp_len = right_x - left_x
    for ln in page.lines:
        if abs(ln["y1"] - ln["y0"]) > 2:  # 不是水平
            continue
        length = abs(ln["x1"] - ln["x0"])
        if abs(length - exp_len) > tol_x:
            continue
        if is_dark_and_greyscale_like(ln.get("non_stroking_color", 0.0)):
            return True
    return False


def _extract_raw_lines(page, tol: float) -> tuple[list[float], list[float]]:
    """
    提取 (v_lines, h_lines)：
      - v_lines: 竖线 x 坐标（近竖直且高度≥页高25%）
      - h_lines: 横线 y 坐标（近水平且长度≥页宽70%）
    同时把 page.rects / page.curves 里满足条件的边也补进来。
    """
    W, H = page.width, page.height
    v_bucket, h_bucket = [], []

    # --- page.lines ---------------------------------------------------------
    for ln in page.lines:
        dx, dy = ln["x1"] - ln["x0"], ln["y1"] - ln["y0"]
        length = (dx * dx + dy * dy) ** 0.5
        if abs(dx) <= 2 and length >= H * 0.25:  # 竖线
            v_bucket.append(ln["x0"])
        elif abs(dy) <= 2 and length >= W * 0.70:  # 横线
            h_bucket.append(H - ln["y0"])  # 统一 y 方向

    # --- page.rects ---------------------------------------------------------
    for rc in page.rects:
        rw, rh = rc["x1"] - rc["x0"], rc["y1"] - rc["y0"]
        # 横边
        if rh <= tol and rw >= W * 0.75:
            h_bucket.extend([H - rc["y0"], H - rc["y1"]])
        # 竖边
        if rw <= tol and rh >= H * 0.35:
            v_bucket.extend([rc["x0"], rc["x1"]])

    # --- page.curves --------------------------------------------------------
    for cv in getattr(page, "curves", []):
        if abs(cv["x1"] - cv["x0"]) < 1:  # 近竖直
            v_bucket.extend([cv["x0"], cv["x1"]])
        if abs(cv["y1"] - cv["y0"]) < 1:  # 近水平
            h_bucket.extend([H - cv["y0"], H - cv["y1"]])

    return v_bucket, h_bucket


def has_large_table(page, tol_ratio: float = DEFAULT_TOL_RATIO) -> bool:
    """返回 bool：当前页是否存在“大表格”"""
    W, H = page.width, page.height
    tol_x, tol_y = W * tol_ratio, H * tol_ratio

    # --- 1. 线条抽取 + 聚类 -----------------------------------------------
    raw_v, raw_h = _extract_raw_lines(page, tol_y)
    v_lines = cluster(raw_v, tol_x)
    h_lines = cluster(raw_h, tol_y)

    # --- 2. 左右边界竖线存在？ --------------------------------------------
    left_tgt, right_tgt = W * SIDE_BOUNDS[0], W * SIDE_BOUNDS[1]
    has_left = any(_in_range(x, left_tgt, tol_x) for x in v_lines)
    has_right = any(_in_range(x, right_tgt, tol_x) for x in v_lines)
    if not (has_left and has_right):
        return False  # 规则3：左右缺失 => 不是大表格

    # --- 3. 顶/底横线存在？ ----------------------------------------------
    top_min, top_max = H * TOP_BOUNDS[0], H * TOP_BOUNDS[1]
    bot_min, bot_max = H * BOTTOM_BOUNDS[0], H * BOTTOM_BOUNDS[1]

    has_top = any((top_min - tol_y) <= y <= (top_max + tol_y) for y in h_lines)
    has_bot = any((bot_min - tol_y) <= y <= (bot_max + tol_y) for y in h_lines)

    # Rule-1：左右都有 & 顶底都有 → True
    if has_top and has_bot:
        return True

    # Rule-2：左右都有 & 顶缺失 & 底有长黑线 → True
    if (not has_top) and has_bot:
        if _has_dark_footer(page, left_tgt, right_tgt, tol_x):
            return True

    # 其他情况 → False
    return False
