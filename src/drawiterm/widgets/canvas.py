"""CanvasWidget: the main interactive drawing area."""
from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual.app import RenderResult
from textual.events import Click, Key, MouseDown, MouseMove, MouseUp, MouseScrollDown, MouseScrollUp
from textual.geometry import Size
from textual.message import Message
from textual.widget import Widget

from ..commands import UndoStack
from ..models import Document, Viewport, CANVAS_WIDTH, CANVAS_HEIGHT
from ..painter import CanvasPainter, SelectionState, ToolPreviewState, CellGrid
from ..tool_controller import ToolController


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

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return container.width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return container.height

    def on_mount(self) -> None:
        self._sync_viewport_size()

    def on_resize(self, event) -> None:
        self._sync_viewport_size()

    def _sync_viewport_size(self) -> None:
        size = self.size
        self.viewport.terminal_width = size.width
        self.viewport.terminal_height = size.height

    def render(self) -> RenderResult:
        self._sync_viewport_size()
        grid = CanvasPainter.paint(
            self.document, self.viewport, self.selection, self.preview
        )
        return _grid_to_renderable(grid, self.viewport.terminal_width, self.viewport.terminal_height)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def on_mouse_down(self, event: MouseDown) -> None:
        col, row = self.viewport.to_canvas(event.x, event.y)
        self._last_mouse_col = col
        self._last_mouse_row = row
        self._mouse_button_held = event.button
        changed = self.tool_ctrl.on_mouse_down(
            col, row, event.button,
            self.document, self.undo_stack, self.selection, self.preview,
        )
        if changed:
            self.refresh()
            self.post_message(self.StatusChanged())

    def on_mouse_move(self, event: MouseMove) -> None:
        col, row = self.viewport.to_canvas(event.x, event.y)
        self._last_mouse_col = col
        self._last_mouse_row = row
        changed = self.tool_ctrl.on_mouse_move(
            col, row, self._mouse_button_held,
            self.document, self.undo_stack, self.selection, self.preview,
        )
        if changed:
            self.refresh()
        self.post_message(self.StatusChanged())

    def on_mouse_up(self, event: MouseUp) -> None:
        col, row = self.viewport.to_canvas(event.x, event.y)
        self._mouse_button_held = 0
        changed = self.tool_ctrl.on_mouse_up(
            col, row, event.button,
            self.document, self.undo_stack, self.selection, self.preview,
        )
        if changed:
            self.refresh()
            self.post_message(self.StatusChanged())

    def on_click(self, event: Click) -> None:
        if event.button == 1 and event.ctrl is False:
            col, row = self.viewport.to_canvas(event.x, event.y)
            if self._double_click_pending:
                self._double_click_pending = False
                changed = self.tool_ctrl.on_double_click(col, row, self.document, self.selection)
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


# ---------------------------------------------------------------------------
# Convert CellGrid → Rich renderable
# ---------------------------------------------------------------------------

def _grid_to_renderable(grid: CellGrid, cols: int, rows: int):
    from rich.console import ConsoleOptions, RenderResult as RichRenderResult
    from rich.console import Console

    class GridRenderable:
        def __rich_console__(self, console: Console, options: ConsoleOptions) -> RichRenderResult:
            for row_idx, row in enumerate(grid):
                for col_idx, cell in enumerate(row):
                    yield Segment(cell.char, cell.style)
                if row_idx < len(grid) - 1:
                    yield Segment.line()

    return GridRenderable()
