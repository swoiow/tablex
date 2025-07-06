# TableX

基于 [pdfplumber](https://github.com/jsvine/pdfplumber) 的表格提取工具包，
提供对 PDF 页面的结构线分析、候选表格评分以及多套表格设置搜索。

```python
from tablex import (
    extract_explicit_lines,
    search_best_table_settings,
    ExplicitLineExtractor,
)
```

## 快速上手

```python
import pdfplumber
from tablex import search_best_table_settings

with pdfplumber.open("sample.pdf") as pdf:
    page = pdf.pages[0]
    name, strategy, cfg, tables, v_lines, h_lines = search_best_table_settings(page)
    if tables:
        first_table = tables[0]
        print(first_table.extract())
```

## 项目结构

- **`tablex.lines`** – 显式线段提取。`extract_explicit_lines` 会依次处理
  `page.lines`、`rects` 与 `curves`，通过聚类获得稳定的竖线/横线坐标，
  并在必要时推断缺失的表头线。
- **`tablex.scoring`** – 表格评分与设置搜索。`search_best_table_settings`
  会遍历 `utils.table_settings` 中的多套预设，对每个结果计算结构分数、
  几何分数及文本密度，最终返回得分最高的配置及表格列表。
- **`tablex.utils`** – 辅助工具与配置，包括坐标聚类、颜色判断、调试绘图
  以及表格设置迭代器等。

## 提取流程概览

1. **显式线检测**：`extract_explicit_lines` 对页内的直线、矩形和曲线进行
   过滤和聚类，得到可能的表格边界位置。
2. **枚举表格设置**：`search_best_table_settings` 根据预设参数组合
   调用 `page.find_tables`，并对每个结果执行 `score_tables` 计算质量分。
3. **选择最佳表格**：按得分从高到低选择最合适的设置和表格，返回其
   配置、显式线以及表格内容。

更多示例和细节可参见各模块源码。希望该工具能够帮助你从 PDF
文档中更准确地提取表格结构。
