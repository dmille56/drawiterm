"""CanvasWidget: the main interactive drawing area."""

from __future__ import annotations

from rich.console import Console, ConsoleOptions
from rich.console import RenderResult as RichRenderResult
from rich.segment import Segment
from textual.app import RenderResult
from textual.events import (
    Click,
    MouseDown,
    MouseMove,
    MouseUp,
    MouseScrollDown,
    MouseScrollUp,
)
from textual.geometry import Size
from textual.message import Message
from textual.widget import Widget

from ..commands import UndoStack
from ..models import Document, Viewport
from ..painter import (
    CanvasPainter,
    SelectionState,
    ToolPreviewState,
    CellGrid,
    make_grid,
    clear_grid,
)
from ..tool_controller import ToolController


# ---------------------------------------------------------------------------
# Rich renderable for CellGrid — defined at module level to avoid per-frame
# class redefinition
# ---------------------------------------------------------------------------


class _GridRenderable:
    __slots__ = ("_grid",)

    def __init__(self, grid: CellGrid) -> None:
        self._grid = grid

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RichRenderResult:
        grid = self._grid
        last_row = len(grid) - 1
        for row_idx, row in enumerate(grid):
            for cell in row:
                yield Segment(cell.char, cell.style)
            if row_idx < last_row:
                yield Segment.line()


class CanvasWidget(Widget):
    DEFAULT_CSS = """
    CanvasWidget {
        border: none;
    }
    """

    class StatusChanged(Message):
        pass

    def __init__(
        self,
        document: Document,
        undo_stack: UndoStack,
        tool_controller: ToolController,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.document = document
        self.undo_stack = undo_stack
        self.tool_ctrl = tool_controller
        self.viewport = Viewport()
        self.selection = SelectionState()
        self.preview = ToolPreviewState()
        self._last_mouse_col = 0
        self._last_mouse_row = 0
        self._mouse_button_held = 0
        self._double_click_pending = False
        self._grid: CellGrid | None = None  # reused across renders

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return container.width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return container.height

    def on_mount(self) -> None:
        self._sync_viewport_size()

    def on_resize(self, event) -> None:
        self._sync_viewport_size()
        self._grid = None  # force reallocation on next render

    def _sync_viewport_size(self) -> None:
        size = self.size
        self.viewport.terminal_width = size.width
        self.viewport.terminal_height = size.height

    def render(self) -> RenderResult:
        self._sync_viewport_size()
        rows = self.viewport.terminal_height
        cols = self.viewport.terminal_width

        # Sync painter state from tool controller
        self.selection.editing_id = self.tool_ctrl.editing_element_id
        self.selection.edit_cursor = self.tool_ctrl.edit_cursor
        self.selection.cursor_col = self._last_mouse_col
        self.selection.cursor_row = self._last_mouse_row
        self.preview.tool_name = self.tool_ctrl.current_tool.name.lower()

        # Reuse the grid buffer; reallocate only when dimensions change
        if self._grid is None or len(self._grid) != rows or len(self._grid[0]) != cols:
            self._grid = make_grid(rows, cols)
        else:
            clear_grid(self._grid)

        grid = CanvasPainter.paint(
            self.document, self.viewport, self.selection, self.preview, self._grid
        )
        return _GridRenderable(grid)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def on_mouse_down(self, event: MouseDown) -> None:
        col, row = self.viewport.to_canvas(event.x, event.y)
        self._last_mouse_col = col
        self._last_mouse_row = row
        self._mouse_button_held = event.button
        changed = self.tool_ctrl.on_mouse_down(
            col,
            row,
            event.button,
            self.document,
            self.undo_stack,
            self.selection,
            self.preview,
        )
        if changed:
            self.refresh()
            self.post_message(self.StatusChanged())

    def on_mouse_move(self, event: MouseMove) -> None:
        col, row = self.viewport.to_canvas(event.x, event.y)
        pos_changed = col != self._last_mouse_col or row != self._last_mouse_row
        self._last_mouse_col = col
        self._last_mouse_row = row
        changed = self.tool_ctrl.on_mouse_move(
            col,
            row,
            self._mouse_button_held,
            self.document,
            self.undo_stack,
            self.selection,
            self.preview,
        )
        # Update hover highlight
        if pos_changed:
            hits = self.document.get_at(col, row)
            new_hovered = hits[-1].id if hits else None
            if new_hovered != self.selection.hovered_id:
                self.selection.hovered_id = new_hovered
                changed = True
        if changed:
            self.refresh()
        if changed or pos_changed:
            self.post_message(self.StatusChanged())

    def on_mouse_up(self, event: MouseUp) -> None:
        col, row = self.viewport.to_canvas(event.x, event.y)
        self._mouse_button_held = 0
        changed = self.tool_ctrl.on_mouse_up(
            col,
            row,
            event.button,
            self.document,
            self.undo_stack,
            self.selection,
            self.preview,
        )
        if changed:
            self.refresh()
            self.post_message(self.StatusChanged())

    def on_click(self, event: Click) -> None:
        if event.button == 1 and event.ctrl is False:
            col, row = self.viewport.to_canvas(event.x, event.y)
            if self._double_click_pending:
                self._double_click_pending = False
                changed = self.tool_ctrl.on_double_click(
                    col, row, self.document, self.selection
                )
                if changed:
                    self.refresh()
                    self.post_message(self.StatusChanged())
            else:
                self._double_click_pending = True
                self.set_timer(0.3, self._clear_double_click_pending)

    def _clear_double_click_pending(self) -> None:
        self._double_click_pending = False

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        self.viewport.row_offset += 3
        self.viewport.clamp()
        self.refresh()
        self.post_message(self.StatusChanged())

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        self.viewport.row_offset -= 3
        self.viewport.clamp()
        self.refresh()
        self.post_message(self.StatusChanged())

    # ------------------------------------------------------------------
    # Keyboard (routed from app)
    # ------------------------------------------------------------------

    def handle_key(self, key: str) -> bool:
        changed = self.tool_ctrl.on_key(
            key, self.document, self.undo_stack, self.selection, self.preview
        )
        if changed:
            self.refresh()
            self.post_message(self.StatusChanged())
        return changed

    def pan(self, dc: int, dr: int) -> None:
        self.viewport.col_offset += dc
        self.viewport.row_offset += dr
        self.viewport.clamp()
        self.refresh()
        self.post_message(self.StatusChanged())

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def cursor_canvas_pos(self) -> tuple[int, int]:
        return self._last_mouse_col, self._last_mouse_row
