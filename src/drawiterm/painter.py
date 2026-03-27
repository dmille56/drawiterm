"""CanvasPainter: stateless renderer. Converts Document + state → CellGrid."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import NamedTuple

from rich.style import Style
from rich.text import Text

from .models import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    ArrowElement,
    Document,
    Element,
    EllipseElement,
    RectElement,
    TextElement,
    Viewport,
)

# ---------------------------------------------------------------------------
# Cell / CellGrid
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    char: str = " "
    style: Style = field(default_factory=Style)


CellGrid = list[list[Cell]]  # [row][col]


def make_grid(rows: int, cols: int) -> CellGrid:
    return [[Cell() for _ in range(cols)] for _ in range(rows)]


def grid_set(grid: CellGrid, col: int, row: int, char: str, style: Style) -> None:
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        grid[row][col] = Cell(char, style)


# ---------------------------------------------------------------------------
# Box-drawing characters
# ---------------------------------------------------------------------------

SINGLE = {
    "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
    "h": "─", "v": "│",
    "t": "┬", "b": "┴", "l": "├", "r": "┤", "x": "┼",
}
DOUBLE = {
    "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
    "h": "═", "v": "║",
    "t": "╦", "b": "╩", "l": "╠", "r": "╣", "x": "╬",
}
ROUNDED = {
    "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
    "h": "─", "v": "│",
    "t": "┬", "b": "┴", "l": "├", "r": "┤", "x": "┼",
}
BORDER_CHARS = {"single": SINGLE, "double": DOUBLE, "rounded": ROUNDED}

ARROW_HEADS = {"E": "►", "W": "◄", "N": "▲", "S": "▼"}
ARROW_CORNERS = {
    ("E", "S"): "┐", ("E", "N"): "┘",
    ("W", "S"): "┌", ("W", "N"): "└",
    ("S", "E"): "└", ("S", "W"): "┘",
    ("N", "E"): "┌", ("N", "W"): "┐",
}

# ---------------------------------------------------------------------------
# Selection / tool state passed to painter
# ---------------------------------------------------------------------------

@dataclass
class SelectionState:
    selected_ids: set[int] = field(default_factory=set)
    rubber_band: tuple[int, int, int, int] | None = None  # col,row,w,h in canvas coords


@dataclass
class ToolPreviewState:
    """Ghost preview of in-progress draw operation."""
    element: Element | None = None  # provisional element not yet in Document


# ---------------------------------------------------------------------------
# Main painter
# ---------------------------------------------------------------------------

class CanvasPainter:
    @staticmethod
    def paint(
        document: Document,
        viewport: Viewport,
        selection: SelectionState,
        preview: ToolPreviewState,
    ) -> CellGrid:
        rows = viewport.terminal_height
        cols = viewport.terminal_width
        grid = make_grid(rows, cols)

        # Paint background grid dots (subtle)
        _paint_background(grid, viewport)

        # Paint elements in z_order
        for element in sorted(document.elements, key=lambda e: e.z_order):
            _paint_element(grid, element, viewport, Style())

        # Paint ghost preview
        if preview.element is not None:
            ghost_style = Style(dim=True, color="cyan")
            _paint_element(grid, preview.element, viewport, ghost_style)

        # Paint selection overlay
        if selection.selected_ids:
            sel_style = Style(color="bright_cyan", bold=True)
            for eid in selection.selected_ids:
                el = document.get_by_id(eid)
                if el is not None:
                    _paint_selection_handles(grid, el, viewport, sel_style)

        # Paint rubber-band selection rect
        if selection.rubber_band is not None:
            _paint_rubber_band(grid, selection.rubber_band, viewport)

        return grid


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

def _paint_background(grid: CellGrid, viewport: Viewport) -> None:
    dot_style = Style(color="grey23")
    for tr in range(viewport.terminal_height):
        for tc in range(viewport.terminal_width):
            cc, cr = viewport.to_canvas(tc, tr)
            if cc % 5 == 0 and cr % 5 == 0:
                grid_set(grid, tc, tr, "·", dot_style)


# ---------------------------------------------------------------------------
# Element dispatch
# ---------------------------------------------------------------------------

def _paint_element(
    grid: CellGrid,
    element: Element,
    viewport: Viewport,
    override_style: Style,
) -> None:
    if isinstance(element, RectElement):
        _paint_rect(grid, element, viewport, override_style)
    elif isinstance(element, EllipseElement):
        _paint_ellipse(grid, element, viewport, override_style)
    elif isinstance(element, ArrowElement):
        _paint_arrow(grid, element, viewport, override_style)
    elif isinstance(element, TextElement):
        _paint_text_element(grid, element, viewport, override_style)


# ---------------------------------------------------------------------------
# Rectangle
# ---------------------------------------------------------------------------

def _paint_rect(
    grid: CellGrid,
    el: RectElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    bc = BORDER_CHARS.get(el.border_style, SINGLE)
    base_style = override_style if override_style.color else Style(color="white")

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, base_style)

    c, r, w, h = el.col, el.row, el.width, el.height
    if w < 2 or h < 2:
        return

    # Corners
    put(c, r, bc["tl"])
    put(c + w - 1, r, bc["tr"])
    put(c, r + h - 1, bc["bl"])
    put(c + w - 1, r + h - 1, bc["br"])

    # Top/bottom edges
    for x in range(c + 1, c + w - 1):
        put(x, r, bc["h"])
        put(x, r + h - 1, bc["h"])

    # Left/right edges
    for y in range(r + 1, r + h - 1):
        put(c, y, bc["v"])
        put(c + w - 1, y, bc["v"])

    # Label
    if el.label and w > 2 and h > 2:
        _paint_label_in_box(grid, el.label, c + 1, r + 1, w - 2, h - 2, viewport, base_style)


def _paint_label_in_box(
    grid: CellGrid,
    label: str,
    inner_col: int,
    inner_row: int,
    inner_w: int,
    inner_h: int,
    viewport: Viewport,
    style: Style,
) -> None:
    lines = label.split("\n")
    # Vertically center
    start_row = inner_row + max(0, (inner_h - len(lines)) // 2)
    for i, line in enumerate(lines):
        tr_row = start_row + i
        if tr_row >= inner_row + inner_h:
            break
        # Truncate and horizontally center
        if len(line) > inner_w:
            line = line[: inner_w - 1] + "…"
        start_col = inner_col + max(0, (inner_w - len(line)) // 2)
        for j, ch in enumerate(line):
            tc, tr = viewport.to_terminal(start_col + j, tr_row)
            grid_set(grid, tc, tr, ch, style)


# ---------------------------------------------------------------------------
# Ellipse
# ---------------------------------------------------------------------------

def _paint_ellipse(
    grid: CellGrid,
    el: EllipseElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else Style(color="white")
    c, r, w, h = el.col, el.row, el.width, el.height
    if w < 2 or h < 2:
        return

    cx = c + w / 2.0 - 0.5
    cy = r + h / 2.0 - 0.5
    a = w / 2.0
    b = h / 2.0

    # Draw perimeter using midpoint algorithm approximation
    perimeter_cells: set[tuple[int, int]] = set()
    for col in range(c, c + w):
        for row in range(r, r + h):
            nx = (col - cx) / a
            ny = (row - cy) / b
            dist = nx * nx + ny * ny
            # Accept cells close to the ellipse boundary
            if 0.6 <= dist <= 1.35:
                perimeter_cells.add((col, row))

    for pc, pr in perimeter_cells:
        tc, tr = viewport.to_terminal(pc, pr)
        grid_set(grid, tc, tr, "o", base_style)

    # Label centered
    if el.label and w > 2 and h > 2:
        inner_w = max(1, w - 4)
        inner_h = max(1, h - 2)
        inner_c = c + (w - inner_w) // 2
        inner_r = r + (h - inner_h) // 2
        _paint_label_in_box(grid, el.label, inner_c, inner_r, inner_w, inner_h, viewport, base_style)


# ---------------------------------------------------------------------------
# Arrow
# ---------------------------------------------------------------------------

def _paint_arrow(
    grid: CellGrid,
    el: ArrowElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else Style(color="yellow")
    sc, sr, ec, er = el.start_col, el.start_row, el.end_col, el.end_row

    if el.arrow_style == "straight":
        _paint_straight_arrow(grid, sc, sr, ec, er, viewport, base_style)
    else:
        _paint_orthogonal_arrow(grid, sc, sr, ec, er, viewport, base_style)


def _paint_orthogonal_arrow(
    grid: CellGrid,
    sc: int, sr: int, ec: int, er: int,
    viewport: Viewport,
    style: Style,
) -> None:
    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, style)

    if sc == ec and sr == er:
        return

    # Determine arrowhead direction
    if er == sr:
        head_dir = "E" if ec > sc else "W"
    elif ec == sc:
        head_dir = "S" if er > sr else "N"
    else:
        # Bend: horizontal first, then vertical
        head_dir = "S" if er > sr else "N"

    # Horizontal segment
    h_step = 1 if ec >= sc else -1
    for col in range(sc, ec + h_step, h_step):
        if col == sc and sr == er:
            continue
        put(col, sr, "─")

    if sr != er:
        # Corner at (ec, sr)
        if sc != ec:
            if er > sr:
                corner = "┐" if ec > sc else "┌"
            else:
                corner = "┘" if ec > sc else "└"
            put(ec, sr, corner)

        # Vertical segment
        v_step = 1 if er >= sr else -1
        v_start = sr + v_step if sc != ec else sr
        for row in range(v_start, er, v_step):
            put(ec, row, "│")

    # Arrowhead at destination
    put(ec, er, ARROW_HEADS[head_dir])


def _paint_straight_arrow(
    grid: CellGrid,
    sc: int, sr: int, ec: int, er: int,
    viewport: Viewport,
    style: Style,
) -> None:
    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, style)

    # Bresenham's line
    dx = abs(ec - sc)
    dy = abs(er - sr)
    sx = 1 if ec > sc else -1
    sy = 1 if er > sr else -1
    x, y = sc, sr
    err = dx - dy
    cells = []
    while True:
        cells.append((x, y))
        if x == ec and y == er:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

    for i, (cc, cr) in enumerate(cells):
        if i == len(cells) - 1:
            # Arrowhead
            if dx >= dy:
                ch = "►" if ec > sc else "◄"
            else:
                ch = "▼" if er > sr else "▲"
        elif len(cells) > 1:
            nc, nr = cells[i + 1]
            dc2 = nc - cc
            dr2 = nr - cr
            if dr2 == 0:
                ch = "─"
            elif dc2 == 0:
                ch = "│"
            elif (dc2 > 0 and dr2 < 0) or (dc2 < 0 and dr2 > 0):
                ch = "/"
            else:
                ch = "\\"
        else:
            ch = "·"
        put(cc, cr, ch)


# ---------------------------------------------------------------------------
# Text element
# ---------------------------------------------------------------------------

def _paint_text_element(
    grid: CellGrid,
    el: TextElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else Style(color="white")
    lines = el.text.split("\n") if el.text else []
    for i, line in enumerate(lines):
        for j, ch in enumerate(line):
            tc, tr = viewport.to_terminal(el.col + j, el.row + i)
            grid_set(grid, tc, tr, ch, base_style)


# ---------------------------------------------------------------------------
# Selection handles
# ---------------------------------------------------------------------------

def _paint_selection_handles(
    grid: CellGrid,
    element: Element,
    viewport: Viewport,
    style: Style,
) -> None:
    c, r, w, h = element.bounding_box()
    # Draw bounding box 1 cell outside
    oc, or_ = c - 1, r - 1
    ow, oh = w + 2, h + 2

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, style)

    # Corners (handles)
    for hc, hr in [(oc, or_), (oc + ow - 1, or_), (oc, or_ + oh - 1), (oc + ow - 1, or_ + oh - 1)]:
        put(hc, hr, "+")

    # Edge midpoint handles
    put(oc + ow // 2, or_, "+")
    put(oc + ow // 2, or_ + oh - 1, "+")
    put(oc, or_ + oh // 2, "+")
    put(oc + ow - 1, or_ + oh // 2, "+")


# ---------------------------------------------------------------------------
# Rubber band
# ---------------------------------------------------------------------------

def _paint_rubber_band(
    grid: CellGrid,
    rubber_band: tuple[int, int, int, int],
    viewport: Viewport,
) -> None:
    style = Style(color="bright_white", dim=True)
    c, r, w, h = rubber_band
    if w == 0 or h == 0:
        return

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, style)

    for x in range(c, c + w):
        put(x, r, "─")
        put(x, r + h - 1, "─")
    for y in range(r, r + h):
        put(c, y, "│")
        put(c + w - 1, y, "│")
    put(c, r, "┌")
    put(c + w - 1, r, "┐")
    put(c, r + h - 1, "└")
    put(c + w - 1, r + h - 1, "┘")
