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
    ) -> None:
        dirty_flag = " *" if dirty else ""
        self.update(
            f" {tool.upper()}  col:{col} row:{row}  {filename}{dirty_flag}"
            "  | R=Rect E=Ellipse A=Arrow T=Text S=Select  Ctrl+S=Save Ctrl+Z=Undo Ctrl+Q=Quit"
        )
