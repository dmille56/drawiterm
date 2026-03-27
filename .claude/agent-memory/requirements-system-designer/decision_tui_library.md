---
name: decision_tui_library
description: Chosen Python TUI library for drawiterm and the rationale behind the choice
type: project
---

**Decision: Textual (by Textualize)**

Rationale:
- Pure Python, pip-installable, no native extensions
- Built on top of Rich for rendering — excellent Unicode and ANSI support
- Event-driven architecture (on_key, on_mouse_move, on_click) suits a drawing tool
- Widget system allows composing a canvas area, toolbar, status bar cleanly
- Active development and large community as of 2025
- Mouse support (click, drag) works over SSH via standard terminal mouse protocols (ANSI escape sequences — no graphics extensions needed)
- CSS-like layout system simplifies panel arrangement

Alternatives considered and rejected:
- curses: Too low-level; would require reimplementing event loop, layout, and color management from scratch
- urwid: Mature but aging; widget model not well-suited to free-form canvas
- blessed: Good for low-level terminal control but no widget/layout system
- pytermgui: Less mature, smaller community, fewer examples of canvas-style apps

**How to apply:** Use Textual's App + Widget model. The canvas is a custom Widget subclass. Use Textual's built-in mouse event system. Do NOT reach for curses or direct terminal I/O — go through Textual's abstraction layer.
