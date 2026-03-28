"""Toolbar widget showing the available drawing tools."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Button, Static


TOOL_BUTTONS = [
    ("select", "S Select", "s"),
    ("rect", "R Rect", "r"),
    ("ellipse", "E Ellipse", "e"),
    ("diamond", "D Diamond", "d"),
    ("arrow", "A Arrow", "a"),
    ("line", "L Line", "l"),
    ("text", "T Text", "t"),
]


class ToolBar(Static):
    DEFAULT_CSS = """
    ToolBar {
        height: 1;
        layout: horizontal;
        background: $panel;
    }
    ToolBar Button {
        height: 1;
        min-width: 10;
        border: none;
        background: $panel;
        color: $text;
    }
    ToolBar Button.active {
        background: $accent;
        color: $text;
    }
    """

    class ToolSelected(Message):
        def __init__(self, tool_id: str) -> None:
            super().__init__()
            self.tool_id = tool_id

    def compose(self) -> ComposeResult:
        for tool_id, label, _ in TOOL_BUTTONS:
            btn = Button(label, id=f"tool_{tool_id}", classes="active" if tool_id == "select" else "")
            yield btn

    def set_active(self, tool_id: str) -> None:
        for tid, _, _ in TOOL_BUTTONS:
            btn = self.query_one(f"#tool_{tid}", Button)
            if tid == tool_id:
                btn.add_class("active")
            else:
                btn.remove_class("active")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("tool_"):
            tool_id = btn_id[5:]
            self.post_message(self.ToolSelected(tool_id))
