import heapq
from dataclasses import dataclass
from typing import Any, List, Tuple

from tablex.utils.cluster import cluster
from tablex.utils.color import _is_white, is_dark_and_greyscale_like
from tablex.utils.debug import draw_lines_on_page_plus  # noqa


DEBUG = 0


def div(a: float, b: float = 1.0) -> float:
    """安全除法并四舍五入"""
    return round(a / b, 5) if b != 0 else 0.0


@dataclass(slots=True)
class BoundConfig:
    top: Tuple[float, float] = (0.10, 0.22)
    side: Tuple[float, float] = (0.10, 0.90)
    bottom: Tuple[float, float] = (0.80, 0.92)
    tol_ratio: float = 0.015
    dx_tol: float = 2.0
    dy_tol: float = 2.0


CFG = BoundConfig()


def _extract_raw_lines(page, cfg: BoundConfig = CFG) -> Tuple[List[float], List[float]]:
    """提取所有结构线段（直线、rect、curve）的横纵坐标点"""
    H = page.height
    v_bucket, h_bucket = [], []

    if DEBUG:
        print(f"[DEBUG] _extract_raw_lines：页面高度={H}")

    # 从 lines 中提取竖线和横线
    for ln in page.lines:
        dx, dy = ln["x1"] - ln["x0"], ln["y1"] - ln["y0"]
        if abs(dx) <= cfg.dx_tol:
            v_bucket.append(div(ln["x0"]))
        if abs(dy) <= cfg.dy_tol:
            h_bucket.append(div(H - ln["y0"]))

    if DEBUG:
        print(f"[DEBUG] 线条数量={len(page.lines)}，竖线候选={len(v_bucket)}，横线候选={len(h_bucket)}")

    # 从 rect 中提取左右、上下边界
    for rc in page.rects:
        v_bucket.extend([div(rc["x0"]), div(rc["x1"])])
        h_bucket.extend([div(H - rc["y0"]), div(H - rc["y1"])])

    if DEBUG:
        print(f"[DEBUG] 矩形贡献{len(page.rects) * 2}个坐标")

    # 从 curves 中提取结构线
    for cv in getattr(page, "curves", []):
        if abs(cv["x1"] - cv["x0"]) <= cfg.dx_tol:
            v_bucket.extend([div(cv["x0"]), div(cv["x1"])])
        if abs(cv["y1"] - cv["y0"]) <= cfg.dy_tol:
            h_bucket.extend([div(H - cv["y0"]), div(H - cv["y1"])])

    if DEBUG:
        print(f"[DEBUG] Curves：原始 v_bucket 总数={len(v_bucket)}，原始 h_bucket={len(h_bucket)}")
        print(f"[DEBUG] raw_h 值（排序后）：{sorted(h_bucket)}")

    return v_bucket, h_bucket


def _collect_vertical_edges(page, cfg: BoundConfig = CFG) -> List[Tuple[float, float]]:
    """收集所有垂直边（含高度信息）"""
    edges = []
    H = page.height

    if DEBUG:
        print(f"[DEBUG] _collect_vertical_edges：页面高度={H}")

    for ln in page.lines:
        if abs(ln["x1"] - ln["x0"]) <= cfg.dx_tol:
            edges.append((div(ln["x0"]), div(abs(ln["y1"] - ln["y0"]))))

    if DEBUG:
        print(f"[DEBUG] Lines：收集自{len(page.lines)}条线")

    for rc in page.rects:
        height = div(rc["y1"] - rc["y0"])
        edges.extend([(div(rc["x0"]), height), (div(rc["x1"]), height)])

    if DEBUG:
        print(f"[DEBUG] Rects：收集自{len(page.rects)}个矩形，总计={len(edges)}")

    for cv in getattr(page, "curves", []):
        if abs(cv["x1"] - cv["x0"]) <= cfg.dx_tol:
            edges.append((div(cv["x0"]), div(abs(cv["y1"] - cv["y0"]))))

    if DEBUG:
        print(f"[DEBUG] Curves：垂直边总数={len(edges)}")

    return edges


def _iter_h_edges_with_y(page, cfg: BoundConfig):
    """遍历所有水平边缘，返回 y 坐标、长度和颜色"""
    H = page.height

    for ln in page.lines:
        if abs(ln["y1"] - ln["y0"]) <= cfg.dy_tol:
            y_pt = div(H - ln["y0"])
            length = div(abs(ln["x1"] - ln["x0"]))
            color = ln.get("non_stroking_color") or ln.get("stroking_color", 0.0)
            yield y_pt, length, color

    for rc in page.rects:
        for y_raw in (rc["y0"], rc["y1"]):
            y_pt = div(H - y_raw)
            length = div(rc["x1"] - rc["x0"])
            color = rc.get("non_stroking_color") or rc.get("stroking_color", 0.0)
            yield y_pt, length, color

    for cv in getattr(page, "curves", []):
        if abs(cv["y1"] - cv["y0"]) <= cfg.dy_tol:
            y_pt = div(H - cv["y0"])
            length = div(abs(cv["x1"] - cv["x0"]))
            color = cv.get("stroking_color", 0.0)
            yield y_pt, length, color


def _has_dark_longline(page, exp_len: float, cfg: BoundConfig, y_band: Tuple[float, float]) -> bool:
    """判断 y_band 区域内是否存在一条黑灰长横线"""
    H = page.height
    tol_len = div(exp_len * cfg.tol_ratio)
    y_min, y_max = y_band
    tol_y = div(H * cfg.tol_ratio)

    def y_ok(y_pt: float) -> bool:
        return (y_min - tol_y) <= y_pt <= (y_max + tol_y)

    for y_pt, length, color in _iter_h_edges_with_y(page, cfg):
        if y_ok(y_pt):
            if DEBUG:
                print(f"[DEBUG] 边@{y_pt}：长度={length}，颜色={color}")
            if abs(length - exp_len) <= tol_len and is_dark_and_greyscale_like(color):
                print("[DEBUG] 找到符合条件的黑色长横线")
                return True

    print("[DEBUG] 未找到符合条件的黑色长横线")
    return False


def _vertical_top_aligned(page, left_x: float, right_x: float, cfg: BoundConfig) -> bool:
    """检查左右边界的顶部是否对齐（避免底部误判为大表）"""
    H = page.height
    tol_x = div(page.width * cfg.tol_ratio)
    tol_y = div(H * cfg.tol_ratio)
    heap_left, heap_right = [], []

    def try_push(x_ref, x_val, y0, heap):
        if abs(x_val - x_ref) <= tol_x:
            heapq.heappush(heap, div(H - y0))

    for ln in page.lines:
        if abs(ln["x1"] - ln["x0"]) <= cfg.dx_tol:
            try_push(left_x, ln["x0"], ln["y0"], heap_left)
            try_push(right_x, ln["x0"], ln["y0"], heap_right)

    for rc in page.rects:
        for x_val in (rc["x0"], rc["x1"]):
            try_push(left_x, x_val, rc["y0"], heap_left)
            try_push(right_x, x_val, rc["y0"], heap_right)

    for cv in getattr(page, "curves", []):
        if abs(cv["x1"] - cv["x0"]) <= cfg.dx_tol:
            try_push(left_x, cv["x0"], cv["y0"], heap_left)
            try_push(right_x, cv["x0"], cv["y0"], heap_right)

    if heap_left and heap_right:
        diff = abs(heap_left[0] - heap_right[0])
        aligned = diff <= tol_y
        if DEBUG:
            print(f"[DEBUG] 顶部对齐差值={diff}，是否对齐={aligned}")
        return aligned

    print("[DEBUG] 用于顶部对齐的线迹不足")
    return False


def has_large_table(page, cfg: BoundConfig = CFG) -> bool:
    """主入口函数：判断页面是否含有较大的表格结构"""
    W, H = page.width, page.height
    tol_x, tol_y = div(W * cfg.tol_ratio), div(H * cfg.tol_ratio)

    raw_v, raw_h = _extract_raw_lines(page, cfg)
    v_lines = cluster(raw_v, tol_x)
    h_lines = cluster(raw_h, tol_y)

    edges = _collect_vertical_edges(page, cfg)
    if not edges:
        print("[DEBUG] 无边线：提前结束")
        return False

    max_h = max(h for _, h in edges)
    h_thr = div(max_h * (1 - cfg.tol_ratio))
    left_thr, right_thr = div(W * cfg.side[0]), div(W * cfg.side[1])

    # 利用 virtual_v 合并靠近的竖线高度信息
    tol_x = div(W * cfg.tol_ratio)
    virtual_v = cluster([x for x, _ in edges] + v_lines, tol_x)
    virtual_edges: List[Tuple[float, float]] = []
    for x_cluster in virtual_v:
        nearby_h = [h for x, h in edges if abs(x - x_cluster) <= tol_x]
        if not nearby_h:
            continue
        max_h_cluster = max(nearby_h)
        virtual_edges.append((x_cluster, max_h_cluster))
    edges.extend(virtual_edges)

    has_left = any(x <= left_thr and h >= h_thr for x, h in edges)
    has_right = any(x >= right_thr and h >= max_h * 0.35 for x, h in edges)

    if not (has_left and has_right):
        print("[DEBUG] 两边没有线段")
        return False

    left_x = min(x for x, h in edges if x <= left_thr and h >= h_thr)
    right_x = max(x for x, h in edges if x >= right_thr and h >= max_h * 0.35)
    exp_len = div(right_x - left_x)

    top_min, top_max = div(H * cfg.top[0]), div(H * cfg.top[1])
    bot_min, bot_max = div(H * cfg.bottom[0]), div(H * cfg.bottom[1])

    has_top = any((top_min - tol_y) <= y <= (top_max + tol_y) for y in h_lines)
    has_bot = any((bot_min - tol_y) <= y <= (bot_max + tol_y) for y in h_lines)

    # 情况 1：左右 + 顶部
    if has_left and has_right and has_top:
        return True

    # 情况 2：顶部 + 底部
    if has_top and has_bot:
        return True

    # 情况 3：只有顶部时的 fallback 检查
    if has_top and not has_bot:
        max_cluster_y = max(h_lines)
        if max_cluster_y > top_max + tol_y:
            for y_pt, length, color in _iter_h_edges_with_y(page, cfg):
                if abs(y_pt - max_cluster_y) <= tol_y and is_dark_and_greyscale_like(color):
                    if DEBUG:
                        print(f"[DEBUG] 回退：聚类底部黑线于 y={y_pt}")
                    return True

        max_top = max(y for y in h_lines if y <= top_max + tol_y)
        y_band = (max_top, bot_max)
        if _has_dark_longline(page, exp_len, cfg, y_band):
            return True

    # 情况 4：只有底部时，检查左右边是否顶部对齐
    if has_bot and not has_top:
        print("[DEBUG] 仅出现底部：检查左右对齐")

        if _vertical_top_aligned(page, left_x, right_x, cfg):
            return True

    print("[DEBUG] 最后返回False")
    return False


def get_large_table_vlines(page, cfg: BoundConfig = CFG) -> List[float]:
    """获取大表格的竖线（x 坐标）"""

    # 1. 获取所有竖线边缘
    edges = _collect_vertical_edges(page, cfg)
    if not edges:
        return []

    # 2. 过滤出接近最高的线条
    max_h = max(h for _, h in edges)
    h_thr = div(max_h * (1 - cfg.tol_ratio))
    tall = [(x, h) for x, h in edges if h >= h_thr]
    if len(tall) < 2:
        return []

    tol_x = div(page.width * cfg.tol_ratio)
    left_x = min(x for x, _ in tall)
    right_x = max(x for x, _ in tall)

    # 3. 只保留主要左右边界之间的线
    xs = [x for x, _ in tall if (left_x - tol_x) <= x <= (right_x + tol_x)]

    # 4. 聚类合并相近线条并排序
    return sorted(cluster(xs, tol_x))


def get_horizon_edges(
    page,
    cfg: BoundConfig = CFG,
) -> List[Tuple[float, float, Any]]:
    """
    收集页面中所有“非白色”水平线。

    返回值
    ----
    List[Tuple[y_pt, length, color]]
        • y_pt   : 以页面左下角为原点时的 y 坐标（已经经过 div 归一化）
        • length : 线段长度（经过 div 归一化，与源码保持一致）
        • color  : 原始颜色对象，便于后续调试或进一步分类
    """
    # 利用现有生成器抽取所有水平线
    h_edges = [
        (y_pt, length, color)
        for y_pt, length, color in _iter_h_edges_with_y(page, cfg)
        if not _is_white(color)
    ]

    # 按 y 坐标从小到大排序，方便查看
    h_edges.sort(key=lambda t: t[0])
    return h_edges


def get_large_table_hlines(page, cfg: BoundConfig = CFG, do_fallback=False) -> List[float]:
    min_line_ratio = 0.875 if (not do_fallback) else 0.75
    result = set()

    raw_v, raw_h = _extract_raw_lines(page, cfg)
    v_lines = cluster(raw_v)
    min_x, max_x = min(v_lines), max(v_lines)
    # draw_lines_on_page_plus(page,v_lines=[min_x, max_x],h_lines=[])
    min_table_width = div(max_x - min_x) * min_line_ratio

    for y, length, color in _iter_h_edges_with_y(page, cfg):
        if (length > min_table_width) and (not _is_white(color)):
            result.add(y)

    r = sorted(cluster(result))
    return r
