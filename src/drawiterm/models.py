"""Core data model: elements, document, viewport."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

# ---------------------------------------------------------------------------
# Canvas constants
# ---------------------------------------------------------------------------

CANVAS_WIDTH = 500
CANVAS_HEIGHT = 200


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

@dataclass
class ElementStyle:
    fg_color: str = "default"
    bg_color: str = "default"
    bold: bool = False

    def to_dict(self) -> dict:
        return {"fg_color": self.fg_color, "bg_color": self.bg_color, "bold": self.bold}

    @staticmethod
    def from_dict(d: dict) -> "ElementStyle":
        return ElementStyle(
            fg_color=d.get("fg_color", "default"),
            bg_color=d.get("bg_color", "default"),
            bold=d.get("bold", False),
        )


# ---------------------------------------------------------------------------
# Element base + subtypes
# ---------------------------------------------------------------------------

@dataclass
class Element:
    id: int
    element_type: str
    z_order: int = 0
    label: str = ""
    style: ElementStyle = field(default_factory=ElementStyle)

    def bounding_box(self) -> tuple[int, int, int, int]:
        """Return (col, row, width, height). Subclasses override."""
        raise NotImplementedError

    def contains_point(self, col: int, row: int) -> bool:
        c, r, w, h = self.bounding_box()
        return c <= col < c + w and r <= row < r + h

    def to_dict(self) -> dict:
        raise NotImplementedError

    @staticmethod
    def from_dict(d: dict) -> "Element":
        t = d["element_type"]
        if t == "rect":
            return RectElement.from_dict(d)
        if t == "ellipse":
            return EllipseElement.from_dict(d)
        if t == "arrow":
            return ArrowElement.from_dict(d)
        if t == "text":
            return TextElement.from_dict(d)
        raise ValueError(f"Unknown element_type: {t!r}")


@dataclass
class RectElement(Element):
    element_type: str = field(default="rect", init=False)
    col: int = 0
    row: int = 0
    width: int = 10
    height: int = 5
    border_style: str = "single"  # "single" | "double" | "rounded"

    def bounding_box(self) -> tuple[int, int, int, int]:
        return self.col, self.row, self.width, self.height

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "z_order": self.z_order,
            "label": self.label,
            "style": self.style.to_dict(),
            "col": self.col,
            "row": self.row,
            "width": self.width,
            "height": self.height,
            "border_style": self.border_style,
        }

    @staticmethod
    def from_dict(d: dict) -> "RectElement":
        e = RectElement(
            id=d["id"],
            z_order=d.get("z_order", 0),
            label=d.get("label", ""),
            style=ElementStyle.from_dict(d.get("style", {})),
            col=d.get("col", 0),
            row=d.get("row", 0),
            width=d.get("width", 10),
            height=d.get("height", 5),
            border_style=d.get("border_style", "single"),
        )
        return e


@dataclass
class EllipseElement(Element):
    element_type: str = field(default="ellipse", init=False)
    col: int = 0
    row: int = 0
    width: int = 10
    height: int = 5

    def bounding_box(self) -> tuple[int, int, int, int]:
        return self.col, self.row, self.width, self.height

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "z_order": self.z_order,
            "label": self.label,
            "style": self.style.to_dict(),
            "col": self.col,
            "row": self.row,
            "width": self.width,
            "height": self.height,
        }

    @staticmethod
    def from_dict(d: dict) -> "EllipseElement":
        return EllipseElement(
            id=d["id"],
            z_order=d.get("z_order", 0),
            label=d.get("label", ""),
            style=ElementStyle.from_dict(d.get("style", {})),
            col=d.get("col", 0),
            row=d.get("row", 0),
            width=d.get("width", 10),
            height=d.get("height", 5),
        )


@dataclass
class ArrowElement(Element):
    element_type: str = field(default="arrow", init=False)
    start_col: int = 0
    start_row: int = 0
    end_col: int = 10
    end_row: int = 0
    arrow_style: str = "orthogonal"  # "orthogonal" | "straight"
    start_element_id: int | None = None
    end_element_id: int | None = None

    def bounding_box(self) -> tuple[int, int, int, int]:
        c = min(self.start_col, self.end_col)
        r = min(self.start_row, self.end_row)
        w = max(abs(self.end_col - self.start_col), 1)
        h = max(abs(self.end_row - self.start_row), 1)
        return c, r, w, h

    def contains_point(self, col: int, row: int) -> bool:
        # Arrow hit test: check if point is on any cell of the arrow path
        for pc, pr in _orthogonal_arrow_cells(
            self.start_col, self.start_row, self.end_col, self.end_row
        ):
            if pc == col and pr == row:
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "z_order": self.z_order,
            "label": self.label,
            "style": self.style.to_dict(),
            "start_col": self.start_col,
            "start_row": self.start_row,
            "end_col": self.end_col,
            "end_row": self.end_row,
            "arrow_style": self.arrow_style,
            "start_element_id": self.start_element_id,
            "end_element_id": self.end_element_id,
        }

    @staticmethod
    def from_dict(d: dict) -> "ArrowElement":
        return ArrowElement(
            id=d["id"],
            z_order=d.get("z_order", 0),
            label=d.get("label", ""),
            style=ElementStyle.from_dict(d.get("style", {})),
            start_col=d.get("start_col", 0),
            start_row=d.get("start_row", 0),
            end_col=d.get("end_col", 10),
            end_row=d.get("end_row", 0),
            arrow_style=d.get("arrow_style", "orthogonal"),
            start_element_id=d.get("start_element_id"),
            end_element_id=d.get("end_element_id"),
        )


@dataclass
class TextElement(Element):
    element_type: str = field(default="text", init=False)
    col: int = 0
    row: int = 0
    text: str = ""

    def bounding_box(self) -> tuple[int, int, int, int]:
        lines = self.text.split("\n") if self.text else [""]
        w = max((len(l) for l in lines), default=1)
        h = len(lines)
        return self.col, self.row, max(w, 1), max(h, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "z_order": self.z_order,
            "label": self.label,
            "style": self.style.to_dict(),
            "col": self.col,
            "row": self.row,
            "text": self.text,
        }

    @staticmethod
    def from_dict(d: dict) -> "TextElement":
        return TextElement(
            id=d["id"],
            z_order=d.get("z_order", 0),
            label=d.get("label", ""),
            style=ElementStyle.from_dict(d.get("style", {})),
            col=d.get("col", 0),
            row=d.get("row", 0),
            text=d.get("text", ""),
        )


def _orthogonal_arrow_cells(
    sc: int, sr: int, ec: int, er: int
) -> list[tuple[int, int]]:
    """Return the list of (col, row) cells that an orthogonal arrow occupies."""
    cells: list[tuple[int, int]] = []
    # L-shape: horizontal first, then vertical
    mid_col = ec
    mid_row = sr
    # horizontal segment
    step = 1 if ec >= sc else -1
    for c in range(sc, ec + step, step):
        cells.append((c, sr))
    # vertical segment (skip start of second segment to avoid duplicate)
    step = 1 if er >= sr else -1
    for r in range(sr + step, er + step, step):
        cells.append((ec, r))
    return cells


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

@dataclass
class Document:
    schema_version: int = 1
    title: str = "Untitled"
    elements: list[Element] = field(default_factory=list)
    _next_id: int = field(default=1, init=False, repr=False)

    def __post_init__(self) -> None:
        # Ensure _next_id is above any existing element ids
        if self.elements:
            self._next_id = max(e.id for e in self.elements) + 1

    def next_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def add(self, element: Element) -> Element:
        self.elements.append(element)
        return element

    def remove(self, element_id: int) -> Element | None:
        for i, e in enumerate(self.elements):
            if e.id == element_id:
                return self.elements.pop(i)
        return None

    def get_by_id(self, element_id: int) -> Element | None:
        for e in self.elements:
            if e.id == element_id:
                return e
        return None

    def get_at(self, col: int, row: int) -> list[Element]:
        """Hit-test: return all elements whose bounding box contains (col, row), back-to-front."""
        return [e for e in self.elements if e.contains_point(col, row)]

    def elements_in_rect(
        self, col: int, row: int, width: int, height: int
    ) -> list[Element]:
        """Return elements whose bounding box overlaps the given rect."""
        result = []
        for e in self.elements:
            ec, er, ew, eh = e.bounding_box()
            if ec < col + width and ec + ew > col and er < row + height and er + eh > row:
                result.append(e)
        return result

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "elements": [e.to_dict() for e in self.elements],
        }

    @staticmethod
    def from_dict(d: dict) -> "Document":
        elements = [Element.from_dict(ed) for ed in d.get("elements", [])]
        doc = Document(
            schema_version=d.get("schema_version", 1),
            title=d.get("title", "Untitled"),
            elements=elements,
        )
        return doc


# ---------------------------------------------------------------------------
# Viewport
# ---------------------------------------------------------------------------

@dataclass
class Viewport:
    col_offset: int = 0
    row_offset: int = 0
    terminal_width: int = 80
    terminal_height: int = 24

    def to_canvas(self, term_col: int, term_row: int) -> tuple[int, int]:
        return term_col + self.col_offset, term_row + self.row_offset

    def to_terminal(self, canvas_col: int, canvas_row: int) -> tuple[int, int]:
        return canvas_col - self.col_offset, canvas_row - self.row_offset

    def is_visible(self, canvas_col: int, canvas_row: int) -> bool:
        tc, tr = self.to_terminal(canvas_col, canvas_row)
        return 0 <= tc < self.terminal_width and 0 <= tr < self.terminal_height

    def clamp(self) -> None:
        """Keep viewport within canvas bounds."""
        self.col_offset = max(0, min(self.col_offset, CANVAS_WIDTH - self.terminal_width))
        self.row_offset = max(0, min(self.row_offset, CANVAS_HEIGHT - self.terminal_height))
