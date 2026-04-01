from drawiterm.commands import UndoStack
from drawiterm.models import Document, RectElement
from drawiterm.painter import SelectionState, ToolPreviewState
from drawiterm.tool_controller import Tool, ToolController


def test_draw_rectangle_via_drag():
    doc = Document()
    sel = SelectionState()
    prev = ToolPreviewState()
    s = UndoStack()
    ctrl = ToolController()
    ctrl.set_tool(Tool.RECT)
    assert ctrl.on_mouse_down(1, 1, 1, doc, s, sel, prev) is True
    assert ctrl.on_mouse_move(5, 4, 1, doc, s, sel, prev) is True
    assert ctrl.on_mouse_up(5, 4, 1, doc, s, sel, prev) is True
    rects = [e for e in doc.elements if isinstance(e, RectElement)]
    assert len(rects) == 1
    assert rects[0].width >= 3 and rects[0].height >= 3


def test_toggle_arrow_style_with_tab():
    doc = Document()
    sel = SelectionState()
    prev = ToolPreviewState()
    s = UndoStack()
    ctrl = ToolController()
    ctrl.set_tool(Tool.ARROW)
    ctrl.on_mouse_down(0, 0, 1, doc, s, sel, prev)
    ctrl.on_mouse_move(5, 0, 1, doc, s, sel, prev)
    ctrl.on_mouse_up(5, 0, 1, doc, s, sel, prev)
    assert sel.selected_ids  # arrow should be selected after creation
    assert ctrl.on_key("tab", doc, s, sel, prev) is True


def test_ctrl_a_selects_all():
    doc = Document()
    s = UndoStack()
    sel = SelectionState()
    prev = ToolPreviewState()
    r1 = RectElement(id=doc.next_id(), z_order=1, col=0, row=0, width=3, height=3)
    r2 = RectElement(id=doc.next_id(), z_order=2, col=5, row=0, width=3, height=3)
    doc.add(r1)
    doc.add(r2)
    ctrl = ToolController()
    assert ctrl.on_key("ctrl+a", doc, s, sel, prev) is True
    assert sel.selected_ids == {r1.id, r2.id}
