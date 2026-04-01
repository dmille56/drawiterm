from drawiterm.commands import Command, UndoStack
from drawiterm.models import Document


class Dummy(Command):
    def __init__(self, name: str) -> None:
        self.name = name
        self.did: list[str] = []

    def execute(self, d: Document) -> None:
        self.did.append("do")

    def undo(self, d: Document) -> None:
        self.did.append("undo")


def test_redo_cleared_on_new_push():
    s = UndoStack()
    doc = Document()
    a = Dummy("a")
    b = Dummy("b")
    s.push(a, doc)
    assert s.can_undo and not s.can_redo
    assert s.undo(doc) is True
    assert s.can_redo
    s.push(b, doc)
    assert not s.can_redo


def test_max_depth_drops_oldest():
    s = UndoStack(max_depth=1)
    doc = Document()
    a = Dummy("a")
    b = Dummy("b")
    s.push(a, doc)
    s.push(b, doc)
    # Only b remains undoable
    assert s.undo(doc) is True  # undoes b
    assert s.undo(doc) is False  # a was dropped
