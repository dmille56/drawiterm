# drawiterm

> Excalidraw-style system design sketching tool for the terminal

Draw boxes, arrows, and labels directly in your terminal using keyboard and mouse. Diagrams are saved as plain JSON files. Works over SSH — no graphics extensions, no browser, no GUI framework required.

```
╭──────────╮        ╭──────────╮        ╭──────────╮
│   API    │───────►│  Cache   │───────►│    DB    │
╰──────────╯        ╰──────────╯        ╰──────────╯
```

## Requirements

- Python 3.12+
- Any ANSI/VT100-compatible terminal (xterm, kitty, alacritty, tmux, etc.)

## Installation

### With Nix (recommended)

```bash
nix run github:dmille56/drawiterm
```

Or enter a dev shell:

```bash
nix develop
```

### With pip

```bash
pip install .
```

## Usage

```bash
drawiterm                       # new blank diagram
drawiterm mydiagram.drawiterm   # open existing file
```

## Tools

| Key | Tool |
|-----|------|
| `s` / `Escape` | Select |
| `r` | Rectangle |
| `e` | Ellipse |
| `d` | Diamond |
| `a` | Arrow |
| `l` | Line |
| `t` | Text |

Arrows and Lines are orthogonal by default; use Shift+Tab to toggle to straight.

## Key Bindings

| Key | Action |
|-----|--------|
| `Ctrl+S` | Save |
| `Ctrl+O` | Open file |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Ctrl+A` | Select all |
| `Ctrl+D` | Duplicate selection |
| `Delete` / `Backspace` | Delete selected elements |
| Arrow keys | Nudge selected elements |
| `Tab` | Next tool |
| `Shift+Tab` | Toggle arrow/line style (straight/orthogonal) |
| `Ctrl+Arrow` | Pan canvas |
| `Ctrl+Left-drag` | Pan canvas |
| `Ctrl+Q` | Quit |

Double-click an element to edit its label. Press `Escape` to commit the edit.

## File Format

Diagrams are saved as `.drawiterm` JSON files — human-readable and version-control friendly.

## Development

```bash
direnv allow        # activate Nix shell (sets PYTHONPATH=src automatically)
# or manually:
nix develop
export PYTHONPATH=src

python -m drawiterm # run from source

ruff check src/     # lint
ruff format src/    # format
pytest              # tests
```

See [SPEC.md](SPEC.md) for the full requirements specification.
