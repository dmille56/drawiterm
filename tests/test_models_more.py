from drawiterm.models import Document, RectElement, Viewport


def test_get_at_orders_by_area_then_z():
    small = RectElement(id=1, z_order=1, col=0, row=0, width=3, height=3)
    big = RectElement(id=2, z_order=0, col=0, row=0, width=10, height=10)
    doc = Document(elements=[small, big])
    hits = doc.get_at(1, 1)
    assert hits[-1].id == small.id


def test_viewport_clamp_within_canvas():
    vp = Viewport(col_offset=10_000, row_offset=10_000, terminal_width=80, terminal_height=24)
    vp.clamp()
    assert 0 <= vp.col_offset <= 500 - 80
    assert 0 <= vp.row_offset <= 200 - 24
