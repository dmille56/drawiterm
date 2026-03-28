from drawiterm.painter import make_grid, grid_set, _paint_text_element, _STYLE_WHITE
from drawiterm.models import TextElement, Viewport


def test_make_grid_and_grid_set():
    g = make_grid(3, 4)
    assert len(g) == 3
    assert len(g[0]) == 4
    grid_set(g, 1, 2, "x", _STYLE_WHITE)
    assert g[2][1].char == "x"


def test_paint_text_element_writes_chars():
    g = make_grid(3, 8)
    vp = Viewport(col_offset=0, row_offset=0, terminal_width=8, terminal_height=3)
    el = TextElement(id=1, col=1, row=0, text="ok\n!")
    _paint_text_element(g, el, vp, _STYLE_WHITE)
    assert g[0][1].char == "o"
    assert g[1][1].char == "!"
