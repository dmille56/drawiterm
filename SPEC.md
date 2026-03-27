# drawiterm — System Design Specification
**Version:** 0.1 (Draft)
**Date:** 2026-03-27
**Status:** Requirements complete, awaiting implementation

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [Stakeholders and Users](#2-stakeholders-and-users)
3. [Constraints and Assumptions](#3-constraints-and-assumptions)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Out of Scope — V1](#6-out-of-scope--v1)
7. [TUI Library Selection](#7-tui-library-selection)
8. [High-Level Component Architecture](#8-high-level-component-architecture)
9. [Data Model](#9-data-model)
10. [File Format](#10-file-format)
11. [Rendering Model](#11-rendering-model)
12. [Key UX Interactions](#12-key-ux-interactions)
13. [V1 Milestone Scope](#13-v1-milestone-scope)
14. [Open Questions](#14-open-questions)
15. [Glossary](#15-glossary)

---

## 1. Product Vision

**drawiterm** is a standalone terminal drawing tool for system design sketches, modelled after Excalidraw. It runs entirely inside a terminal emulator using pure character-cell rendering — no graphics extensions, no browser, no GUI framework. Engineers draw boxes, arrows, and labels directly in the terminal using keyboard and mouse, then save their diagrams to disk.

**Target experience:** An engineer SSHed into a remote server opens drawiterm, sketches a quick architecture diagram — a few rectangles labelled "API", "DB", "Cache", connected by arrows — saves it as a `.drawiterm` file, and exits. Another engineer opens the same file and edits it. The entire workflow requires nothing beyond a standard terminal and Python.

**North star:** "Excalidraw in the terminal." The aesthetic is informal and sketch-like, not pixel-perfect. Speed of expression matters more than precision.

---

## 2. Stakeholders and Users

| Role | Description |
|---|---|
| **Primary user** | An engineer drawing system design diagrams from a terminal, possibly over SSH |
| **Secondary user** | A teammate opening and editing a saved `.drawiterm` file |
| **Operator** | The person installing drawiterm on a system (typically the primary user themselves) |

---

## 3. Constraints and Assumptions

### Hard Constraints

| ID | Constraint |
|---|---|
| CON-001 | Implementation language: Python 3.10+ |
| CON-002 | Rendering: pure character-cell only. No sixel, no kitty graphics protocol, no image output |
| CON-003 | Must function correctly over an SSH session to a Linux/macOS remote host |
| CON-004 | Must not require any native compiled extensions as a runtime dependency |
| CON-005 | Must work in any ANSI/VT100-compatible terminal (xterm, xterm-256color, screen, tmux) |

### Assumptions

| ID | Assumption |
|---|---|
| ASM-001 | The terminal supports ANSI mouse reporting (ANSI escape sequences for mouse events) — this is true for all modern terminal emulators and is tunnelled correctly over SSH |
| ASM-002 | The terminal supports at least 16 colors; 256-color support is preferred but not required for core functionality |
| ASM-003 | Terminal width is at least 80 columns and height at least 24 rows |
| ASM-004 | Unicode box-drawing characters (U+2500 block) render as single-width in the target terminal |
| ASM-005 | The primary use case is informal system design sketches, not pixel-precise technical drawings |
| ASM-006 | File I/O is to the local filesystem (or a remotely-mounted filesystem accessible as local) |

---

## 4. Functional Requirements

Requirements are prioritized using MoSCoW: **M** = Must Have, **S** = Should Have, **C** = Could Have.

### 4.1 Canvas and Viewport

| ID | Priority | Requirement |
|---|---|---|
| FR-001 | M | The system SHALL provide an infinite (or very large) scrollable canvas with a viewport that fills the terminal window |
| FR-002 | M | The system SHALL display the current cursor/tool position in character-cell coordinates in the status bar |
| FR-003 | S | The system SHALL support panning the viewport using keyboard shortcuts and middle-mouse drag |
| FR-004 | C | The system SHALL support zoom in/out that adjusts how many cells each logical canvas unit occupies |

### 4.2 Shape Drawing — Rectangle

| ID | Priority | Requirement |
|---|---|---|
| FR-010 | M | The system SHALL allow the user to draw a rectangle by clicking and dragging to define a bounding box |
| FR-011 | M | The system SHALL render rectangles using Unicode box-drawing characters for borders |
| FR-012 | M | Rectangles SHALL have a configurable label (text displayed inside the rectangle) |
| FR-013 | S | The system SHALL allow the user to choose between single-line and double-line border styles for rectangles |

### 4.3 Shape Drawing — Ellipse

| ID | Priority | Requirement |
|---|---|---|
| FR-020 | M | The system SHALL allow the user to draw an ellipse by clicking and dragging to define a bounding box |
| FR-021 | M | The system SHALL render ellipses using an ASCII/Unicode approximation within the bounding box |
| FR-022 | M | Ellipses SHALL support a text label centered within the shape |

### 4.4 Arrows and Connectors

| ID | Priority | Requirement |
|---|---|---|
| FR-030 | M | The system SHALL allow the user to draw an arrow between two points by clicking a start point and an end point |
| FR-031 | M | Arrows SHALL render as orthogonal (axis-aligned, L-shaped or Z-shaped) lines using box-drawing characters, with an arrowhead character at the destination end |
| FR-032 | S | The system SHALL support straight (diagonal) arrows as an alternative arrow style |
| FR-033 | S | Arrows SHALL snap to the nearest edge midpoint of a shape when the start or end point is dragged near a shape border (within 1 cell) |
| FR-034 | C | Arrows SHALL re-route automatically when a connected shape is moved |

### 4.5 Text Labels

| ID | Priority | Requirement |
|---|---|---|
| FR-040 | M | The system SHALL allow the user to place a standalone text label at any position on the canvas |
| FR-041 | M | Text labels SHALL support multi-line text (newline-delimited) |
| FR-042 | M | The system SHALL provide an in-place text editing mode activated by pressing Enter or double-clicking on a text element |

### 4.6 Selection and Manipulation

| ID | Priority | Requirement |
|---|---|---|
| FR-050 | M | The system SHALL allow the user to select a single element by clicking on it |
| FR-051 | M | The system SHALL allow the user to select multiple elements using a rubber-band (drag-to-select) selection rectangle |
| FR-052 | M | The system SHALL allow the user to move selected element(s) by dragging them |
| FR-053 | M | The system SHALL allow the user to resize a selected rectangle or ellipse by dragging its corner or edge handles |
| FR-054 | M | The system SHALL allow the user to delete selected element(s) with the Delete or Backspace key |
| FR-055 | S | The system SHALL allow the user to select all elements with Ctrl+A |

### 4.7 Undo and Redo

| ID | Priority | Requirement |
|---|---|---|
| FR-060 | M | The system SHALL support undo of the last action with Ctrl+Z |
| FR-061 | M | The system SHALL support redo with Ctrl+Y or Ctrl+Shift+Z |
| FR-062 | M | The undo history SHALL retain at least 50 steps per session |
| FR-063 | S | The undo history SHALL be reset when a new file is loaded |

### 4.8 File Operations

| ID | Priority | Requirement |
|---|---|---|
| FR-070 | M | The system SHALL save the current drawing to a `.drawiterm` JSON file with Ctrl+S |
| FR-071 | M | On first save, the system SHALL prompt the user to enter a filename |
| FR-072 | M | The system SHALL open an existing `.drawiterm` file passed as a command-line argument |
| FR-073 | M | The system SHALL open an existing `.drawiterm` file from within the application using Ctrl+O |
| FR-074 | S | The system SHALL prompt the user to save unsaved changes before exiting or loading another file |
| FR-075 | S | The system SHALL support Save As (Ctrl+Shift+S) to save to a new filename |

### 4.9 Clipboard (Internal)

| ID | Priority | Requirement |
|---|---|---|
| FR-080 | S | The system SHALL support copying selected element(s) to an internal clipboard with Ctrl+C |
| FR-081 | S | The system SHALL support pasting from the internal clipboard with Ctrl+V, placing the copy offset by 2 cells diagonally from the original |

### 4.10 Application Shell

| ID | Priority | Requirement |
|---|---|---|
| FR-090 | M | The system SHALL display a toolbar showing available tools (Select, Rectangle, Ellipse, Arrow, Text) |
| FR-091 | M | The system SHALL display a status bar showing: current tool, cursor position, filename, and unsaved-changes indicator |
| FR-092 | M | The system SHALL support quitting the application with Ctrl+Q or Ctrl+C (with unsaved-changes prompt) |
| FR-093 | M | The system SHALL be launchable from the command line as `drawiterm [filename]` |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement |
|---|---|
| NFR-001 | The canvas SHALL re-render within 50ms of any user input on a canvas containing up to 500 elements |
| NFR-002 | Application startup SHALL complete within 1 second on a modern machine |
| NFR-003 | File save and load SHALL complete within 500ms for files containing up to 1,000 elements |

### 5.2 Compatibility

| ID | Requirement |
|---|---|
| NFR-010 | The application SHALL run on Python 3.10, 3.11, 3.12, and 3.13 |
| NFR-011 | The application SHALL run on Linux and macOS |
| NFR-012 | The application SHALL function correctly when the terminal is connected over SSH |
| NFR-013 | The application SHALL function in tmux and GNU screen multiplexed sessions |
| NFR-014 | The application SHALL NOT depend on any terminal graphics protocol (sixel, kitty, iTerm2 inline images) |

### 5.3 Usability

| ID | Requirement |
|---|---|
| NFR-020 | All primary drawing operations SHALL be operable with mouse and keyboard combinations |
| NFR-021 | All primary drawing operations SHALL have a keyboard-only alternative (no operation SHALL require a mouse) |
| NFR-022 | A new user SHALL be able to create, save, and reload a diagram containing at least three shapes and two arrows within 5 minutes without documentation |

### 5.4 Reliability

| ID | Requirement |
|---|---|
| NFR-030 | The application SHALL NOT lose unsaved work due to an unhandled exception — it SHALL catch top-level exceptions, display an error, and offer to save a recovery file |
| NFR-031 | The `.drawiterm` file format SHALL be versioned so that future format changes can be detected and migration offered |

### 5.5 Maintainability

| ID | Requirement |
|---|---|
| NFR-040 | The codebase SHALL maintain a clean separation between: rendering logic, data model, input handling, and file I/O |
| NFR-041 | Each element type SHALL be self-describing (able to render itself given a canvas context) |
| NFR-042 | The project SHALL include a test suite covering the data model, serialization, and core rendering logic |

---

## 6. Out of Scope — V1

The following items are explicitly deferred to future versions. They MUST NOT be partially implemented in V1 in ways that would need to be reworked.

| Item | Reason for deferral |
|---|---|
| Smart connectors (arrows that route around shapes) | Significant algorithmic complexity (pathfinding); adds little value until larger diagrams are needed |
| Groups and containers (nested shapes) | Requires a recursive element tree, complicating selection, move, and rendering |
| Export to PNG, SVG, or any image format | Requires an off-canvas rendering pipeline; not achievable with pure character-cell rendering in a natural way |
| Collaboration / multiplayer / real-time sync | Out of scope for a local tool |
| Themes and style customization | Useful but not core to the drawing loop |
| Plugin or extension system | Premature before the architecture stabilizes |
| Clipboard interop with the OS clipboard | Terminal clipboard integration is terminal-dependent and fragile over SSH |
| Freehand / pencil drawing | Does not fit the system-design sketch use case well at character-cell resolution |
| Multiple pages / canvases in one file | Adds file format and UI complexity; one diagram per file is sufficient for V1 |
| Undo persistence across sessions | Undo history is in-memory only; it resets on close |

---

## 7. TUI Library Selection

### Decision: Textual (by Textualize)

**Install:** `pip install textual`

### Evaluation Matrix

| Criterion | Textual | curses | urwid | blessed | pytermgui |
|---|---|---|---|---|---|
| Mouse support (drag) | Yes, built-in | Manual | Partial | Manual | Partial |
| Works over SSH | Yes | Yes | Yes | Yes | Yes |
| No native extensions | Yes | stdlib (C) | Yes | Yes | Yes |
| Layout system | CSS-like, strong | None | Box model | None | Limited |
| Active maintenance | Yes (2025) | stdlib | Slow | Slow | Slow |
| Canvas/free-draw precedent | Growing | Many | Few | Few | Few |
| Python 3.10+ | Yes | Yes | Yes | Yes | Yes |

### Justification

Textual is the only library in this set that provides a complete, well-maintained event-driven framework with:

1. **Mouse drag events** delivered as clean Python objects (`MouseDown`, `MouseMove`, `MouseUp`) via standard ANSI mouse protocols — these work identically over SSH.
2. **A `Widget.render()` model** that maps directly to the "canvas draws itself" mental model. A `CanvasWidget` subclass overrides `render()` to iterate over all elements and paint cells.
3. **Rich integration** for cell-level color and style control without fighting escape codes directly.
4. **Compositor / layout engine** that handles toolbar + canvas + status bar arrangement without manual geometry.

The stdlib `curses` module is available without installation but its programming model would require reimplementing everything Textual provides: an event loop, layout, color management, and widget abstraction. This is months of accidental complexity before a single rectangle is drawn.

### Architecture Note on Textual's Render Model

Textual's `Widget` renders via a `render()` method that returns a Rich `RenderableType`. For a free-form canvas, the most appropriate approach is to return a `Rich.Segment`-based renderable (a list of character+style rows) built by the canvas painter. This gives per-cell control without leaving Textual's abstraction.

---

## 8. High-Level Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        drawiterm (CLI entry)                    │
│                     drawiterm [filename]                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DrawitermApp (Textual App)                 │
│  Owns: document state, undo stack, tool state, file path        │
│  Orchestrates: layout, event routing, modal dialogs             │
│                                                                 │
│  ┌─────────────┐  ┌──────────────────────────┐  ┌───────────┐  │
│  │  ToolBar    │  │      CanvasWidget         │  │  Side     │  │
│  │  Widget     │  │  (core interactive area)  │  │  Panel    │  │
│  │             │  │                           │  │  (future) │  │
│  │  [Select]   │  │  Handles: mouse events,   │  │           │  │
│  │  [Rect]     │  │  keyboard, viewport pan,  │  └───────────┘  │
│  │  [Ellipse]  │  │  cursor, rubber-band sel  │                 │
│  │  [Arrow]    │  │                           │                 │
│  │  [Text]     │  └──────────┬───────────────┘                 │
│  └─────────────┘             │                                  │
│                              │                                  │
│  ┌───────────────────────────▼──────────────────────────────┐  │
│  │                      StatusBar Widget                    │  │
│  │   tool | cursor (col,row) | filename | * unsaved         │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Core Domain Layer                         │
│                                                                  │
│  ┌─────────────────────┐    ┌────────────────────────────────┐  │
│  │   Document          │    │   UndoStack                    │  │
│  │                     │    │                                │  │
│  │  elements: list     │    │  push(command: Command)        │  │
│  │  next_id: int       │    │  undo() / redo()               │  │
│  │                     │    │  max_depth: 50                 │  │
│  │  add_element()      │    └────────────────────────────────┘  │
│  │  remove_element()   │                                        │
│  │  move_element()     │    ┌────────────────────────────────┐  │
│  │  resize_element()   │    │   ToolController               │  │
│  │  get_at(col, row)   │    │                                │  │
│  └─────────────────────┘    │  current_tool: Tool enum       │  │
│                             │  tool_state: dict              │  │
│  ┌──────────────────────┐   │  handle_mouse_down()           │  │
│  │   Element hierarchy  │   │  handle_mouse_move()           │  │
│  │                      │   │  handle_mouse_up()             │  │
│  │  Element (base)      │   └────────────────────────────────┘  │
│  │    RectElement       │                                        │
│  │    EllipseElement    │                                        │
│  │    ArrowElement      │                                        │
│  │    TextElement       │                                        │
│  └──────────────────────┘                                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │   CanvasPainter                                            │  │
│  │                                                            │  │
│  │  paint(document, viewport, selection, tool_state)         │  │
│  │  → CellGrid (col x row array of (char, style) tuples)     │  │
│  │                                                            │  │
│  │  Delegates to per-element renderers:                      │  │
│  │    RectRenderer, EllipseRenderer, ArrowRenderer,          │  │
│  │    TextRenderer, SelectionOverlayRenderer                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │   FileIO                                                   │  │
│  │                                                            │  │
│  │  save(document, path: Path)                               │  │
│  │  load(path: Path) → Document                              │  │
│  │  validate_version(data: dict) → bool                      │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|---|---|
| `DrawitermApp` | Textual App subclass. Owns document, undo stack, current tool. Routes events between widgets and domain layer. |
| `CanvasWidget` | Textual Widget subclass. Translates mouse/keyboard events into tool controller calls. Calls `CanvasPainter` to build render output. Manages viewport offset. |
| `ToolBar` | Displays and switches the active drawing tool. |
| `StatusBar` | Displays read-only state (tool name, cursor position, filename, dirty flag). |
| `Document` | Pure data container. Holds the ordered list of elements. Provides spatial lookup. No rendering logic. |
| `UndoStack` | Command pattern implementation. Each mutating operation is a `Command` object with `execute()` and `undo()` methods. |
| `ToolController` | State machine for each drawing tool. Translates raw mouse events + current tool into Document mutations. |
| `CanvasPainter` | Stateless. Takes a Document + viewport + selection state and produces a `CellGrid`. Delegates to per-element renderers. |
| `FileIO` | Serializes/deserializes Document to/from JSON. Handles schema version checking. |

---

## 9. Data Model

### 9.1 Coordinate System

All positions use **integer character-cell coordinates**. `(col=0, row=0)` is the top-left cell of the canvas (not the viewport). The viewport defines a window into the canvas.

```
canvas (0,0) ─────────────────────────────────────────────────────►  col
    │
    │   (viewport_col, viewport_row) ┌──────────────────────┐
    │                                │                      │
    │                                │  visible terminal    │
    │                                │  area                │
    │                                │                      │
    │                                └──────────────────────┘
    ▼
   row
```

**Terminal col, row → canvas col, row:**
```
canvas_col = terminal_col + viewport_col_offset
canvas_row = terminal_row + viewport_row_offset
```

### 9.2 Element Base Class

```python
@dataclass
class Element:
    id: int                    # unique within Document, assigned sequentially
    element_type: str          # "rect" | "ellipse" | "arrow" | "text"
    z_order: int               # paint order (higher = on top)
    label: str                 # text content (may be empty)
    style: ElementStyle        # line style, colors
```

### 9.3 Element Types

```python
@dataclass
class RectElement(Element):
    element_type: str = "rect"
    col: int = 0               # left edge, canvas coordinates
    row: int = 0               # top edge, canvas coordinates
    width: int = 10            # in character cells (includes border)
    height: int = 5            # in character cells (includes border)
    border_style: str = "single"  # "single" | "double" | "rounded"

@dataclass
class EllipseElement(Element):
    element_type: str = "ellipse"
    col: int = 0               # bounding box left
    row: int = 0               # bounding box top
    width: int = 10            # bounding box width
    height: int = 5            # bounding box height

@dataclass
class ArrowElement(Element):
    element_type: str = "arrow"
    start_col: int = 0
    start_row: int = 0
    end_col: int = 10
    end_row: int = 0
    style: str = "orthogonal"  # "orthogonal" | "straight"
    start_element_id: int | None = None   # snapped-to element, if any
    end_element_id: int | None = None     # snapped-to element, if any

@dataclass
class TextElement(Element):
    element_type: str = "text"
    col: int = 0
    row: int = 0
    text: str = ""             # newline-delimited for multi-line

@dataclass
class ElementStyle:
    fg_color: str = "default"  # Rich color string or "default"
    bg_color: str = "default"
    bold: bool = False
```

### 9.4 Document

```python
@dataclass
class Document:
    schema_version: int = 1
    title: str = "Untitled"
    elements: list[Element] = field(default_factory=list)
    _next_id: int = field(default=1, init=False, repr=False)

    def add(self, element: Element) -> Element
    def remove(self, element_id: int) -> Element
    def get_by_id(self, element_id: int) -> Element | None
    def get_at(self, col: int, row: int) -> list[Element]  # hit test
    def elements_in_rect(self, col, row, width, height) -> list[Element]
```

### 9.5 Viewport

```python
@dataclass
class Viewport:
    col_offset: int = 0      # canvas column at the left edge of the terminal
    row_offset: int = 0      # canvas row at the top edge of the terminal
    terminal_width: int = 80
    terminal_height: int = 24

    def to_canvas(self, term_col: int, term_row: int) -> tuple[int, int]
    def to_terminal(self, canvas_col: int, canvas_row: int) -> tuple[int, int]
    def is_visible(self, canvas_col: int, canvas_row: int) -> bool
```

### 9.6 Command Pattern for Undo

```python
class Command(Protocol):
    def execute(self, document: Document) -> None: ...
    def undo(self, document: Document) -> None: ...

# Examples:
class AddElementCommand:
    element: Element

class DeleteElementsCommand:
    element_ids: list[int]

class MoveElementsCommand:
    moves: list[tuple[int, int, int]]  # (element_id, delta_col, delta_row)

class ResizeElementCommand:
    element_id: int
    old_rect: tuple[int, int, int, int]  # col, row, width, height
    new_rect: tuple[int, int, int, int]

class EditTextCommand:
    element_id: int
    old_text: str
    new_text: str
```

---

## 10. File Format

### 10.1 Extension and MIME

- Extension: `.drawiterm`
- Format: UTF-8 encoded JSON
- No binary encoding

### 10.2 Schema

```json
{
  "schema_version": 1,
  "title": "My Architecture Diagram",
  "elements": [
    {
      "id": 1,
      "element_type": "rect",
      "z_order": 0,
      "col": 5,
      "row": 3,
      "width": 12,
      "height": 5,
      "border_style": "single",
      "label": "API Server",
      "style": {
        "fg_color": "default",
        "bg_color": "default",
        "bold": false
      }
    },
    {
      "id": 2,
      "element_type": "arrow",
      "z_order": 1,
      "start_col": 17,
      "start_row": 5,
      "end_col": 28,
      "end_row": 5,
      "style_type": "orthogonal",
      "start_element_id": 1,
      "end_element_id": 3,
      "label": "",
      "style": {
        "fg_color": "default",
        "bg_color": "default",
        "bold": false
      }
    }
  ]
}
```

### 10.3 Version Migration

When `FileIO.load()` reads a file with `schema_version` lower than the current version, it SHALL:
1. Log a warning to the status bar
2. Apply forward migrations sequentially (migration functions registered per version step)
3. Mark the document as dirty so the user is prompted to save

---

## 11. Rendering Model

### 11.1 Cell Grid

The painter produces a `CellGrid`: a two-dimensional array of `(character: str, style: Style)` tuples, sized to the terminal viewport dimensions. The canvas widget converts this to a Textual/Rich `Strip`-based renderable.

### 11.2 Paint Order

Elements are painted in ascending `z_order`. Later elements overwrite earlier ones cell by cell. The selection overlay and tool preview (ghost shape during drawing) are painted last, above all elements.

### 11.3 Rectangle Rendering

Box-drawing character map for single-line style:

```
┌─────┐     corners: ┌ ┐ └ ┘
│     │     horizontal: ─
└─────┘     vertical: │
```

Double-line style uses: `╔ ╗ ╚ ╝ ═ ║`

Rounded style uses: `╭ ╮ ╰ ╯ ─ │`

Label text is centered horizontally and vertically within the interior (excluding border cells). Text is truncated with `…` if it exceeds the interior width.

### 11.4 Ellipse Rendering

Ellipse approximation at character-cell resolution uses a midpoint ellipse algorithm mapping each (col, row) cell to the ellipse equation:

```
(col - cx)^2 / a^2 + (row - cy)^2 / b^2 = 1
```

Cells where the ellipse perimeter passes are drawn with `·` or `o`. For small ellipses (width < 6 or height < 3), a lookup table of precomputed shapes is used for visual quality. The label is rendered in the center cell(s).

### 11.5 Arrow Rendering

**Orthogonal arrows:** Route using an L-shape (one horizontal segment + one vertical segment, or vice versa) or Z-shape (two right-angle bends). The bend point is chosen to minimize visual collisions. Characters used:

```
Horizontal run: ─
Vertical run:   │
Corners:        ┐ ┘ └ ┌
Arrowheads:     ► ◄ ▲ ▼  (for E, W, N, S arrival directions)
```

**Straight arrows:** Bresenham's line algorithm determines which cells to fill. Diagonal cells use `/` or `\`. The arrowhead is placed at the end cell.

### 11.6 Selection Overlay

Selected elements render with a highlighted border (color inversion or a bright color outline drawn one cell outside the element's bounding box). Resize handles appear as `+` characters at the four corners and four edge midpoints of the bounding box.

### 11.7 Tool Preview (Ghost)

While a draw operation is in progress (mouse button held), a preview of the shape-in-progress is rendered using a dimmed style. This gives immediate feedback on the size and position of the shape being drawn.

---

## 12. Key UX Interactions

### 12.1 Tool Selection

| Action | Effect |
|---|---|
| `R` key | Switch to Rectangle tool |
| `E` key | Switch to Ellipse tool |
| `A` key | Switch to Arrow tool |
| `T` key | Switch to Text tool |
| `S` or `Escape` | Switch to Select tool |
| Click toolbar button | Switch to that tool |

### 12.2 Drawing Shapes (Rectangle / Ellipse)

| Action | Effect |
|---|---|
| Mouse down | Anchor first corner |
| Mouse drag | Preview ghost shape expanding from anchor |
| Mouse up | Commit shape to document |
| Escape (during drag) | Cancel operation, no shape added |

### 12.3 Drawing Arrows

| Action | Effect |
|---|---|
| Mouse down | Anchor start point; if near a shape edge, snap to it |
| Mouse drag | Preview arrow routing |
| Mouse up | Commit arrow; if near a shape edge, snap end to it |
| Escape (during drag) | Cancel |

### 12.4 Adding Text

| Action | Effect |
|---|---|
| Mouse click (Text tool) | Place text element at clicked position; enter edit mode immediately |
| Enter / F2 (Select tool, text selected) | Enter edit mode on selected text element |
| Double-click any element | Enter label-edit mode for that element |
| In edit mode: type | Append to text |
| In edit mode: Enter | Insert newline |
| In edit mode: Escape | Commit text and exit edit mode |

### 12.5 Selection and Manipulation

| Action | Effect |
|---|---|
| Click (Select tool) | Select element under cursor; deselect if clicking empty space |
| Drag on empty space | Rubber-band rectangle selection |
| Ctrl+A | Select all |
| Escape | Deselect all |
| Drag selected element | Move element(s) |
| Drag corner/edge handle | Resize element (rect or ellipse) |
| Delete / Backspace | Delete selected element(s) |
| Arrow keys | Nudge selected element(s) by 1 cell |

### 12.6 Viewport Navigation

| Action | Effect |
|---|---|
| Middle-mouse drag | Pan viewport |
| Ctrl+Arrow keys | Pan viewport by 5 cells |
| Ctrl+Shift+H / Home | Reset viewport to origin (0,0) |

### 12.7 File Operations

| Action | Effect |
|---|---|
| Ctrl+S | Save (prompts for filename if new) |
| Ctrl+Shift+S | Save As |
| Ctrl+O | Open file (prompts with text input) |
| Ctrl+Q | Quit (prompts if unsaved changes) |

### 12.8 Undo / Redo

| Action | Effect |
|---|---|
| Ctrl+Z | Undo last action |
| Ctrl+Y or Ctrl+Shift+Z | Redo |

### 12.9 Clipboard (Internal)

| Action | Effect |
|---|---|
| Ctrl+C | Copy selected element(s) to internal clipboard |
| Ctrl+V | Paste, placing copies offset by (2, 2) cells |

---

## 13. V1 Milestone Scope

V1 is defined as the smallest complete, useful product. A user can create, edit, save, and reload a system design diagram with the core shape types.

### V1 Deliverables

| # | Deliverable | Acceptance Criteria |
|---|---|---|
| 1 | Project scaffolding | `pip install -e .` succeeds; `drawiterm` launches in a terminal |
| 2 | Canvas widget with viewport | Blank canvas renders; viewport pans with Ctrl+Arrow |
| 3 | Rectangle drawing | User can draw a rectangle with click-drag; it renders with box-drawing chars |
| 4 | Rectangle label editing | Double-click rectangle opens inline text editor; Escape commits |
| 5 | Ellipse drawing | User can draw an ellipse with click-drag |
| 6 | Arrow drawing | User can draw an orthogonal arrow between two points |
| 7 | Arrow snapping to shapes | Arrow endpoints snap to the nearest edge midpoint of a nearby shape |
| 8 | Text label placement | User can place and edit a standalone text label |
| 9 | Select tool | Click to select; drag to rubber-band select; Delete to remove |
| 10 | Move elements | Drag selected element(s) to move |
| 11 | Resize rectangles/ellipses | Drag corner handles to resize |
| 12 | Undo/redo | Ctrl+Z / Ctrl+Y works for all mutating operations |
| 13 | Save and load | Ctrl+S saves; `drawiterm myfile.drawiterm` loads; format is valid JSON |
| 14 | Status bar | Shows tool, cursor position, filename, dirty flag |
| 15 | Toolbar | Shows available tools; clicking switches tool |

### V1 Non-Goals (Confirmed Deferrals)

- Straight-line arrows
- Arrow re-routing when shapes move
- Internal clipboard (copy/paste)
- Multiple border styles (single-line only in V1)
- Zoom
- Save As / Open dialog (Ctrl+O deferred; command-line argument only in V1)

### V1 Suggested Implementation Order

```
Phase 1 — Foundation (no visible output yet)
  1. Project structure, pyproject.toml, Textual app skeleton
  2. Element dataclasses + Document class
  3. FileIO (save/load) with schema version
  4. UndoStack with Command protocol

Phase 2 — Visible Canvas
  5. CanvasWidget with blank canvas render
  6. Viewport + pan
  7. StatusBar (static for now)
  8. ToolBar (static for now)

Phase 3 — First Shape
  9. RectRenderer
  10. Rectangle draw tool (mouse down/drag/up → AddElementCommand)
  11. Ghost preview during draw
  12. ToolBar activates Rect tool

Phase 4 — More Shapes
  13. EllipseRenderer + Ellipse draw tool
  14. TextRenderer + Text placement + inline editing

Phase 5 — Arrows
  15. Orthogonal arrow router
  16. ArrowRenderer
  17. Arrow draw tool + shape edge snapping

Phase 6 — Selection and Edit
  18. Hit testing (get_at)
  19. Select tool: single click, rubber-band
  20. Move via drag
  21. Resize handles + drag
  22. Delete
  23. Label editing for rect/ellipse

Phase 7 — Polish and File I/O
  24. Undo/redo wired to all commands
  25. Save / load wired to Ctrl+S and CLI arg
  26. Unsaved-changes dirty flag
  27. Error handling (crash recovery)
```

---

## 14. Open Questions

| ID | Question | Impact | Decision Criteria |
|---|---|---|---|
| OQ-001 | Should the canvas be truly infinite, or bounded (e.g., 1000x1000 cells)? | Viewport implementation, file size | Infinite is cleaner conceptually but requires sparse data structures; bounded is simpler. Recommend: 500x200 logical canvas for V1, no scroll beyond that. |
| OQ-002 | How should arrow routing handle the case where start and end are on the same row or column? | Arrow renderer | Degenerate case: render as a straight line segment |
| OQ-003 | Should labels that exceed the interior of a rectangle wrap to multiple lines, or truncate? | Text rendering | Truncation is simpler for V1; wrapping deferred |
| OQ-004 | Should the `.drawiterm` file be pretty-printed (human-readable) or compact JSON? | File I/O | Recommend pretty-printed (indent=2) so files are diffable in git |
| OQ-005 | What happens when the user resizes the terminal window mid-session? | Textual resize event | Textual handles viewport resize automatically; canvas painter must respect current terminal dimensions on each render |
| OQ-006 | Should Ctrl+C copy-to-clipboard or quit the app? Conflict with standard terminal behavior. | UX | Recommend: Ctrl+Q to quit; Ctrl+C reserved for copy. But Ctrl+C sends SIGINT in many terminals — needs testing. |

---

## 15. Glossary

| Term | Definition |
|---|---|
| **Canvas** | The infinite (or large bounded) coordinate space in which elements are placed, measured in character-cell units |
| **Viewport** | The portion of the canvas currently visible in the terminal window |
| **Cell** | A single character position in the terminal, defined by (column, row) |
| **Element** | A single drawable object on the canvas: a rectangle, ellipse, arrow, or text label |
| **Document** | The complete set of elements in a single drawing, plus metadata |
| **Tool** | The current interaction mode (Select, Rectangle, Ellipse, Arrow, Text) |
| **Ghost** | A preview rendering of the shape currently being drawn, shown during mouse drag |
| **Rubber-band selection** | A selection rectangle drawn by dragging on empty canvas space to select all elements within it |
| **Orthogonal arrow** | An arrow that travels only horizontally and vertically (no diagonal segments) |
| **Snapping** | Automatically aligning an arrow endpoint to the nearest edge midpoint of a nearby shape |
| **Command** | An object encapsulating a single reversible mutation of the Document, used for undo/redo |
| **Dirty flag** | A boolean indicating the Document has unsaved changes |
| **CellGrid** | The intermediate 2D rendering output produced by the CanvasPainter before being passed to Textual |
| **z_order** | The paint order of elements; higher z_order elements are drawn on top of lower ones |
