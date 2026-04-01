from drawiterm.models import Document, RectElement, Viewport
from drawiterm.painter import CanvasPainter, SelectionState, ToolPreviewState, make_grid


def test_paint_rect_draws_corners():
    doc = Document()
    r = RectElement(id=doc.next_id(), z_order=1, col=1, row=1, width=4, height=3)
    doc.add(r)
    vp = Viewport(col_offset=0, row_offset=0, terminal_width=10, terminal_height=6)
    grid = make_grid(vp.terminal_height, vp.terminal_width)
    CanvasPainter.paint(doc, vp, SelectionState(), ToolPreviewState(), grid)
    # Top-left corner at (1,1), top-right at (4,1) in terminal coords
    assert grid[1][1].char == "┌"
    assert grid[1][4].char == "┐"
