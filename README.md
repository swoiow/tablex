# TableX

基于 pdfplumber 的表格提取工具包。

```
from tablex import extract_explicit_lines, search_best_table_settings, ExplicitLineExtractor
```

- `tablex.lines` 提供显式线段提取函数
  - 可使用 `ExplicitLineExtractor` 自定义 `page.lines`/`rects`/`curves`
- `tablex.scoring` 负责表格打分与最佳设置搜索
- `tablex.utils` 包含聚类、调试与预设配置
