from typing import Any, List, Tuple, Union


def extract_explicit_lines(
    page,
    cluster_tol: float = 8,
    use_color_filter: bool = True,
    dump_rects_log: bool = True,
) -> Tuple[List[float], List[float]]:
    """
    主函数：融合提取结构性竖线/横线，并返回聚类后的 explicit_v/h。

    输入：
        - page: pdfplumber 的页面对象
        - cluster_tol: 坐标聚类容差
        - use_color_filter: 是否使用颜色过滤，仅保留近黑色线
        - dump_rects_log: 是否输出 rects 调试信息

    输出：
        - explicit_v: 所有聚类后的竖线位置（升序）
        - explicit_h: 所有聚类后的横线位置（升序）
    """
    print(f"[INFO] === Page {page.page_number} Start ===")

    raw_v: List[float] = []
    raw_h: List[float] = []

    # Step 1: 提取 page.lines 中结构性线段
    ev, eh = extract_lines_from_page_lines(page)
    raw_v.extend(ev)
    raw_h.extend(eh)

    # Step 2: 提取 page.rects 中结构性边框
    ev, eh = extract_lines_from_page_rects(page, use_color_filter, dump_rects_log)
    raw_v.extend(ev)
    raw_h.extend(eh)

    # Step 3: 提取 page.curves 中近似直线
    ev, eh = extract_lines_from_page_curves(page)
    raw_v.extend(ev)
    raw_h.extend(eh)

    # Step 4: 坐标聚类处理，合并相近位置的线段
    explicit_v = sorted(_cluster(raw_v, cluster_tol=cluster_tol))
    explicit_h_pdf = sorted(_cluster(raw_h, cluster_tol=cluster_tol))

    # Step 5: 判断是否缺少顶部横线，必要时补全
    explicit_h_pdf = ensure_header_line(page, explicit_h_pdf, explicit_v, cluster_tol)

    print(f"[INFO] === Page {page.page_number} End ===")
    return explicit_v, explicit_h_pdf


def extract_lines_from_page_lines(page) -> tuple[list[Any], list[Any]]:
    """
    提取 page.lines 中结构性横线（长）和竖线（高），返回坐标列表。
    横线条件：接近水平且长度 > 页宽 75%；竖线条件：接近竖直且高度 > 页高 35%
    """
    W, H = page.width, page.height
    bucket_v, bucket_h = [], []
    for l in page.lines:
        dx, dy = l["x1"] - l["x0"], l["y1"] - l["y0"]
        length = (dx ** 2 + dy ** 2) ** 0.5  # 计算线段长度
        if abs(dy) < 1 and length >= W * 0.75:
            bucket_h.append(l["y0"])  # 保留水平线 y 坐标
        elif abs(dx) < 1 and length >= H * 0.35:
            bucket_v.append(l["x0"])  # 保留竖直线 x 坐标
    return bucket_v, bucket_h


def extract_lines_from_page_rects(
    page,
    use_color_filter: bool,
    dump_log: bool,
) -> tuple[list[Any], list[Any]]:
    """
    提取 page.rects 中的结构线（粗竖线或长横线），返回坐标列表。
    条件：横线高度较小且长度 ≥ 页宽 75%；竖线宽度较小且高度 ≥ 页高 35%
    """
    W, H = page.width, page.height
    bucket_v, bucket_h = [], []
    if dump_log:
        print(f"[DEBUG] page.rects:\n{page.rects}\n")

    for r in page.rects:
        rw, rh = r["x1"] - r["x0"], r["y1"] - r["y0"]  # 计算矩形宽高
        color = r.get("non_stroking_color", 0.0)
        if use_color_filter and not is_near_black(color):
            continue  # 跳过非黑色边框

        if rh >= 1.5 and rw >= W * 0.75:
            bucket_h.extend([r["y0"], r["y1"]])  # 横线 y 坐标
        elif rw >= 1.5 and rh >= H * 0.35:
            bucket_v.extend([r["x0"], r["x1"]])  # 竖线 x 坐标
    return bucket_v, bucket_h


def extract_lines_from_page_curves(page) -> tuple[list[Any], list[Any]]:
    """
    提取 page.curves 中近似水平或竖直的曲线段，返回坐标列表。
    """
    print(f"[DEBUG] page.curves:\n{page.curves}\n")
    bucket_v, bucket_h = [], []
    for c in getattr(page, "curves", []):
        if abs(c["x1"] - c["x0"]) < 1:
            bucket_v.extend([c["x0"], c["x1"]])  # 近似竖线
        if abs(c["y1"] - c["y0"]) < 1:
            bucket_h.extend([c["y0"], c["y1"]])  # 近似横线
    return bucket_v, bucket_h


def ensure_header_line(
    page,
    explicit_h: List[float],
    explicit_v: List[float],
    cluster_tol: float,
) -> List[float]:
    """
    检查是否缺失表头横线，若缺失则通过：
      1）底部线长度 + 左上角矩形构造 header；
      2）使用最大矩形底部而不是顶部；
      3）第一列文字 bottom 推断
    """
    H = page.height
    y_min, y_max = H * 0.80, H * 0.95  # 顶部区域判断范围

    header_missing = all(not (y_min <= y <= y_max) for y in explicit_h)
    print(f"[DEBUG] Header line missing: {header_missing}")

    if not header_missing or not explicit_h:
        return explicit_h

    bottom_y = min(explicit_h)  # 底部横线位置
    bottom_len = None
    for l in page.lines:
        if abs(l["y0"] - bottom_y) < cluster_tol:
            dx, dy = l["x1"] - l["x0"], l["y1"] - l["y0"]
            bottom_len = (dx ** 2 + dy ** 2) ** 0.5  # 计算底部线段长度
            break

    if bottom_len:
        print(f"[INFO] Found bottom line length = {bottom_len:.2f}")
    else:
        print(f"[WARN] Failed to find bottom line length")

    if bottom_len:
        left_rect = min(page.rects, key=lambda r: r["x0"], default=None)
        if left_rect:
            header_y = left_rect["y1"]
            header_x = left_rect["x0"]
            print(f"[INFO] Use rect(x={header_x:.2f}, y={header_y:.2f}) + len={bottom_len:.2f} to synth header")
            explicit_h.append(header_y)
            return sorted(_cluster(explicit_h, cluster_tol=cluster_tol))

    if page.rects:
        r_max = max(page.rects, key=lambda r: (r["x1"] - r["x0"]) * (r["y1"] - r["y0"]))
        fallback_y = r_max["y1"]  # 表示最大矩形的底边位置
        print(f"[INFO] Fallback: Use max rect y1={fallback_y:.2f} as header line")
        explicit_h.append(fallback_y)
        return sorted(_cluster(explicit_h, cluster_tol=cluster_tol))

    if not explicit_h and explicit_v:
        limit = explicit_v[1] if len(explicit_v) > 1 else explicit_v[0]
        col_chars = [c for c in page.chars if c["x0"] <= limit]
        if col_chars:
            inferred_line = max(c["bottom"] for c in col_chars) + 1.0
            print(f"[INFO] Fallback line from char bottom: {inferred_line:.2f}")
            return [inferred_line]

    return explicit_h


def _cluster(coords: List[float], cluster_tol: float = 8.0) -> List[float]:
    """
    聚类：将相近坐标归并成一个值（取均值）。如 x=[10, 11, 12, 50]，tol=5 -> 聚为两个中心点
    """
    if not coords:
        return []
    coords = sorted(coords)
    clusters = []
    group = [coords[0]]
    for c in coords[1:]:
        if abs(c - group[-1]) <= cluster_tol:
            group.append(c)
        else:
            clusters.append(sum(group) / len(group))
            group = [c]
    clusters.append(sum(group) / len(group))
    return clusters


def is_near_black(color: Union[float, int, Tuple[float, ...], List[float]], threshold: float = 0.2) -> bool:
    """
    判断颜色是否接近黑色：支持灰度值或 RGB 元组。默认阈值为 0.2。
    """
    if isinstance(color, (int, float)):
        return color < threshold
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return all(c < threshold for c in color[:3])
    return False
