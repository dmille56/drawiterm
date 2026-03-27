"""Command pattern for undo/redo. All document mutations go through here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import Document, Element


class Command(Protocol):
    def execute(self, document: Document) -> None: ...
    def undo(self, document: Document) -> None: ...


# ---------------------------------------------------------------------------
# Concrete commands
# ---------------------------------------------------------------------------

@dataclass
class AddElementCommand:
    element: Element

    def execute(self, document: Document) -> None:
        document.add(self.element)

    def undo(self, document: Document) -> None:
        document.remove(self.element.id)


@dataclass
class DeleteElementsCommand:
    element_ids: list[int]
    _removed: list[Element] = field(default_factory=list, init=False, repr=False)

    def execute(self, document: Document) -> None:
        self._removed = []
        for eid in self.element_ids:
            e = document.remove(eid)
            if e is not None:
                self._removed.append(e)

    def undo(self, document: Document) -> None:
        for e in self._removed:
            document.add(e)


@dataclass
class MoveElementsCommand:
    moves: list[tuple[int, int, int]]  # (element_id, delta_col, delta_row)

    def execute(self, document: Document) -> None:
        for eid, dc, dr in self.moves:
            e = document.get_by_id(eid)
            if e is None:
                continue
            _apply_move(e, dc, dr)

    def undo(self, document: Document) -> None:
        for eid, dc, dr in self.moves:
            e = document.get_by_id(eid)
            if e is None:
                continue
            _apply_move(e, -dc, -dr)


@dataclass
class ResizeElementCommand:
    element_id: int
    old_col: int
    old_row: int
    old_width: int
    old_height: int
    new_col: int
    new_row: int
    new_width: int
    new_height: int

    def execute(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None:
            _apply_geometry(e, self.new_col, self.new_row, self.new_width, self.new_height)

    def undo(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None:
            _apply_geometry(e, self.old_col, self.old_row, self.old_width, self.old_height)


@dataclass
class EditTextCommand:
    element_id: int
    old_text: str
    new_text: str
    _is_label: bool = False  # True = editing element.label, False = TextElement.text

    def execute(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None:
            _set_text(e, self.new_text, self._is_label)

    def undo(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None:
            _set_text(e, self.old_text, self._is_label)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_move(element: Element, dc: int, dr: int) -> None:
    from .models import RectElement, EllipseElement, TextElement, ArrowElement
    if isinstance(element, (RectElement, EllipseElement)):
        element.col += dc
        element.row += dr
    elif isinstance(element, TextElement):
        element.col += dc
        element.row += dr
    elif isinstance(element, ArrowElement):
        element.start_col += dc
        element.start_row += dr
        element.end_col += dc
        element.end_row += dr


def _apply_geometry(element: Element, col: int, row: int, width: int, height: int) -> None:
    from .models import RectElement, EllipseElement
    if isinstance(element, (RectElement, EllipseElement)):
        element.col = col
        element.row = row
        element.width = width
        element.height = height


def _set_text(element: Element, text: str, is_label: bool) -> None:
    from .models import TextElement
    if is_label:
        element.label = text
    elif isinstance(element, TextElement):
        element.text = text


# ---------------------------------------------------------------------------
# UndoStack
# ---------------------------------------------------------------------------

class UndoStack:
    def __init__(self, max_depth: int = 50) -> None:
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self.max_depth = max_depth

    def push(self, command: Command, document: Document) -> None:
        command.execute(document)
        self._undo.append(command)
        if len(self._undo) > self.max_depth:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, document: Document) -> bool:
        if not self._undo:
            return False
        cmd = self._undo.pop()
        cmd.undo(document)
        self._redo.append(cmd)
        return True

    def redo(self, document: Document) -> bool:
        if not self._redo:
            return False
        cmd = self._redo.pop()
        cmd.execute(document)
        self._undo.append(cmd)
        return True

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)
