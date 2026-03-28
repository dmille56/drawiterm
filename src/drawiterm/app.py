"""DrawitermApp: the root Textual application."""
from __future__ import annotations

import sys
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Label
from textual.containers import Vertical

from .commands import UndoStack
from .file_io import save, load
from .models import Document
from .tool_controller import ToolController, Tool
from .widgets.canvas import CanvasWidget
from .widgets.statusbar import StatusBar
from .widgets.toolbar import ToolBar

TOOL_ID_MAP = {
    "select": Tool.SELECT,
    "rect": Tool.RECT,
    "ellipse": Tool.ELLIPSE,
    "diamond": Tool.DIAMOND,
    "arrow": Tool.ARROW,
    "line": Tool.LINE,
    "text": Tool.TEXT,
}

TOOL_NAME_MAP = {v: k for k, v in TOOL_ID_MAP.items()}


class DrawitermApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    CanvasWidget {
        height: 1fr;
    }
    #save-dialog {
        layer: overlay;
        background: $panel;
        border: solid $accent;
        padding: 1 2;
        width: 50;
        height: 7;
        align: center middle;
        offset: 50% 40%;
    }
    #open-dialog {
        layer: overlay;
        background: $panel;
        border: solid $accent;
        padding: 1 2;
        width: 50;
        height: 7;
        align: center middle;
        offset: 50% 40%;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=False),
        Binding("ctrl+o", "open_file", "Open", show=False),
        Binding("ctrl+z", "undo", "Undo", show=False),
        Binding("ctrl+y", "redo", "Redo", show=False),
        Binding("ctrl+shift+z", "redo", "Redo", show=False),
        Binding("ctrl+a", "select_all", "Select All", show=False),
        Binding("ctrl+d", "duplicate", "Duplicate", show=False),
        Binding("tab", "tab_key", "Toggle Arrow Style", show=False),
        Binding("ctrl+q", "quit_app", "Quit", show=False),
        Binding("ctrl+up", "pan_up", "Pan Up", show=False),
        Binding("ctrl+down", "pan_down", "Pan Down", show=False),
        Binding("ctrl+left", "pan_left", "Pan Left", show=False),
        Binding("ctrl+right", "pan_right", "Pan Right", show=False),
    ]

    def __init__(self, filepath: Path | None = None) -> None:
        super().__init__()
        self._filepath = filepath
        self._dirty = False
        self.document = Document()
        self.undo_stack = UndoStack()
        self.tool_ctrl = ToolController()

        if filepath and filepath.exists():
            try:
                self.document = load(filepath)
            except Exception as exc:
                self._load_error = str(exc)
            else:
                self._load_error = None
        else:
            self._load_error = None

    def compose(self) -> ComposeResult:
        yield ToolBar(id="toolbar")
        yield CanvasWidget(
            self.document,
            self.undo_stack,
            self.tool_ctrl,
            id="canvas",
        )
        yield StatusBar(id="statusbar")

    def on_mount(self) -> None:
        self._update_status()
        canvas = self.query_one(CanvasWidget)
        canvas.focus()

    def _canvas(self) -> CanvasWidget:
        return self.query_one(CanvasWidget)

    def _statusbar(self) -> StatusBar:
        return self.query_one(StatusBar)

    def _toolbar(self) -> ToolBar:
        return self.query_one(ToolBar)

    def _update_status(self) -> None:
        canvas = self._canvas()
        col, row = canvas.cursor_canvas_pos
        filename = str(self._filepath) if self._filepath else "Untitled"
        self._statusbar().update_status(
            TOOL_NAME_MAP.get(self.tool_ctrl.current_tool, "select"),
            col, row,
            filename,
            self._dirty,
            selection_count=len(canvas.selection.selected_ids),
            is_editing=self.tool_ctrl.is_editing,
            can_undo=self.undo_stack.can_undo,
            can_redo=self.undo_stack.can_redo,
        )

    @on(CanvasWidget.StatusChanged)
    def _on_canvas_status_changed(self) -> None:
        self._update_status()

    @on(ToolBar.ToolSelected)
    def _on_tool_selected(self, event: ToolBar.ToolSelected) -> None:
        tool = TOOL_ID_MAP.get(event.tool_id, Tool.SELECT)
        self.tool_ctrl.set_tool(tool)
        self._toolbar().set_active(event.tool_id)
        self._canvas().refresh()
        self._update_status()

    # ------------------------------------------------------------------
    # Keyboard routing
    # ------------------------------------------------------------------

    def on_key(self, event) -> None:
        key = event.key

        # Let bindings handle ctrl combos and tab (tab cycles focus by default)
        if key.startswith("ctrl+") or key.startswith("shift+") or key == "tab":
            return

        canvas = self._canvas()

        # Tool shortcuts and canvas keys
        handled = canvas.handle_key(key)
        if handled:
            # Sync toolbar when tool changes
            tool_id = TOOL_NAME_MAP.get(self.tool_ctrl.current_tool, "select")
            self._toolbar().set_active(tool_id)
            self._dirty = True
            self._update_status()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_save(self) -> None:
        if self._filepath is None:
            self._show_save_dialog()
        else:
            self._do_save(self._filepath)

    def action_open_file(self) -> None:
        self._show_open_dialog()

    def action_undo(self) -> None:
        if self.undo_stack.undo(self.document):
            self._canvas().refresh()
            self._dirty = True
            self._update_status()

    def action_redo(self) -> None:
        if self.undo_stack.redo(self.document):
            self._canvas().refresh()
            self._dirty = True
            self._update_status()

    def action_select_all(self) -> None:
        canvas = self._canvas()
        canvas.selection.selected_ids = {e.id for e in self.document.elements}
        canvas.refresh()

    def action_tab_key(self) -> None:
        self._canvas().handle_key("tab")
        self._update_status()

    def action_duplicate(self) -> None:
        canvas = self._canvas()
        if not canvas.selection.selected_ids:
            return
        from .commands import DuplicateElementsCommand
        cmd = DuplicateElementsCommand(list(canvas.selection.selected_ids))
        self.undo_stack.push(cmd, self.document)
        canvas.selection.selected_ids = {clone.id for clone in cmd._clones}
        canvas.refresh()
        self._dirty = True
        self._update_status()

    def action_quit_app(self) -> None:
        if self._dirty:
            self._show_quit_confirm()
        else:
            self.exit()

    def action_pan_up(self) -> None:
        self._canvas().pan(0, -5)

    def action_pan_down(self) -> None:
        self._canvas().pan(0, 5)

    def action_pan_left(self) -> None:
        self._canvas().pan(-5, 0)

    def action_pan_right(self) -> None:
        self._canvas().pan(5, 0)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _show_save_dialog(self) -> None:
        from textual.screen import ModalScreen

        class SaveDialog(ModalScreen):
            def compose(self) -> ComposeResult:
                yield Vertical(
                    Label("Save as (.drawiterm):"),
                    Input(placeholder="filename.drawiterm", id="save-input"),
                    id="save-dialog",
                )

            def on_input_submitted(self, event: Input.Submitted) -> None:
                self.dismiss(event.value)

            def on_key(self, event) -> None:
                if event.key == "escape":
                    self.dismiss(None)

        def _on_save(filename: str | None) -> None:
            if filename:
                p = Path(filename)
                if not p.suffix:
                    p = p.with_suffix(".drawiterm")
                self._filepath = p
                self._do_save(p)

        self.push_screen(SaveDialog(), _on_save)

    def _show_open_dialog(self) -> None:
        from textual.screen import ModalScreen

        class OpenDialog(ModalScreen):
            def compose(self) -> ComposeResult:
                yield Vertical(
                    Label("Open file:"),
                    Input(placeholder="path/to/file.drawiterm", id="open-input"),
                    id="open-dialog",
                )

            def on_input_submitted(self, event: Input.Submitted) -> None:
                self.dismiss(event.value)

            def on_key(self, event) -> None:
                if event.key == "escape":
                    self.dismiss(None)

        def _on_open(filename: str | None) -> None:
            if filename:
                p = Path(filename)
                if p.exists():
                    try:
                        self.document = load(p)
                        self._filepath = p
                        self._dirty = False
                        self.undo_stack.clear()
                        canvas = self._canvas()
                        canvas.document = self.document
                        canvas.selection.selected_ids = set()
                        canvas.refresh()
                        self._update_status()
                    except Exception as exc:
                        self.notify(f"Error loading file: {exc}", severity="error")
                else:
                    self.notify(f"File not found: {p}", severity="error")

        self.push_screen(OpenDialog(), _on_open)

    def _show_quit_confirm(self) -> None:
        from textual.screen import ModalScreen

        class QuitConfirm(ModalScreen):
            DEFAULT_CSS = """
            QuitConfirm {
                align: center middle;
            }
            #quit-dialog {
                background: $panel;
                border: solid $accent;
                padding: 1 2;
                width: 40;
                height: 5;
                align: center middle;
            }
            """

            def compose(self) -> ComposeResult:
                yield Vertical(
                    Label("Unsaved changes. Quit anyway? (y/n)"),
                    id="quit-dialog",
                )

            def on_key(self, event) -> None:
                if event.key == "y":
                    self.dismiss(True)
                else:
                    self.dismiss(False)

        def _on_confirm(quit: bool) -> None:
            if quit:
                self.exit()

        self.push_screen(QuitConfirm(), _on_confirm)

    def _do_save(self, path: Path) -> None:
        try:
            save(self.document, path)
            self._dirty = False
            self._update_status()
            self.notify(f"Saved to {path}", severity="information")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")
