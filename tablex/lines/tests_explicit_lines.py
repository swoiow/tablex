import pdfplumber
from PIL import ImageDraw, ImageFont

from tablex import extract_explicit_lines


def draw_line(img, xy, color="black", width=3):
    draw = ImageDraw.Draw(img)
    draw.line(xy, fill=color, width=width)


def annotate(img, xy, text, color="black", size=12):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except:
        font = ImageFont.load_default()
    draw.text(xy, text, fill=color, font=font)


pdf_path = r"1.pdf"
with pdfplumber.open(pdf_path) as pdf:
    for idx, page in enumerate(pdf.pages, start=1):
        prev_v, prev_h_img = extract_explicit_lines(page, dump_rects_log=False)

        print(f"\n--- Page {idx} ---")
        H, W = page.height, page.width
        img = page.to_image(resolution=100)
        pil_img = img.original  # PIL.Image 对象

        # === 计算 pt 到 px 的缩放因子 ===
        scale_x = pil_img.width / W
        scale_y = pil_img.height / H


        # === 工具函数：将 pt 坐标转换为 px 坐标 ===
        def px(x, y):
            return (x * scale_x, y * scale_y)


        # ========= 顶部线条 =========
        y_top_min = H * 0.10
        y_top_max = H * 0.18
        draw_line(pil_img, [px(0, y_top_min), px(W, y_top_min)], color="purple", width=3)
        draw_line(pil_img, [px(0, y_top_max), px(W, y_top_max)], color="purple", width=3)
        annotate(pil_img, px(10, y_top_min + 2), "top bound: 10%", color="purple")
        annotate(pil_img, px(10, y_top_max + 2), "top bound: 18%", color="purple")

        # ========= 左右边界线 =========
        x_side_min = W * 0.10
        x_side_max = W * 0.90
        draw_line(pil_img, [px(x_side_min, 0), px(x_side_min, H)], color="green", width=3)
        draw_line(pil_img, [px(x_side_max, 0), px(x_side_max, H)], color="green", width=3)
        annotate(pil_img, px(x_side_min + 2, 10), "left bound: 10%", color="green")
        annotate(pil_img, px(x_side_max + 2, 10), "right bound: 90%", color="green")

        # ========= 底部线条 =========
        y_bottom_min = H * 0.80
        y_bottom_max = H * 0.92
        draw_line(pil_img, [px(0, y_bottom_min), px(W, y_bottom_min)], color="purple", width=3)
        draw_line(pil_img, [px(0, y_bottom_max), px(W, y_bottom_max)], color="purple", width=3)
        annotate(pil_img, px(10, y_bottom_min + 2), "bottom bound: 80%", color="purple")
        annotate(pil_img, px(10, y_bottom_max + 2), "bottom bound: 92%", color="purple")

        # ========= 显示图像 =========
        pil_img.show()

        print()
