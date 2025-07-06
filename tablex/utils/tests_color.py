import pathlib
import sys


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from tablex.utils.color import is_near_black, is_dark_color, is_dark_and_greyscale_like


@pytest.mark.parametrize("value,expected", [
    (0.1, True),
    (0.3, False),
])
def test_is_near_black_gray(value, expected):
    assert is_near_black(value) is expected


@pytest.mark.parametrize("color,expected", [
    ((0.05, 0.1, 0.18), True),
    ((0.21, 0.1, 0.1), False),
])
def test_is_near_black_rgb(color, expected):
    assert is_near_black(color) is expected


@pytest.mark.parametrize("value,expected", [
    (0.4, True),
    (0.5, False),
])
def test_is_dark_color_gray(value, expected):
    assert is_dark_color(value) is expected


@pytest.mark.parametrize(
    "color,expected",
    [
        ((0.0, 0.0, 0.0), True),
        ((1.0, 1.0, 1.0), False),
        ((0.4, 0.4, 0.2), True),
        ((0.5, 0.5, 0.5), False),
    ],
)
def test_is_dark_color_rgb(color, expected):
    assert is_dark_color(color) is expected


@pytest.mark.parametrize("value,expected", [
    (0.4, True),
    (0.6, False),
])
def test_is_dark_and_greyscale_like_gray(value, expected):
    assert is_dark_and_greyscale_like(value) is expected


@pytest.mark.parametrize(
    "color,expected",
    [
        ((0.3, 0.32, 0.28), True),  # dark and grey like
        ((0.6, 0.6, 0.6), False),  # greyscale but not dark
        ((0.3, 0.4, 0.3), False),  # dark but color deviation > tol
    ],
)
def test_is_dark_and_greyscale_like_rgb(color, expected):
    assert is_dark_and_greyscale_like(color) is expected
