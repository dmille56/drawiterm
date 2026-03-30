"""Status bar widget."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def update_status(
        self,
        tool: str,
        col: int,
        row: int,
        filename: str,
        dirty: bool,
        selection_count: int = 0,
        is_editing: bool = False,
        can_undo: bool = False,
        can_redo: bool = False,
        has_arrow_or_line_selected: bool = False,
    ) -> None:
        dirty_flag = "*" if dirty else ""
        name = f"{filename}{dirty_flag}"
        pos = f"col:{col} row:{row}"

        if is_editing:
            hint = "Esc=commit  Enter=newline(text)  ←→=cursor"
        elif tool == "select":
            if selection_count == 0:
                hint = "Click=select  Drag=rubber-band  Ctrl+A=select-all  R/E/D/A/L/T=tool"
            else:
                hint = f"{selection_count} selected  Del=delete  Ctrl+D=duplicate  Arrow=nudge  "
                if has_arrow_or_line_selected:
                    hint += "Shift+Tab=toggle-arrow/line  "
                hint += "Enter/F2=edit  Esc=deselect"
        elif tool == "rect":
            hint = "Drag to draw rect  S/Esc=cancel"
        elif tool == "ellipse":
            hint = "Drag to draw ellipse  S/Esc=cancel"
        elif tool == "diamond":
            hint = "Drag to draw diamond  S/Esc=cancel"
        elif tool == "arrow":
            hint = "Drag to draw arrow  S/Esc=cancel"
        elif tool == "line":
            hint = "Drag to draw line  S/Esc=cancel"
        elif tool == "text":
            hint = "Click to place text  S/Esc=cancel"
        else:
            hint = "R=Rect E=Ellipse A=Arrow T=Text S=Select"

        undo_indicator = ""
        if can_undo:
            undo_indicator += " Ctrl+Z=undo"
        if can_redo:
            undo_indicator += " Ctrl+Y=redo"

        self.update(
            f" {tool.upper()}  {pos}  {name}  | {hint}{undo_indicator}  "
            "Ctrl+O=open Ctrl+S=save "
            "Ctrl+Q=quit"
        )
