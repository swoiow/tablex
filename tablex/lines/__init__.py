"""Line extraction utilities.

This package exposes the default explicit line extractor and helpers.
"""

from .explicit import (
    ExplicitLineExtractor,
    extract_explicit_lines,
    extract_lines_from_page_lines,
    extract_lines_from_page_rects,
    extract_lines_from_page_curves,
    ensure_header_line,
)

__all__ = [
    "extract_explicit_lines",
    "ExplicitLineExtractor",
    "extract_lines_from_page_lines",
    "extract_lines_from_page_rects",
    "extract_lines_from_page_curves",
    "ensure_header_line",
]
