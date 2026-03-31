"""CanvasPainter: stateless renderer. Converts Document + state → CellGrid."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.style import Style

from .models import (
    AnchorPoint,
    ArrowElement,
    DiamondElement,
    Document,
    Element,
    EllipseElement,
    PathElement,
    RectElement,
    TextElement,
    Viewport,
    resolve_anchor_position,
)

# ---------------------------------------------------------------------------
# Cell / CellGrid
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Cell:
    char: str = " "
    style: Style = field(default_factory=Style)


CellGrid = list[list[Cell]]  # [row][col]


def make_grid(rows: int, cols: int) -> CellGrid:
    return [[Cell() for _ in range(cols)] for _ in range(rows)]


def clear_grid(grid: CellGrid) -> None:
    """Reset all cells to blank in-place."""
    for row in grid:
        for cell in row:
            cell.char = " "
            cell.style = _STYLE_NONE


def grid_set(grid: CellGrid, col: int, row: int, char: str, style: Style) -> None:
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        cell = grid[row][col]
        cell.char = char
        cell.style = style


# ---------------------------------------------------------------------------
# Cached module-level styles (avoid per-frame allocation)
# ---------------------------------------------------------------------------

_STYLE_NONE = Style()
_STYLE_WHITE = Style(color="white")
_STYLE_YELLOW = Style(color="yellow")
_STYLE_BOLD = Style(bold=True)  # combined with arrow style for arrowhead cells
_STYLE_GHOST = Style(dim=True, color="cyan")
_STYLE_SEL = Style(color="bright_cyan", bold=True)
_STYLE_DOT = Style(color="grey23")
_STYLE_RUBBER = Style(color="bright_white", dim=True)
_STYLE_HOVER = Style(color="yellow")
_STYLE_EDIT = Style(color="bright_green", bold=True)
_STYLE_CURSOR = Style(color="bright_white", bold=True)


# ---------------------------------------------------------------------------
# Box-drawing characters
# ---------------------------------------------------------------------------

SINGLE = {
    "tl": "┌",
    "tr": "┐",
    "bl": "└",
    "br": "┘",
    "h": "─",
    "v": "│",
    "t": "┬",
    "b": "┴",
    "l": "├",
    "r": "┤",
    "x": "┼",
}
DOUBLE = {
    "tl": "╔",
    "tr": "╗",
    "bl": "╚",
    "br": "╝",
    "h": "═",
    "v": "║",
    "t": "╦",
    "b": "╩",
    "l": "╠",
    "r": "╣",
    "x": "╬",
}
ROUNDED = {
    "tl": "╭",
    "tr": "╮",
    "bl": "╰",
    "br": "╯",
    "h": "─",
    "v": "│",
    "t": "┬",
    "b": "┴",
    "l": "├",
    "r": "┤",
    "x": "┼",
}
BORDER_CHARS = {"single": SINGLE, "double": DOUBLE, "rounded": ROUNDED}

ARROW_HEADS = {"E": "▶", "W": "◀", "N": "▲", "S": "▼"}
ARROW_CORNERS = {
    ("E", "S"): "┐",
    ("E", "N"): "┘",
    ("W", "S"): "┌",
    ("W", "N"): "└",
    ("S", "E"): "└",
    ("S", "W"): "┘",
    ("N", "E"): "┌",
    ("N", "W"): "┐",
}

# ---------------------------------------------------------------------------
# Selection / tool state passed to painter
# ---------------------------------------------------------------------------


@dataclass
class SelectionState:
    selected_ids: set[int] = field(default_factory=set)
    rubber_band: tuple[int, int, int, int] | None = None  # col,row,w,h in canvas coords
    hovered_id: int | None = None  # element under the mouse cursor
    editing_id: int | None = None  # element currently being text-edited
    edit_cursor: int = 0  # byte offset of text cursor within edited text
    hover_anchor: AnchorPoint | None = None
    cursor_col: int = -1  # canvas col of mouse cursor (-1 = unknown)
    cursor_row: int = -1  # canvas row of mouse cursor


@dataclass
class ToolPreviewState:
    """Ghost preview of in-progress draw operation."""

    element: Element | None = None  # provisional element not yet in Document
    tool_name: str = "select"  # current tool, for cursor-shape rendering
    snap_anchor: AnchorPoint | None = None


# ---------------------------------------------------------------------------
# Background dot cache
# ---------------------------------------------------------------------------

# Key: (col_offset % 5, row_offset % 5, terminal_width, terminal_height)
# Value: list of (tc, tr) terminal positions that receive a dot
_bg_pos_cache: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}


def _get_bg_positions(
    col_offset: int, row_offset: int, width: int, height: int
) -> list[tuple[int, int]]:
    key = (col_offset % 5, row_offset % 5, width, height)
    cached = _bg_pos_cache.get(key)
    if cached is not None:
        return cached
    positions = [
        (tc, tr)
        for tr in range(height)
        for tc in range(width)
        if (tc + col_offset) % 5 == 0 and (tr + row_offset) % 5 == 0
    ]
    _bg_pos_cache[key] = positions
    return positions


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
        grid: CellGrid | None = None,
    ) -> CellGrid:
        rows = viewport.terminal_height
        cols = viewport.terminal_width
        if grid is None:
            grid = make_grid(rows, cols)

        # Paint background grid dots (subtle)
        _paint_background(grid, viewport)

        # Paint elements in z_order — using pre-sorted list, with viewport culling
        for element in document._sorted_elements:
            ec, er, ew, eh = element.bounding_box()
            if not viewport.bbox_visible(ec, er, ew, eh):
                continue
            _paint_element(grid, element, viewport, _STYLE_NONE)

        # Hover highlight (dim yellow outline on element under cursor)
        _paint_hover_highlight(grid, selection, document, viewport)
        if selection.hover_anchor is not None:
            _paint_anchor_marker(grid, selection.hover_anchor, viewport, _STYLE_HOVER)

        # Paint ghost preview
        if preview.element is not None:
            _paint_element(grid, preview.element, viewport, _STYLE_GHOST)
        if preview.snap_anchor is not None:
            _paint_anchor_marker(grid, preview.snap_anchor, viewport, _STYLE_GHOST)

        # Paint rubber-band selection rect
        if selection.rubber_band is not None:
            _paint_rubber_band(grid, selection.rubber_band, viewport)

        # Paint selection overlay
        if selection.selected_ids:
            for eid in selection.selected_ids:
                el = document.get_by_id(eid)
                if el is not None:
                    _paint_selection_handles(grid, el, viewport, _STYLE_SEL)
            _paint_connected_anchor_points(grid, document, selection, viewport)

        # Edit-mode indicator: bright-green border + text cursor
        _paint_edit_indicator(grid, selection, document, viewport)

        # Mouse cursor indicator (tool-dependent crosshair / beam)
        _paint_cursor_indicator(grid, selection, preview, viewport)

        return grid


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


def _paint_background(grid: CellGrid, viewport: Viewport) -> None:
    positions = _get_bg_positions(
        viewport.col_offset,
        viewport.row_offset,
        viewport.terminal_width,
        viewport.terminal_height,
    )
    for tc, tr in positions:
        grid_set(grid, tc, tr, "·", _STYLE_DOT)


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
    elif isinstance(element, DiamondElement):
        _paint_diamond(grid, element, viewport, override_style)
    elif isinstance(element, PathElement):
        _paint_path(grid, element, viewport, override_style)
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
    base_style = override_style if override_style.color else _STYLE_WHITE

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
    base_style = override_style if override_style.color else _STYLE_WHITE
    c, r, w, h = el.col, el.row, el.width, el.height
    if w < 2 or h < 2:
        return

    for pc, pr in el.get_perimeter_cells():
        tc, tr = viewport.to_terminal(pc, pr)
        grid_set(grid, tc, tr, "o", base_style)

    # Label centered
    if el.label and w > 2 and h > 2:
        inner_w = max(1, w - 4)
        inner_h = max(1, h - 2)
        inner_c = c + (w - inner_w) // 2
        inner_r = r + (h - inner_h) // 2
        _paint_label_in_box(
            grid, el.label, inner_c, inner_r, inner_w, inner_h, viewport, base_style
        )


# ---------------------------------------------------------------------------
# Diamond
# ---------------------------------------------------------------------------


def _bresenham(x0: int, y0: int, x1: int, y1: int):
    """Yield (col, row) integer cells along the line from (x0,y0) to (x1,y1)."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    x, y = x0, y0
    err = dx - dy
    while True:
        yield x, y
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def _paint_diamond(
    grid: CellGrid,
    el: DiamondElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else _STYLE_WHITE
    c, r, w, h = el.col, el.row, el.width, el.height
    if w < 3 or h < 3:
        return

    # Four tip points of the diamond
    top = (c + w // 2, r)
    right = (c + w - 1, r + h // 2)
    bottom = (c + w // 2, r + h - 1)
    left = (c, r + h // 2)

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, base_style)

    # Four sides: char reflects slope direction
    #   left→top:    NE (dx>0, dy<0) → /
    #   top→right:   SE (dx>0, dy>0) → \
    #   right→bottom: SW (dx<0, dy>0) → /   (mirrored NE)
    #   bottom→left: NW (dx<0, dy<0) → \   (mirrored SE)
    for px, py in _bresenham(*left, *top):
        put(px, py, "/")
    for px, py in _bresenham(*top, *right):
        put(px, py, "\\")
    for px, py in _bresenham(*right, *bottom):
        put(px, py, "/")
    for px, py in _bresenham(*bottom, *left):
        put(px, py, "\\")

    # Tip points drawn last with a distinct marker
    put(*top, "*")
    put(*right, "*")
    put(*bottom, "*")
    put(*left, "*")

    # Label at center
    if el.label and w > 4 and h > 4:
        lw = max(1, w // 2 - 1)
        lh = max(1, h // 2 - 1)
        lc = top[0] - lw // 2
        lr = r + h // 2 - lh // 2
        _paint_label_in_box(grid, el.label, lc, lr, lw, lh, viewport, base_style)


# ---------------------------------------------------------------------------
# Freehand Path
# ---------------------------------------------------------------------------


def _paint_path(
    grid: CellGrid,
    el: PathElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else _STYLE_WHITE

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, base_style)

    pts = el.points
    if not pts:
        return
    if len(pts) == 1:
        put(pts[0][0], pts[0][1], "•")
        return
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for px, py in _bresenham(x0, y0, x1, y1):
            put(px, py, "•")


# ---------------------------------------------------------------------------
# Arrow
# ---------------------------------------------------------------------------


def _paint_arrow(
    grid: CellGrid,
    el: ArrowElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else _STYLE_YELLOW
    sc, sr, ec, er = el.start_col, el.start_row, el.end_col, el.end_row

    if el.arrow_style == "straight":
        _paint_straight_arrow(grid, sc, sr, ec, er, viewport, base_style, el.show_arrowhead)
    else:
        _paint_orthogonal_arrow(grid, sc, sr, ec, er, viewport, base_style, el.show_arrowhead)

    _paint_arrow_label(grid, el, viewport, base_style)


def _paint_arrow_label(
    grid: CellGrid,
    el: ArrowElement,
    viewport: Viewport,
    style: Style,
) -> None:
    """Paint the arrow/line label centered at the midpoint of the path."""
    if not el.label:
        return
    sc, sr, ec, er = el.start_col, el.start_row, el.end_col, el.end_row
    if sr == er:
        lc, lr = (sc + ec) // 2, sr  # midpoint of horizontal
    elif sc == ec:
        lc, lr = sc, (sr + er) // 2  # midpoint of vertical
    elif abs(ec - sc) >= abs(er - sr):
        lc, lr = (sc + ec) // 2, sr  # H→V: mid of the horizontal segment
    else:
        lc, lr = sc, (sr + er) // 2  # V→H: mid of the vertical segment
    label = el.label.split("\n")[0]  # arrows show only the first line
    start_c = lc - len(label) // 2
    for i, ch in enumerate(label):
        tc, tr = viewport.to_terminal(start_c + i, lr)
        grid_set(grid, tc, tr, ch, style)


def _paint_orthogonal_arrow(
    grid: CellGrid,
    sc: int,
    sr: int,
    ec: int,
    er: int,
    viewport: Viewport,
    style: Style,
    show_arrowhead: bool = True,
) -> None:
    head_style = style + _STYLE_BOLD

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, style)

    def put_head(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, head_style if show_arrowhead else style)

    if sc == ec and sr == er:
        return

    if sr == er:
        # Pure horizontal
        h_step = 1 if ec > sc else -1
        for col in range(sc, ec, h_step):
            put(col, sr, "─")
        put_head(ec, er, ARROW_HEADS["E" if ec > sc else "W"] if show_arrowhead else "─")
        return

    if sc == ec:
        # Pure vertical
        v_step = 1 if er > sr else -1
        for row in range(sr, er, v_step):
            put(sc, row, "│")
        put_head(ec, er, ARROW_HEADS["S" if er > sr else "N"] if show_arrowhead else "│")
        return

    h_going_right = ec > sc
    v_going_down = er > sr
    h_step = 1 if h_going_right else -1
    v_step = 1 if v_going_down else -1

    if abs(ec - sc) >= abs(er - sr):
        # H → V: horizontal to (ec, sr), corner, vertical to (ec, er)
        for col in range(sc, ec, h_step):
            put(col, sr, "─")

        CORNER_HV = {
            (True, True): "┐",
            (True, False): "┘",
            (False, True): "┌",
            (False, False): "└",
        }
        put(ec, sr, CORNER_HV[(h_going_right, v_going_down)])

        for row in range(sr + v_step, er, v_step):
            put(ec, row, "│")

        put_head(ec, er, ARROW_HEADS["S" if v_going_down else "N"] if show_arrowhead else "│")

    else:
        # V → H: vertical to (sc, er), corner, horizontal to (ec, er)
        for row in range(sr, er, v_step):
            put(sc, row, "│")

        CORNER_VH = {
            (True, True): "└",
            (True, False): "┌",
            (False, True): "┘",
            (False, False): "┐",
        }
        put(sc, er, CORNER_VH[(h_going_right, v_going_down)])

        for col in range(sc + h_step, ec, h_step):
            put(col, er, "─")

        put_head(
            ec,
            er,
            ARROW_HEADS["E" if h_going_right else "W"] if show_arrowhead else "─",
        )


def _paint_straight_arrow(
    grid: CellGrid,
    sc: int,
    sr: int,
    ec: int,
    er: int,
    viewport: Viewport,
    style: Style,
    show_arrowhead: bool = True,
) -> None:
    head_style = style + _STYLE_BOLD

    def put(cc: int, cr: int, ch: str, s: Style = style) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, s)

    dx = abs(ec - sc)
    dy = abs(er - sr)
    sx = 1 if ec > sc else -1
    sy = 1 if er > sr else -1
    x, y = sc, sr
    err = dx - dy

    while True:
        is_last = x == ec and y == er
        if is_last and show_arrowhead:
            if dx >= dy:
                direction = "E" if ec > sc else "W"
            else:
                direction = "S" if er > sr else "N"
            put(x, y, ARROW_HEADS[direction], head_style)
        elif is_last:
            # No arrowhead: use dominant direction
            if dy == 0:
                ch = "─"
            elif dx == 0:
                ch = "│"
            elif (sx > 0 and sy < 0) or (sx < 0 and sy > 0):
                ch = "/"
            else:
                ch = "\\"
            put(x, y, ch)
        else:
            # Look ahead to pick the right line character
            e2 = 2 * err
            ndx = sx if e2 > -dy else 0
            ndy = sy if e2 < dx else 0
            if ndy == 0:
                ch = "─"
            elif ndx == 0:
                ch = "│"
            elif (ndx > 0 and ndy < 0) or (ndx < 0 and ndy > 0):
                ch = "/"
            else:
                ch = "\\"
            put(x, y, ch)

        if is_last:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


# ---------------------------------------------------------------------------
# Text element
# ---------------------------------------------------------------------------


def _paint_text_element(
    grid: CellGrid,
    el: TextElement,
    viewport: Viewport,
    override_style: Style,
) -> None:
    base_style = override_style if override_style.color else _STYLE_WHITE
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

    # Skip entirely if the handle region is outside the viewport
    if not viewport.bbox_visible(oc, or_, ow, oh):
        return

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, style)

    # Corners (handles)
    for hc, hr in [
        (oc, or_),
        (oc + ow - 1, or_),
        (oc, or_ + oh - 1),
        (oc + ow - 1, or_ + oh - 1),
    ]:
        put(hc, hr, "+")

    # Edge midpoint handles
    put(oc + ow // 2, or_, "+")
    put(oc + ow // 2, or_ + oh - 1, "+")
    put(oc, or_ + oh // 2, "+")
    put(oc + ow - 1, or_ + oh // 2, "+")


def _paint_anchor_marker(
    grid: CellGrid,
    anchor: AnchorPoint,
    viewport: Viewport,
    style: Style,
) -> None:
    tc, tr = viewport.to_terminal(anchor.col, anchor.row)
    grid_set(grid, tc, tr, "•", style)


def _paint_connected_anchor_points(
    grid: CellGrid,
    document: Document,
    selection: SelectionState,
    viewport: Viewport,
) -> None:
    for eid in selection.selected_ids:
        el = document.get_by_id(eid)
        if not isinstance(el, ArrowElement):
            continue
        for element_id, anchor_name in [
            (el.start_element_id, el.start_anchor),
            (el.end_element_id, el.end_anchor),
        ]:
            anchor = resolve_anchor_position(document, element_id, anchor_name)
            if anchor is not None:
                _paint_anchor_marker(grid, anchor, viewport, _STYLE_SEL)


# ---------------------------------------------------------------------------
# Hover highlight
# ---------------------------------------------------------------------------


def _paint_hover_highlight(
    grid: CellGrid,
    selection: SelectionState,
    document: Document,
    viewport: Viewport,
) -> None:
    hid = selection.hovered_id
    if hid is None:
        return
    if hid in selection.selected_ids or hid == selection.editing_id:
        return  # selection / edit indicators already cover this element
    if selection.editing_id is not None:
        return  # suppress hover during text editing
    el = document.get_by_id(hid)
    if el is not None:
        ec, er, ew, eh = el.bounding_box()
        if viewport.bbox_visible(ec, er, ew, eh):
            _paint_element(grid, el, viewport, _STYLE_HOVER)


# ---------------------------------------------------------------------------
# Edit-mode indicator and text cursor
# ---------------------------------------------------------------------------


def _paint_edit_indicator(
    grid: CellGrid,
    selection: SelectionState,
    document: Document,
    viewport: Viewport,
) -> None:
    eid = selection.editing_id
    if eid is None:
        return
    el = document.get_by_id(eid)
    if el is None:
        return
    ec, er, ew, eh = el.bounding_box()
    if viewport.bbox_visible(ec, er, ew, eh):
        _paint_element(grid, el, viewport, _STYLE_EDIT)
    _paint_text_cursor(grid, el, selection.edit_cursor, viewport)


def _paint_text_cursor(
    grid: CellGrid,
    el: Element,
    cursor_pos: int,
    viewport: Viewport,
) -> None:
    """Paint │ at the text-cursor position within a TextElement."""
    if not isinstance(el, TextElement):
        return  # shape-label cursor positioning is too complex to do precisely
    text = el.text
    before = text[:cursor_pos]
    lines = before.split("\n")
    row_offset = len(lines) - 1
    col_offset = len(lines[-1])
    tc, tr = viewport.to_terminal(el.col + col_offset, el.row + row_offset)
    grid_set(grid, tc, tr, "│", _STYLE_CURSOR)


# ---------------------------------------------------------------------------
# Mouse cursor indicator
# ---------------------------------------------------------------------------


def _paint_cursor_indicator(
    grid: CellGrid,
    selection: SelectionState,
    preview: ToolPreviewState,
    viewport: Viewport,
) -> None:
    if selection.cursor_col < 0 or selection.cursor_row < 0:
        return
    if selection.editing_id is not None:
        return  # text cursor takes over during editing
    tool = preview.tool_name
    if tool == "select":
        return  # hover highlight is sufficient feedback for select tool
    if tool == "text":
        char, style = "│", _STYLE_CURSOR
    else:
        # draw tools: show + crosshair only while NOT mid-draw (ghost preview covers that)
        if preview.element is not None:
            return
        char, style = "+", _STYLE_CURSOR
    tc, tr = viewport.to_terminal(selection.cursor_col, selection.cursor_row)
    if 0 <= tr < len(grid) and 0 <= tc < len(grid[tr]):
        # Only paint on background cells so we don't overwrite drawn content
        if grid[tr][tc].char in (" ", "·"):
            grid_set(grid, tc, tr, char, style)


# ---------------------------------------------------------------------------
# Rubber band
# ---------------------------------------------------------------------------


def _paint_rubber_band(
    grid: CellGrid,
    rubber_band: tuple[int, int, int, int],
    viewport: Viewport,
) -> None:
    c, r, w, h = rubber_band
    if w == 0 or h == 0:
        return

    def put(cc: int, cr: int, ch: str) -> None:
        tc, tr = viewport.to_terminal(cc, cr)
        grid_set(grid, tc, tr, ch, _STYLE_RUBBER)

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
