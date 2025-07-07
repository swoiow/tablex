from typing import Any, Iterable, List, Optional, Tuple

from tablex.utils.cluster import cluster
from tablex.utils.color import is_dark_and_greyscale_like
from tablex.utils.debug import draw_lines_on_page_plus


class ExplicitLineExtractor:
    """Explicit line extractor that allows overriding page primitives."""

    def __init__(
        self,
        cluster_tol: float = 10,
        use_color_filter: bool = True,
        dump_rects_log: bool = True,
    ) -> None:
        self.cluster_tol = cluster_tol
        self.use_color_filter = use_color_filter
        self.dump_rects_log = dump_rects_log

    def extract(
        self,
        page,
        *,
        page_lines: Optional[Iterable[Any]] = None,
        page_rects: Optional[Iterable[Any]] = None,
        page_curves: Optional[Iterable[Any]] = None,
        dump_explicit: bool = False,
    ) -> Tuple[List[float], List[float]]:
        """Return clustered explicit vertical and horizontal lines."""

        cluster_tol = self.cluster_tol

        print(f"[INFO] === Page {page.page_number} Start ===")

        raw_v: List[float] = []
        raw_h: List[float] = []

        # Step 1: 提取 page.lines 中结构性线段
        ev0, eh0 = extract_lines_from_page_lines(page, lines=page_lines)
        raw_v.extend(ev0)
        raw_h.extend(eh0)

        # Step 2: 提取 page.rects 中结构性边框
        ev1, eh1 = extract_lines_from_page_rects(
            page,
            use_color_filter=self.use_color_filter,
            dump_log=self.dump_rects_log,
            rects=page_rects,
        )
        raw_v.extend(ev1)
        raw_h.extend(eh1)

        # Step 3: 提取 page.curves 中近似直线
        ev2, eh2 = extract_lines_from_page_curves(page, curves=page_curves)
        raw_v.extend(ev2)
        raw_h.extend(eh2)

        # Step 4: 坐标聚类处理，合并相近位置的线段
        explicit_v = sorted(cluster(raw_v, cluster_tol=cluster_tol))
        explicit_h = sorted(cluster(raw_h, cluster_tol=cluster_tol))

        # Step 5: 判断是否缺少顶部横线，必要时补全
        explicit_h_pdf_top = ensure_header_line(page, explicit_h, explicit_v, cluster_tol)
        explicit_h2 = sorted(cluster(explicit_h + explicit_h_pdf_top, cluster_tol=cluster_tol))

        print(f"[INFO] explicit_v={explicit_v}; explicit_h={explicit_h2}")
        print(f"[INFO] === Page {page.page_number} End ===")
        if dump_explicit:
            draw_lines_on_page_plus(page, explicit_v, explicit_h2)

        if (not explicit_v) or (not explicit_h2):
            ev0, eh0 = extract_lines_from_page_lines(page, plus=True)
            raw_v.extend(ev0)
            raw_h.extend(eh0)
            explicit_v = sorted(cluster(raw_v, cluster_tol=cluster_tol))
            explicit_h2 = sorted(cluster(raw_h, cluster_tol=cluster_tol))
            print("兼容")

        return explicit_v, explicit_h2


def extract_explicit_lines(
    page,
    cluster_tol: float = 10,
    use_color_filter: bool = True,
    dump_rects_log: bool = True,
    dump_explicit: bool = False,
    *,
    page_lines: Optional[Iterable[Any]] = None,
    page_rects: Optional[Iterable[Any]] = None,
    page_curves: Optional[Iterable[Any]] = None,
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
    extractor = ExplicitLineExtractor(
        cluster_tol=cluster_tol,
        use_color_filter=use_color_filter,
        dump_rects_log=dump_rects_log,
    )
    return extractor.extract(
        page,
        page_lines=page_lines,
        page_rects=page_rects,
        page_curves=page_curves,
        dump_explicit=dump_explicit,
    )


def extract_lines_from_page_lines(
    page,
    lines: Optional[Iterable[Any]] = None,
    plus=False,
) -> tuple[list[Any], list[Any]]:
    """
    提取 page.lines 中结构性横线（长）和竖线（高），返回坐标列表。
    横线条件：接近水平且长度 > 页宽 70%；竖线条件：接近竖直且高度 > 页高 25%
    """
    W, H = page.width, page.height
    bucket_v, bucket_h = [], []
    lines = list(page.lines if lines is None else lines)
    for l in lines:
        dx, dy = l["x1"] - l["x0"], l["y1"] - l["y0"]
        length = (dx ** 2 + dy ** 2) ** 0.5  # 计算线段长度
        if abs(dy) <= 2 and length >= W * 0.70:
            # TODO|<TASK1>: 究竟是用 l["y0"] 还是 H - l["y0"] 这是个谜
            bucket_h.append(H - l["y0"])  # 保留水平线 y 坐标
        elif abs(dx) <= 2 and length >= H * 0.25:
            bucket_v.append(l["x0"])  # 保留竖直线 x 坐标

    if plus:  # 通过edges获取边框, 非必要
        try:
            if not bucket_h:
                edge_h = [l["bottom"] for l in page.rects]
                bucket_h = [max(edge_h), min(edge_h)]
            if not bucket_v:
                edge_v = [l["x0"] for l in page.rects]
                bucket_v = [max(edge_v), min(edge_v)]
        except ValueError:
            raise RuntimeWarning("警告：此页没有表格！")
    return bucket_v, bucket_h


def extract_lines_from_page_rects(
    page,
    use_color_filter: bool = True,
    dump_log: bool = True,
    simple_draw=False,
    power_draw=False,
    *,
    rects: Optional[Iterable[Any]] = None,
) -> tuple[list[Any], list[Any]]:
    """
    提取 page.rects 中的结构线（粗竖线或长横线），返回坐标列表。
    条件：横线高度较小且长度 ≥ 页宽 75%；竖线宽度较小且高度 ≥ 页高 35%
    """
    W, H = page.width, page.height
    bucket_v, bucket_h = [], []
    rects = list(page.rects if rects is None else rects)
    if dump_log:
        print(f"[DEBUG] page.rects：\n{rects}\n")

    for ix, r in enumerate(page.rects):
        rw, rh = r["x1"] - r["x0"], r["y1"] - r["y0"]  # 计算矩形宽高
        color = r.get("non_stroking_color", 0.0)
        if dump_log and (simple_draw or power_draw):
            print([rw, rh], r["x0"], r["y0"], r["x1"], r["y1"])

        if simple_draw:
            im = page.to_image().draw_rect(r, stroke="blue", fill="red")
            # im.show()
        elif power_draw:
            bbox = (r["x0"], r["top"], r["x1"], r["bottom"])  # 注意y轴方向不同
            im = page.to_image()
            im.draw.rectangle(bbox, outline="red", width=3)
            # im.show()

        if use_color_filter and (not is_dark_and_greyscale_like(color)):
            continue  # 跳过非黑色边框

        # 策略1,使用debug决定：没有效果
        #     if (0.5 <= rh) and (rw >= W * 0.55):
        #         bucket_h.extend([r["y0"], r["y1"]])  # 横线 y 坐标
        #     elif (0.5 <= rw) and (rh >= H * 0.35):
        #         bucket_v.extend([r["x0"], r["x1"]])  # 竖线 x 坐标
        # return bucket_v, bucket_h

        # 策略2,使用debug决定：page.rects属于点-线融合
        # TODO|<TASK1>: 究竟是用 [r["y0"], r["y1"]] 还是 [H - r["y0"], H - r["y1"]] 这是个谜
        bucket_h.extend([H - r["y0"], H - r["y1"]])  # 横线 y 坐标
        bucket_v.extend([r["x0"], r["x1"]])  # 竖线 x 坐标
    return cluster(bucket_v), cluster(bucket_h)


def extract_lines_from_page_curves(
    page,
    curves: Optional[Iterable[Any]] = None,
) -> tuple[list[Any], list[Any]]:
    """
    提取 page.curves 中近似水平或竖直的曲线段，返回坐标列表。
    """
    curves = list(getattr(page, "curves", []) if curves is None else curves)
    print(f"[DEBUG] page.curves：\n{curves}\n")
    bucket_v, bucket_h = [], []
    for c in curves:
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
    # 底部判断器，使用 draw_lines_on_page_plus(page, v_lines=[], h_lines=[y_min, y_max])
    # y_min, y_max = H * 0.80, H * 0.95
    # footer_missing = all(not (y_min <= y <= y_max) for y in explicit_h)

    # 顶部判断器，使用 draw_lines_on_page_plus(page, v_lines=[], h_lines=[y_min, y_max])
    y_min, y_max = H * 0.1, H * 0.2
    header_missing = all(not (y_min <= y <= y_max) for y in explicit_h)
    print(f"[DEBUG] 表头线缺失：{header_missing}")

    if not header_missing or not explicit_h:
        return []

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
            return sorted(cluster(explicit_h, cluster_tol=cluster_tol))

    if page.rects:
        r_max = max(page.rects, key=lambda r: (r["x1"] - r["x0"]) * (r["y1"] - r["y0"]))
        fallback_y = r_max["y1"]  # 表示最大矩形的底边位置
        print(f"[INFO] Fallback: Use max rect y1={fallback_y:.2f} as header line")
        explicit_h.append(fallback_y)
        return sorted(cluster(explicit_h, cluster_tol=cluster_tol))

    if not explicit_h and explicit_v:
        limit = explicit_v[1] if len(explicit_v) > 1 else explicit_v[0]
        col_chars = [c for c in page.chars if c["x0"] <= limit]
        if col_chars:
            inferred_line = max(c["bottom"] for c in col_chars) + 1.0
            print(f"[INFO] Fallback line from char bottom: {inferred_line:.2f}")
            return [inferred_line]

    return explicit_h
