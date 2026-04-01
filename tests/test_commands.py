from drawiterm.commands import (
    AddElementCommand,
    DeleteElementsCommand,
    DuplicateElementsCommand,
    EditTextCommand,
    MoveElementsCommand,
    ResizeElementCommand,
    ToggleArrowStyleCommand,
    UndoStack,
)
from drawiterm.models import ArrowElement, Document, RectElement, TextElement


def test_add_and_undo():
    doc = Document()
    s = UndoStack()
    el = RectElement(id=doc.next_id(), z_order=1, col=1, row=1, width=4, height=3)
    s.push(AddElementCommand(el), doc)
    assert doc.get_by_id(el.id) is not None
    assert s.can_undo and not s.can_redo
    assert s.undo(doc) is True
    assert doc.get_by_id(el.id) is None
    assert s.can_redo


def test_delete_and_undo():
    doc = Document()
    s = UndoStack()
    el = RectElement(id=doc.next_id(), z_order=1, col=0, row=0, width=3, height=3)
    s.push(AddElementCommand(el), doc)
    s.push(DeleteElementsCommand([el.id]), doc)
    assert doc.get_by_id(el.id) is None
    assert s.undo(doc) is True
    assert doc.get_by_id(el.id) is not None


def test_move_and_undo():
    doc = Document()
    s = UndoStack()
    el = RectElement(id=doc.next_id(), z_order=1, col=1, row=1, width=3, height=2)
    s.push(AddElementCommand(el), doc)
    s.push(MoveElementsCommand([(el.id, 2, 3)]), doc)
    assert (el.col, el.row) == (3, 4)
    assert s.undo(doc) is True
    assert (el.col, el.row) == (1, 1)


def test_resize_and_undo():
    doc = Document()
    s = UndoStack()
    el = RectElement(id=doc.next_id(), z_order=1, col=1, row=1, width=3, height=3)
    s.push(AddElementCommand(el), doc)
    s.push(ResizeElementCommand(el.id, 1, 1, 3, 3, 2, 2, 6, 5), doc)
    assert el.bounding_box() == (2, 2, 6, 5)
    assert s.undo(doc) is True
    assert el.bounding_box() == (1, 1, 3, 3)


def test_edit_text_and_undo_for_text_element():
    doc = Document()
    s = UndoStack()
    t = TextElement(id=doc.next_id(), z_order=1, col=0, row=0, text="a")
    s.push(AddElementCommand(t), doc)
    s.push(EditTextCommand(t.id, "a", "hello", _is_label=False), doc)
    assert t.text == "hello"
    assert s.undo(doc) is True
    assert t.text == "a"


def test_edit_label_and_undo_for_shape():
    doc = Document()
    s = UndoStack()
    r = RectElement(id=doc.next_id(), z_order=1, col=0, row=0, width=4, height=3, label="")
    s.push(AddElementCommand(r), doc)
    s.push(EditTextCommand(r.id, "", "LBL", _is_label=True), doc)
    assert r.label == "LBL"
    assert s.undo(doc) is True
    assert r.label == ""


def test_duplicate_and_undo():
    doc = Document()
    s = UndoStack()
    r = RectElement(id=doc.next_id(), z_order=1, col=1, row=1, width=4, height=3)
    s.push(AddElementCommand(r), doc)
    cmd = DuplicateElementsCommand([r.id], offset_col=2, offset_row=2)
    s.push(cmd, doc)
    clones = [e for e in doc.elements if e.id != r.id]
    assert len(clones) == 1
    c = clones[0]
    assert (c.col, c.row) == (r.col + 2, r.row + 2)
    assert s.undo(doc) is True
    assert doc.get_by_id(c.id) is None


def test_toggle_arrow_style_and_undo():
    doc = Document()
    s = UndoStack()
    a = ArrowElement(
        id=doc.next_id(),
        z_order=1,
        start_col=0,
        start_row=0,
        end_col=5,
        end_row=0,
        arrow_style="orthogonal",
    )
    s.push(AddElementCommand(a), doc)
    s.push(ToggleArrowStyleCommand(a.id, "orthogonal", "straight"), doc)
    assert a.arrow_style == "straight"
    assert s.undo(doc) is True
    assert a.arrow_style == "orthogonal"
