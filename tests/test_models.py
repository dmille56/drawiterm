from drawiterm.models import TextElement, _orthogonal_arrow_cells


def test_text_bounding_box_simple():
    t = TextElement(id=1, col=2, row=3, text="hi")
    assert t.bounding_box() == (2, 3, 2, 1)


def test_text_bounding_box_multiline():
    t = TextElement(id=1, col=0, row=0, text="a\nbc\n")
    # trailing newline produces an empty last line -> width should be max(len) == 2, height == 3
    assert t.bounding_box() == (0, 0, 2, 3)


def test_orthogonal_arrow_cells_horizontal():
    cells = _orthogonal_arrow_cells(0, 0, 3, 0)
    assert cells == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_orthogonal_arrow_cells_corner_h_then_v():
    cells = _orthogonal_arrow_cells(0, 0, 2, 2)
    # If wider or equal, expect H→V routing (0,0)->(2,0)->(2,2)
    assert cells[0] == (0, 0)
    assert (2, 0) in cells
    assert (2, 2) in cells
