"""DrawitermApp: the root Textual application."""

from __future__ import annotations

import json
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, Label

from .commands import UndoStack
from .file_io import load, save
from .models import ArrowElement, Document
from .tool_controller import Tool, ToolController
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
    "draw": Tool.DRAW,
    "eraser": Tool.ERASER,
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
        Binding("tab", "next_tool", "Next Tool", show=False, priority=True),
        Binding(
            "shift+tab",
            "toggle_arrow_style",
            "Toggle Arrow Style",
            show=False,
            priority=True,
        ),
        Binding("ctrl+l", "toggle_tool_lock", "Lock Tool", show=False),
        Binding("ctrl+q", "quit_app", "Quit", show=False),
        Binding("ctrl+g", "spawn_ghost", "Spawn Ghost", show=False),  # 👻
        Binding("ctrl+up", "pan_up", "Pan Up", show=False),
        Binding("ctrl+down", "pan_down", "Pan Down", show=False),
        Binding("ctrl+left", "pan_left", "Pan Left", show=False),
        Binding("ctrl+right", "pan_right", "Pan Right", show=False),
        Binding("ctrl+g", "spawn_ghost", "Spawn Ghost", show=False),
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
            except json.JSONDecodeError as exc:
                self._load_error = f"Invalid JSON file: {exc}"
            except FileNotFoundError:
                self._load_error = "File not found"
            except KeyError as exc:
                self._load_error = f"Missing required field: {exc}"
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
        sel_ids = canvas.selection.selected_ids
        has_arrow_or_line = any(
            isinstance(self.document.get_by_id(eid), ArrowElement) for eid in sel_ids
        )
        anchor_hint = self._anchor_hint(sel_ids) if has_arrow_or_line else None

        self._statusbar().update_status(
            TOOL_NAME_MAP.get(self.tool_ctrl.current_tool, "select"),
            col,
            row,
            filename,
            self._dirty,
            selection_count=len(sel_ids),
            is_editing=self.tool_ctrl.is_editing,
            can_undo=self.undo_stack.can_undo,
            can_redo=self.undo_stack.can_redo,
            has_arrow_or_line_selected=has_arrow_or_line,
            anchor_hint=anchor_hint,
        )

    def _anchor_hint(self, sel_ids: set[int]) -> str | None:
        def describe(element_id: int | None, anchor_name: str | None) -> str | None:
            if element_id is None or anchor_name is None:
                return None
            target = self.document.get_by_id(element_id)
            if target is None:
                return None
            label = target.label or target.element_type
            return f"{label}:{anchor_name}"

        for eid in sel_ids:
            el = self.document.get_by_id(eid)
            if not isinstance(el, ArrowElement):
                continue
            start = describe(el.start_element_id, el.start_anchor)
            end = describe(el.end_element_id, el.end_anchor)
            if start and end:
                return f"{start} ↔ {end}"
            if start:
                return start
            if end:
                return end
        return None

    @on(CanvasWidget.StatusChanged)
    def _on_canvas_status_changed(self) -> None:
        self._update_status()
        # Keep toolbar in sync with programmatic tool changes
        self._toolbar().set_active(TOOL_NAME_MAP.get(self.tool_ctrl.current_tool, "select"))

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

        # Track ghost element position when it exists
        self._track_ghost_position(canvas)

    def _track_ghost_position(self, canvas: CanvasWidget) -> None:
        """Move the ghost element to follow the mouse cursor."""
        ghost = self.document.get_by_id(self.document._ghost_element_id)
        if ghost is None:
            return
        col, row = canvas.cursor_canvas_pos
        ghost.col = col
        ghost.row = row
        canvas.refresh()

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

    def action_next_tool(self) -> None:
        order = [
            Tool.SELECT,
            Tool.RECT,
            Tool.ELLIPSE,
            Tool.DIAMOND,
            Tool.ARROW,
            Tool.LINE,
            Tool.DRAW,
            Tool.ERASER,
            Tool.TEXT,
        ]
        cur = self.tool_ctrl.current_tool
        try:
            idx = order.index(cur)
        except ValueError:
            idx = 0
        next_tool = order[(idx + 1) % len(order)]
        self.tool_ctrl.set_tool(next_tool)
        # Clear any ghost preview when switching tools
        self._canvas().preview.element = None
        # Sync toolbar + UI
        self._toolbar().set_active(TOOL_NAME_MAP.get(next_tool, "select"))
        self._canvas().refresh()
        self._update_status()

    def action_toggle_arrow_style(self) -> None:
        # Reuse existing toggle logic in ToolController.on_key("tab")
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

    def action_spawn_ghost(self) -> None:
        """Spawn a ghost element at the cursor position."""
        canvas = self._canvas()
        col, row = canvas.cursor_canvas_pos
        self.document.spawn_ghost(col, row)
        canvas.refresh()
        self._dirty = True
        self._update_status()
        self.notify("👻 The ghost is watching you!", severity="information")

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

    def action_toggle_tool_lock(self) -> None:
        self.tool_ctrl.tool_lock = not self.tool_ctrl.tool_lock
        state = "ON" if self.tool_ctrl.tool_lock else "OFF"
        self.notify(f"Tool lock: {state}", severity="information")
        self._update_status()

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _show_save_dialog(self) -> None:
        from textual.screen import ModalScreen

        class SaveDialog(ModalScreen[None]):
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

        def _on_save(filename: str | None) -> None | None:
            if filename:
                p = Path(filename)
                if not p.suffix:
                    p = p.with_suffix(".drawiterm")
                self._filepath = p
                self._do_save(p)

        self.push_screen(SaveDialog(), _on_save)

    def _show_open_dialog(self) -> None:
        from textual.screen import ModalScreen

        class OpenDialog(ModalScreen[None]):
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

        def _on_open(filename: str | None) -> None | None:
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
                    except json.JSONDecodeError as exc:
                        self.notify(f"Invalid JSON file: {exc}", severity="error")
                    except FileNotFoundError:
                        self.notify("File not found", severity="error")
                    except KeyError as exc:
                        self.notify(f"Missing required field: {exc}", severity="error")
                    except Exception as exc:
                        self.notify(f"Error loading file: {exc}", severity="error")
                else:
                    self.notify(f"File not found: {p}", severity="error")

        self.push_screen(OpenDialog(), _on_open)

    def _show_quit_confirm(self) -> None:
        from textual.screen import ModalScreen

        class QuitConfirm(ModalScreen[None]):
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

        def _on_confirm(quit: bool) -> None | None:
            if quit:
                self.exit()

        self.push_screen(QuitConfirm(), _on_confirm)

    def _do_save(self, path: Path) -> None:
        try:
            save(self.document, path)
            self._dirty = False
            self._update_status()
            self.notify(f"Saved to {path}", severity="information")
        except PermissionError as exc:
            self.notify(f"Permission denied: {exc}", severity="error")
        except json.JSONEncodeError as exc:
            self.notify(f"Invalid data: {exc}", severity="error")
        except OSError as exc:
            self.notify(f"Disk error: {exc}", severity="error")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")
