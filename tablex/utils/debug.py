from typing import List

from PIL import ImageDraw, ImageFont


def draw_lines_on_page(page, v_lines: List[float], h_lines: List[float], color: str = "blue", stroke_width: int = 2):
    im = page.to_image(resolution=150)
    for x in v_lines:
        im.draw_line(((x, 0), (x, page.height)), stroke=color, stroke_width=stroke_width)
    for y in h_lines:
        im.draw_line(((0, y), (page.width, y)), stroke=color, stroke_width=stroke_width)
    im.show()  # 可视化展示
    return im


def draw_lines_on_page_plus(
    page, v_lines: List[float], h_lines: List[float],
    stroke_width: int = 2, text_color: str = "red",
):
    im = page.to_image()
    pil_img = im.original.copy()  # 原始 PIL 图像
    drawer = ImageDraw.Draw(pil_img)

    # 设置字体
    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except:
        font = ImageFont.load_default()

    # 垂直线
    for x in v_lines:
        drawer.line([(x, 0), (x, page.height)], fill="orangered", width=stroke_width)
        drawer.text((x + 2, 5), f"x={x:.1f}", fill=text_color, font=font)

    # 水平线
    for y in h_lines:
        drawer.line([(0, y), (page.width, y)], fill="skyblue", width=stroke_width)
        drawer.text((5, y - 10), f"y={y:.1f}", fill=text_color, font=font)

    pil_img.show()  # 显示图像
    return pil_img
