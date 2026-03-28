# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**drawiterm** is an Excalidraw-style system design sketching tool for the terminal — a TUI application built with Python and the [Textual](https://textual.textualize.io/) framework. It renders diagrams using Unicode box-drawing characters in pure character-cell mode (no graphics protocols required).

## Development Environment

The project uses Nix flakes for a reproducible dev environment with direnv:

```bash
direnv allow   # activates the Nix shell; sets PYTHONPATH=src
```

Without direnv, enter the shell manually:

```bash
nix develop
export PYTHONPATH=src
```

## Common Commands

```bash
# Run the application
python -m drawiterm [filename.drawiterm]

# Lint / format
ruff check src/
ruff format src/

# Tests (when written)
pytest
pytest tests/path/to/test_file.py::test_name   # single test

# Build (Nix)
nix build
```

## Architecture

The codebase follows a clean layered architecture:

```
DrawitermApp (Textual App)
  └─ Widgets: ToolBar | CanvasWidget | StatusBar
       └─ ToolController        ← input state machine, tool logic
       └─ UndoStack             ← Command objects for all mutations
            └─ CanvasPainter    ← stateless renderer: Document → CellGrid
                 └─ Document    ← data model: list of Elements + Viewport
```

**Key design principles:**
- **All mutations go through Commands** (`commands.py`) — never mutate `Document` directly. This is required for undo/redo correctness.
- **`CanvasPainter.paint()` is pure** — takes Document + selection state, returns a `CellGrid`. No side effects.
- **`ToolController`** owns all mouse event state (dragging, resizing, rubber-band selection). The canvas widget delegates raw events to it.

## Key Modules

| File | Responsibility |
|------|---------------|
| `src/drawiterm/models.py` | `Document`, `Element` subtypes (`RectElement`, `EllipseElement`, `ArrowElement`, `TextElement`), `Viewport`, `ElementStyle` |
| `src/drawiterm/commands.py` | Command protocol + concrete commands (`AddElementCommand`, `DeleteElementsCommand`, `MoveElementsCommand`, etc.), `UndoStack` |
| `src/drawiterm/painter.py` | `CanvasPainter`, `Cell`, `CellGrid`; all box-drawing character logic, element rendering, selection handles, ghost previews |
| `src/drawiterm/tool_controller.py` | `ToolController`, `Tool` enum; mouse event handlers and tool state machine |
| `src/drawiterm/file_io.py` | JSON save/load; schema versioning for `.drawiterm` files |
| `src/drawiterm/app.py` | `DrawitermApp`; global keybindings, dialogs, widget composition |
| `src/drawiterm/widgets/canvas.py` | `CanvasWidget`; Textual rendering of `CellGrid`, mouse/key forwarding |

## Coordinate System

- **Canvas coordinates**: virtual space (default 500×200 cells), the authoritative coordinate system for all element positions.
- **Viewport**: offset into the canvas that maps canvas coords to terminal screen coords.
- `(col, row)` on elements is always in canvas coordinates. Convert to screen coords by subtracting the viewport offset.

## File Format

`.drawiterm` files are JSON with `schema_version`, `title`, and an `elements` array. Each element has `id`, `element_type`, `z_order`, `col`, `row`, and type-specific fields. See `file_io.py` for the schema.

## Rendering Pipeline

1. Background dot grid (every 5 cells)
2. Elements sorted by `z_order` — box-drawing chars for rect/ellipse borders, arrowhead glyphs (►◄▲▼) for arrows
3. Ghost preview (dim cyan) for shape being drawn
4. Selection handles (bright cyan) on selected elements
5. Rubber-band rect during drag-to-select

Box-drawing sets: **single** `┌─┐│└┘`, **double** `╔═╗║╚╝`, **rounded** `╭─╮│╰╯`

## Spec

`SPEC.md` is the authoritative requirements document. Check it for expected behaviour before implementing features or fixing edge cases.
