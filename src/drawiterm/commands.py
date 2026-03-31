"""Command pattern for undo/redo. All document mutations go through here."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import (
    ArrowElement,
    DiamondElement,
    Document,
    Element,
    ElementStyle,
    EllipseElement,
    RectElement,
    TextElement,
)


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
            _apply_move(e, dc, dr, document)

    def undo(self, document: Document) -> None:
        for eid, dc, dr in self.moves:
            e = document.get_by_id(eid)
            if e is None:
                continue
            _apply_move(e, -dc, -dr, document)


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
            _apply_geometry(
                e,
                self.new_col,
                self.new_row,
                self.new_width,
                self.new_height,
                document,
            )

    def undo(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None:
            _apply_geometry(
                e,
                self.old_col,
                self.old_row,
                self.old_width,
                self.old_height,
                document,
            )


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


def _apply_move(
    element: Element,
    dc: int,
    dr: int,
    document: Document | None = None,
) -> None:
    from .models import (
        ArrowElement,
        DiamondElement,
        EllipseElement,
        RectElement,
        TextElement,
    )

    if isinstance(element, (RectElement, EllipseElement, DiamondElement)):
        element.col += dc
        element.row += dr
        if document is not None:
            document.reroute_arrows_for_element(element.id)
    elif isinstance(element, TextElement):
        element.col += dc
        element.row += dr
    elif isinstance(element, ArrowElement):
        element.start_col += dc
        element.start_row += dr
        element.end_col += dc
        element.end_row += dr


def _apply_geometry(
    element: Element,
    col: int,
    row: int,
    width: int,
    height: int,
    document: Document | None = None,
) -> None:
    from .models import DiamondElement, EllipseElement, RectElement

    if isinstance(element, (RectElement, EllipseElement, DiamondElement)):
        element.col = col
        element.row = row
        element.width = width
        element.height = height
        if document is not None:
            document.reroute_arrows_for_element(element.id)


def _set_text(element: Element, text: str, is_label: bool) -> None:
    if is_label:
        element.label = text
    elif isinstance(element, TextElement):
        element.text = text


@dataclass
class DuplicateElementsCommand:
    element_ids: list[int]
    offset_col: int = 2
    offset_row: int = 2
    _clones: list[Element] = field(default_factory=list, init=False, repr=False)

    def execute(self, document: Document) -> None:
        if not self._clones:
            # First execution: create clones with new IDs
            for eid in self.element_ids:
                el = document.get_by_id(eid)
                if el is None:
                    continue
                clone = _clone_element(el, document.next_id(), self.offset_col, self.offset_row)
                self._clones.append(clone)
        for clone in self._clones:
            document.add(clone)

    def undo(self, document: Document) -> None:
        for clone in self._clones:
            document.remove(clone.id)


@dataclass
class ToggleArrowStyleCommand:
    element_id: int
    old_style: str
    new_style: str

    def execute(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None and isinstance(e, ArrowElement):
            e.arrow_style = self.new_style

    def undo(self, document: Document) -> None:
        e = document.get_by_id(self.element_id)
        if e is not None and isinstance(e, ArrowElement):
            e.arrow_style = self.old_style


def _clone_element(el: Element, new_id: int, dc: int, dr: int) -> Element:
    """Return a copy of el with new_id and position offset by (dc, dr)."""
    style = ElementStyle(fg_color=el.style.fg_color, bg_color=el.style.bg_color, bold=el.style.bold)
    if isinstance(el, RectElement):
        return RectElement(
            id=new_id,
            z_order=new_id,
            col=el.col + dc,
            row=el.row + dr,
            width=el.width,
            height=el.height,
            border_style=el.border_style,
            label=el.label,
            style=style,
        )
    if isinstance(el, EllipseElement):
        return EllipseElement(
            id=new_id,
            z_order=new_id,
            col=el.col + dc,
            row=el.row + dr,
            width=el.width,
            height=el.height,
            label=el.label,
            style=style,
        )
    if isinstance(el, ArrowElement):
        return ArrowElement(
            id=new_id,
            z_order=new_id,
            start_col=el.start_col + dc,
            start_row=el.start_row + dr,
            end_col=el.end_col + dc,
            end_row=el.end_row + dr,
            arrow_style=el.arrow_style,
            show_arrowhead=el.show_arrowhead,
            start_element_id=el.start_element_id,
            end_element_id=el.end_element_id,
            start_anchor=el.start_anchor,
            end_anchor=el.end_anchor,
            label=el.label,
            style=style,
        )
    if isinstance(el, TextElement):
        return TextElement(
            id=new_id,
            z_order=new_id,
            col=el.col + dc,
            row=el.row + dr,
            text=el.text,
            label=el.label,
            style=style,
        )
    if isinstance(el, DiamondElement):
        return DiamondElement(
            id=new_id,
            z_order=new_id,
            col=el.col + dc,
            row=el.row + dr,
            width=el.width,
            height=el.height,
            label=el.label,
            style=style,
        )
    raise ValueError(f"Cannot clone element of type {type(el).__name__}")


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
