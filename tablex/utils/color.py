from typing import Any, List, Tuple, Union


def is_near_black(color: Union[float, int, Tuple[float, ...], List[float]], threshold: float = 0.2) -> bool:
    """
    判断颜色是否接近黑色：支持灰度值或 RGB 元组。默认阈值为 0.2。
    """
    if isinstance(color, (int, float)):
        return color < threshold
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return all(c < threshold for c in color[:3])
    return False


def is_dark_color(
    color: Union[float, int, Tuple[float, ...], List[float]],
    lum_thresh: float = 0.45,
) -> bool:
    """
    判断颜色是否为“深色边框”：
        • 灰度值：直接比较
        • RGB：使用相对亮度 (WCAG) 公式
    """
    if isinstance(color, (int, float)):
        return color < lum_thresh
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        r, g, b = color[:3]
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return luminance < lum_thresh
    return False


def is_dark_and_greyscale_like(
    color: Union[float, int, Tuple[float, ...], List[float]],
    lum_thresh: float = 0.45,
    grey_tol: float = 0.05,
) -> bool:
    """Return True for nearly-black or grey-scale colors.

    Parameters
    ----------
    color:
        Either a grayscale value or RGB tuple in the range ``[0, 1]``.
    lum_thresh:
        Maximum luminance considered dark.
    grey_tol:
        Allowed channel deviation to still be treated as greyscale.
    """
    if isinstance(color, (int, float)):
        return color < lum_thresh

    if isinstance(color, (tuple, list)) and len(color) >= 3:
        r, g, b = color[:3]

        if max(abs(r - g), abs(g - b), abs(b - r)) > grey_tol:
            return False

        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return luminance < lum_thresh

    return False


def _is_white(color: Any, thr: float = 0.9) -> bool:
    """
    判断颜色是否接近白色。

    pdfplumber 的颜色表示可能是：
      • 0-1 之间的灰度值（float / int）
      • RGB 三元组 (r, g, b)，每个分量 0-1
      • None（极少出现，表示使用当前绘图颜色），此处统一视为“非白”
    参数
    ----
    color : Any
        pdfplumber 提取到的颜色对象
    thr : float
        判断“接近白色”的阈值，默认 0.95
    """
    if color is None:
        return False
    if isinstance(color, (int, float)):
        return color >= thr
    if isinstance(color, (list, tuple)):
        return all(c >= thr for c in color)
    return False
