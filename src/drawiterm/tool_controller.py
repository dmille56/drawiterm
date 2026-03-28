"""ToolController: state machine that converts mouse events → Commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from .commands import (
    AddElementCommand,
    DeleteElementsCommand,
    DuplicateElementsCommand,
    MoveElementsCommand,
    ResizeElementCommand,
    ToggleArrowStyleCommand,
    UndoStack,
)
from .models import (
    ArrowElement,
    DiamondElement,
    Document,
    Element,
    EllipseElement,
    RectElement,
    TextElement,
)
from .painter import ToolPreviewState, SelectionState

if TYPE_CHECKING:
    pass


class Tool(Enum):
    SELECT = auto()
    RECT = auto()
    ELLIPSE = auto()
    DIAMOND = auto()
    ARROW = auto()
    LINE = auto()
    TEXT = auto()


# Handle positions for resize
HANDLE_NONE = "none"
HANDLE_TL = "tl"
HANDLE_TR = "tr"
HANDLE_BL = "bl"
HANDLE_BR = "br"
HANDLE_TM = "tm"
HANDLE_BM = "bm"
HANDLE_ML = "ml"
HANDLE_MR = "mr"


@dataclass
class ToolController:
    current_tool: Tool = Tool.SELECT

    # Draw tool state
    _drawing: bool = False
    _draw_start_col: int = 0
    _draw_start_row: int = 0
    _draw_cur_col: int = 0
    _draw_cur_row: int = 0

    # Arrow snap: element id or None
    _arrow_snap_start_id: int | None = None
    _arrow_snap_end_id: int | None = None

    # Select tool state
    _drag_moving: bool = False
    _drag_move_last_col: int = 0
    _drag_move_last_row: int = 0

    _rubber_banding: bool = False
    _rubber_start_col: int = 0
    _rubber_start_row: int = 0

    _resizing: bool = False
    _resize_handle: str = HANDLE_NONE
    _resize_element_id: int = -1
    _resize_orig: tuple[int, int, int, int] = (0, 0, 0, 0)
    _resize_start_col: int = 0
    _resize_start_row: int = 0

    # Text editing
    _editing_element_id: int | None = None
    _edit_cursor: int = 0

    # Clipboard
    _clipboard: list[Element] = field(default_factory=list)

    def set_tool(self, tool: Tool) -> None:
        self._cancel_draw()
        self.current_tool = tool

    # ------------------------------------------------------------------
    # Mouse events  (return True if canvas should refresh)
    # ------------------------------------------------------------------

    def on_mouse_down(
        self,
        col: int,
        row: int,
        button: int,
        document: Document,
        undo_stack: UndoStack,
        selection: SelectionState,
        preview: ToolPreviewState,
    ) -> bool:
        if self.current_tool in (
            Tool.RECT,
            Tool.ELLIPSE,
            Tool.DIAMOND,
            Tool.ARROW,
            Tool.LINE,
        ):
            self._drawing = True
            self._draw_start_col = col
            self._draw_start_row = row
            self._draw_cur_col = col
            self._draw_cur_row = row
            if self.current_tool in (Tool.ARROW, Tool.LINE):
                self._arrow_snap_start_id = _snap_to_shape(col, row, document)
            _update_preview(self, document, preview)
            return True

        if self.current_tool == Tool.TEXT:
            # Place text element immediately
            eid = document.next_id()
            el = TextElement(id=eid, z_order=eid, col=col, row=row, text="")
            cmd = AddElementCommand(el)
            undo_stack.push(cmd, document)
            selection.selected_ids = {eid}
            self._editing_element_id = eid
            self._edit_cursor = 0
            return True

        if self.current_tool == Tool.SELECT:
            # Check for resize handle first
            handle, eid = _find_resize_handle(col, row, selection, document)
            if handle != HANDLE_NONE and eid != -1:
                self._resizing = True
                self._resize_handle = handle
                self._resize_element_id = eid
                el = document.get_by_id(eid)
                if el is not None:
                    c, r, w, h = el.bounding_box()
                    self._resize_orig = (c, r, w, h)
                self._resize_start_col = col
                self._resize_start_row = row
                return True

            # Hit test for element
            hits = document.get_at(col, row)
            if hits:
                top = hits[-1]
                if top.id not in selection.selected_ids:
                    selection.selected_ids = {top.id}
                self._drag_moving = True
                self._drag_move_last_col = col
                self._drag_move_last_row = row
                return True
            else:
                # Start rubber band
                selection.selected_ids = set()
                self._rubber_banding = True
                self._rubber_start_col = col
                self._rubber_start_row = row
                selection.rubber_band = (col, row, 0, 0)
                return True

        return False

    def on_mouse_move(
        self,
        col: int,
        row: int,
        button: int,
        document: Document,
        undo_stack: UndoStack,
        selection: SelectionState,
        preview: ToolPreviewState,
    ) -> bool:
        if self._drawing and button == 1:
            self._draw_cur_col = col
            self._draw_cur_row = row
            _update_preview(self, document, preview)
            return True

        if self._drag_moving and button == 1:
            dc = col - self._drag_move_last_col
            dr = row - self._drag_move_last_row
            if dc != 0 or dr != 0:
                moves = [(eid, dc, dr) for eid in selection.selected_ids]
                # Direct move without undo during drag (committed on mouse_up)
                for eid, dc2, dr2 in moves:
                    el = document.get_by_id(eid)
                    if el is not None:
                        from .commands import _apply_move

                        _apply_move(el, dc2, dr2)
                self._drag_move_last_col = col
                self._drag_move_last_row = row
            return True

        if self._rubber_banding and button == 1:
            c = min(self._rubber_start_col, col)
            r = min(self._rubber_start_row, row)
            w = abs(col - self._rubber_start_col)
            h = abs(row - self._rubber_start_row)
            selection.rubber_band = (c, r, w, h)
            return True

        if self._resizing and button == 1:
            _apply_resize_preview(
                self._resize_element_id,
                self._resize_handle,
                self._resize_orig,
                self._resize_start_col,
                self._resize_start_row,
                col,
                row,
                document,
            )
            return True

        return False

    def on_mouse_up(
        self,
        col: int,
        row: int,
        button: int,
        document: Document,
        undo_stack: UndoStack,
        selection: SelectionState,
        preview: ToolPreviewState,
    ) -> bool:
        if self._drawing:
            self._drawing = False
            preview.element = None
            sc, sr = self._draw_start_col, self._draw_start_row
            ec, er = col, row
            # Normalize
            c = min(sc, ec)
            r = min(sr, er)
            w = max(abs(ec - sc) + 1, 3)
            h = max(abs(er - sr) + 1, 3)
            eid = document.next_id()

            if self.current_tool == Tool.RECT:
                el = RectElement(id=eid, z_order=eid, col=c, row=r, width=w, height=h)
                undo_stack.push(AddElementCommand(el), document)
                selection.selected_ids = {eid}

            elif self.current_tool == Tool.ELLIPSE:
                el = EllipseElement(
                    id=eid, z_order=eid, col=c, row=r, width=w, height=h
                )
                undo_stack.push(AddElementCommand(el), document)
                selection.selected_ids = {eid}

            elif self.current_tool == Tool.DIAMOND:
                el = DiamondElement(
                    id=eid, z_order=eid, col=c, row=r, width=w, height=h
                )
                undo_stack.push(AddElementCommand(el), document)
                selection.selected_ids = {eid}

            elif self.current_tool in (Tool.ARROW, Tool.LINE):
                snap_end = _snap_to_shape(col, row, document)
                el = ArrowElement(
                    id=eid,
                    z_order=eid,
                    start_col=sc,
                    start_row=sr,
                    end_col=ec,
                    end_row=er,
                    show_arrowhead=(self.current_tool == Tool.ARROW),
                    start_element_id=self._arrow_snap_start_id,
                    end_element_id=snap_end,
                )
                undo_stack.push(AddElementCommand(el), document)
                selection.selected_ids = {eid}

            return True

        if self._drag_moving:
            self._drag_moving = False
            # The move was applied live; nothing more needed
            return True

        if self._rubber_banding:
            self._rubber_banding = False
            if selection.rubber_band:
                c, r, w, h = selection.rubber_band
                hits = document.elements_in_rect(c, r, w + 1, h + 1)
                selection.selected_ids = {e.id for e in hits}
            selection.rubber_band = None
            return True

        if self._resizing:
            self._resizing = False
            # Commit resize as undoable command
            el = document.get_by_id(self._resize_element_id)
            if el is not None:
                new_c, new_r, new_w, new_h = el.bounding_box()
                oc, or_, ow, oh = self._resize_orig
                if (new_c, new_r, new_w, new_h) != (oc, or_, ow, oh):
                    # Revert live changes and re-apply via undo stack
                    from .commands import _apply_geometry

                    _apply_geometry(el, oc, or_, ow, oh)
                    cmd = ResizeElementCommand(
                        self._resize_element_id,
                        oc,
                        or_,
                        ow,
                        oh,
                        new_c,
                        new_r,
                        new_w,
                        new_h,
                    )
                    undo_stack.push(cmd, document)
            return True

        return False

    def on_double_click(
        self,
        col: int,
        row: int,
        document: Document,
        selection: SelectionState,
    ) -> bool:
        """Enter label/text edit mode for the element under cursor."""
        hits = document.get_at(col, row)
        if hits:
            top = hits[-1]
            selection.selected_ids = {top.id}
            self._editing_element_id = top.id
            self._edit_cursor = len(_get_edit_text(top))
            return True
        return False

    # ------------------------------------------------------------------
    # Keyboard events
    # ------------------------------------------------------------------

    def on_key(
        self,
        key: str,
        document: Document,
        undo_stack: UndoStack,
        selection: SelectionState,
        preview: ToolPreviewState,
    ) -> bool:
        """Return True if canvas should refresh."""
        # Text editing
        if self._editing_element_id is not None:
            return self._handle_text_edit_key(key, document, undo_stack)

        # Tool shortcuts
        if key == "r":
            self.set_tool(Tool.RECT)
            return True
        if key == "e":
            self.set_tool(Tool.ELLIPSE)
            return True
        if key == "d":
            self.set_tool(Tool.DIAMOND)
            return True
        if key == "a":
            self.set_tool(Tool.ARROW)
            return True
        if key == "l":
            self.set_tool(Tool.LINE)
            return True
        if key == "t":
            self.set_tool(Tool.TEXT)
            return True
        if key in ("s", "escape"):
            self.set_tool(Tool.SELECT)
            if key == "escape":
                selection.selected_ids = set()
                self._cancel_draw()
                preview.element = None
            return True

        # Delete
        if key in ("delete", "backspace") and selection.selected_ids:
            cmd = DeleteElementsCommand(list(selection.selected_ids))
            undo_stack.push(cmd, document)
            selection.selected_ids = set()
            return True

        # Nudge
        nudge = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        if key in nudge and selection.selected_ids:
            dc, dr = nudge[key]
            moves = [(eid, dc, dr) for eid in selection.selected_ids]
            undo_stack.push(MoveElementsCommand(moves), document)
            return True

        # Ctrl+A
        if key == "ctrl+a":
            selection.selected_ids = {e.id for e in document.elements}
            return True

        # Tab — toggle arrow style for selected arrows
        if key == "tab" and selection.selected_ids:
            refreshed = False
            for eid in selection.selected_ids:
                el = document.get_by_id(eid)
                if el is not None and isinstance(el, ArrowElement):
                    new_style = (
                        "straight" if el.arrow_style == "orthogonal" else "orthogonal"
                    )
                    undo_stack.push(
                        ToggleArrowStyleCommand(eid, el.arrow_style, new_style),
                        document,
                    )
                    refreshed = True
            if refreshed:
                return True

        # Ctrl+D — duplicate selected elements
        if key == "ctrl+d" and selection.selected_ids:
            cmd = DuplicateElementsCommand(list(selection.selected_ids))
            undo_stack.push(cmd, document)
            selection.selected_ids = {clone.id for clone in cmd._clones}
            return True

        # Enter to edit selected text/label
        if key in ("enter", "f2") and len(selection.selected_ids) == 1:
            eid = next(iter(selection.selected_ids))
            el = document.get_by_id(eid)
            if el is not None:
                self._editing_element_id = eid
                self._edit_cursor = len(_get_edit_text(el))
                return True

        return False

    def _handle_text_edit_key(
        self,
        key: str,
        document: Document,
        undo_stack: UndoStack,
    ) -> bool:
        eid = self._editing_element_id
        if eid is None:
            return False
        el = document.get_by_id(eid)
        if el is None:
            self._editing_element_id = None
            return False

        is_text_el = isinstance(el, TextElement)
        old_text = _get_edit_text(el)
        text = old_text

        if key == "escape":
            # Commit
            from .commands import EditTextCommand

            if text != old_text:
                cmd = EditTextCommand(eid, old_text, text, not is_text_el)
                undo_stack.push(cmd, document)
            self._editing_element_id = None
            return True

        if key == "backspace":
            if self._edit_cursor > 0:
                text = text[: self._edit_cursor - 1] + text[self._edit_cursor :]
                self._edit_cursor -= 1
        elif key == "delete":
            if self._edit_cursor < len(text):
                text = text[: self._edit_cursor] + text[self._edit_cursor + 1 :]
        elif key == "enter":
            if is_text_el:
                text = text[: self._edit_cursor] + "\n" + text[self._edit_cursor :]
                self._edit_cursor += 1
            else:
                # Commit label on Enter for shapes
                from .commands import EditTextCommand

                if text != old_text:
                    cmd = EditTextCommand(eid, old_text, text, True)
                    undo_stack.push(cmd, document)
                self._editing_element_id = None
                return True
        elif key == "left":
            self._edit_cursor = max(0, self._edit_cursor - 1)
        elif key == "right":
            self._edit_cursor = min(len(text), self._edit_cursor + 1)
        else:
            # Resolve the character: single-char keys pass through directly;
            # Textual named keys (e.g. "space", "exclamation_mark") are mapped
            # to their character via key_to_character.
            if len(key) == 1:
                char: str | None = key if key.isprintable() else None
            else:
                from textual.keys import key_to_character

                char = key_to_character(key)
            if char is not None and char.isprintable():
                text = text[: self._edit_cursor] + char + text[self._edit_cursor :]
                self._edit_cursor += 1

        # Apply text change live (will be committed on Escape/Enter)
        _set_edit_text(el, text)
        return True

    def _cancel_draw(self) -> None:
        self._drawing = False

    @property
    def is_editing(self) -> bool:
        return self._editing_element_id is not None

    @property
    def editing_element_id(self) -> int | None:
        return self._editing_element_id

    @property
    def edit_cursor(self) -> int:
        return self._edit_cursor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _update_preview(
    ctrl: ToolController, document: Document, preview: ToolPreviewState
) -> None:
    sc, sr = ctrl._draw_start_col, ctrl._draw_start_row
    ec, er = ctrl._draw_cur_col, ctrl._draw_cur_row
    c = min(sc, ec)
    r = min(sr, er)
    w = max(abs(ec - sc) + 1, 3)
    h = max(abs(er - sr) + 1, 3)

    if ctrl.current_tool == Tool.RECT:
        preview.element = RectElement(
            id=-1, z_order=99999, col=c, row=r, width=w, height=h
        )
    elif ctrl.current_tool == Tool.ELLIPSE:
        preview.element = EllipseElement(
            id=-1, z_order=99999, col=c, row=r, width=w, height=h
        )
    elif ctrl.current_tool == Tool.DIAMOND:
        preview.element = DiamondElement(
            id=-1, z_order=99999, col=c, row=r, width=w, height=h
        )
    elif ctrl.current_tool == Tool.ARROW:
        preview.element = ArrowElement(
            id=-1, z_order=99999, start_col=sc, start_row=sr, end_col=ec, end_row=er
        )
    elif ctrl.current_tool == Tool.LINE:
        preview.element = ArrowElement(
            id=-1,
            z_order=99999,
            start_col=sc,
            start_row=sr,
            end_col=ec,
            end_row=er,
            show_arrowhead=False,
        )
    else:
        preview.element = None


def _snap_to_shape(
    col: int, row: int, document: Document, radius: int = 1
) -> int | None:
    """Return element id if (col, row) is within radius of a shape's edge midpoint."""
    for el in document.elements:
        if isinstance(el, (RectElement, EllipseElement)):
            c, r, w, h = el.bounding_box()
            midpoints = [
                (c + w // 2, r),  # top
                (c + w // 2, r + h - 1),  # bottom
                (c, r + h // 2),  # left
                (c + w - 1, r + h // 2),  # right
            ]
            for mc, mr in midpoints:
                if abs(col - mc) <= radius and abs(row - mr) <= radius:
                    return el.id
    return None


def _find_resize_handle(
    col: int,
    row: int,
    selection: SelectionState,
    document: Document,
) -> tuple[str, int]:
    """Return (handle_name, element_id) if cursor is on a resize handle."""
    if len(selection.selected_ids) != 1:
        return HANDLE_NONE, -1
    eid = next(iter(selection.selected_ids))
    el = document.get_by_id(eid)
    if el is None or isinstance(el, (ArrowElement, TextElement)):
        return HANDLE_NONE, -1
    c, r, w, h = el.bounding_box()
    oc, or_ = c - 1, r - 1
    ow, oh = w + 2, h + 2
    handles = {
        HANDLE_TL: (oc, or_),
        HANDLE_TR: (oc + ow - 1, or_),
        HANDLE_BL: (oc, or_ + oh - 1),
        HANDLE_BR: (oc + ow - 1, or_ + oh - 1),
        HANDLE_TM: (oc + ow // 2, or_),
        HANDLE_BM: (oc + ow // 2, or_ + oh - 1),
        HANDLE_ML: (oc, or_ + oh // 2),
        HANDLE_MR: (oc + ow - 1, or_ + oh // 2),
    }
    for name, (hc, hr) in handles.items():
        if hc == col and hr == row:
            return name, eid
    return HANDLE_NONE, -1


def _apply_resize_preview(
    eid: int,
    handle: str,
    orig: tuple[int, int, int, int],
    start_col: int,
    start_row: int,
    cur_col: int,
    cur_row: int,
    document: Document,
) -> None:
    el = document.get_by_id(eid)
    if el is None:
        return
    oc, or_, ow, oh = orig
    dc = cur_col - start_col
    dr = cur_row - start_row

    if handle == HANDLE_BR:
        new_w, new_h = max(3, ow + dc), max(3, oh + dr)
        from .commands import _apply_geometry

        _apply_geometry(el, oc, or_, new_w, new_h)
    elif handle == HANDLE_TL:
        new_c = min(oc + ow - 3, oc + dc)
        new_r = min(or_ + oh - 3, or_ + dr)
        new_w = max(3, ow - dc)
        new_h = max(3, oh - dr)
        from .commands import _apply_geometry

        _apply_geometry(el, new_c, new_r, new_w, new_h)
    elif handle == HANDLE_TR:
        new_r = min(or_ + oh - 3, or_ + dr)
        new_w = max(3, ow + dc)
        new_h = max(3, oh - dr)
        from .commands import _apply_geometry

        _apply_geometry(el, oc, new_r, new_w, new_h)
    elif handle == HANDLE_BL:
        new_c = min(oc + ow - 3, oc + dc)
        new_w = max(3, ow - dc)
        new_h = max(3, oh + dr)
        from .commands import _apply_geometry

        _apply_geometry(el, new_c, or_, new_w, new_h)
    elif handle == HANDLE_TM:
        new_r = min(or_ + oh - 3, or_ + dr)
        new_h = max(3, oh - dr)
        from .commands import _apply_geometry

        _apply_geometry(el, oc, new_r, ow, new_h)
    elif handle == HANDLE_BM:
        new_h = max(3, oh + dr)
        from .commands import _apply_geometry

        _apply_geometry(el, oc, or_, ow, new_h)
    elif handle == HANDLE_ML:
        new_c = min(oc + ow - 3, oc + dc)
        new_w = max(3, ow - dc)
        from .commands import _apply_geometry

        _apply_geometry(el, new_c, or_, new_w, oh)
    elif handle == HANDLE_MR:
        new_w = max(3, ow + dc)
        from .commands import _apply_geometry

        _apply_geometry(el, oc, or_, new_w, oh)


def _get_edit_text(el: Element) -> str:
    if isinstance(el, TextElement):
        return el.text
    return el.label


def _set_edit_text(el: Element, text: str) -> None:
    if isinstance(el, TextElement):
        el.text = text
    else:
        el.label = text
