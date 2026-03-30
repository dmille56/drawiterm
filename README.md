[![CI](https://github.com/dmille56/drawiterm/actions/workflows/ci.yml/badge.svg)](https://github.com/dmille56/drawiterm/actions/workflows/ci.yml)

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

### With pipx (recommended)

```bash
pipx install drawiterm
```

### With Nix

```bash
nix run github:dmille56/drawiterm
```

### With pip

```bash
pip install drawiterm
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

### Setup lorri (and use it)
- https://github.com/nix-community/lorri
- Make sure to run lorri daemon as a service

```bash
lorri init
direnv allow        # activate Nix shell (sets PYTHONPATH=src automatically)
```

### --or-- Manually use nix development shell:
```bash
nix develop
export PYTHONPATH=src
```

### Install pre-commit hooks (so that it runs ruff everytime when you commit to fix issues)
`pre-commit install`

### Commands
```bash
python -m drawiterm # run from source

ruff check src/     # lint
ruff format src/    # format
pytest              # tests
```

See [SPEC.md](SPEC.md) for the full requirements specification.

## Release process

### Automatically
`python scripts/bump_version.py`

### --or-- Manually

- Bump the version in pyproject.toml and nix/drawiterm.nix (no leading "v" in the file values).
- Commit, then tag and push (tag must be v<version> and match pyproject.toml):

```bash
git tag -a "v0.1.0b1" -m "v0.1.0b1"
git push origin v0.1.0b1
```

### Other
The GitHub Actions "Release" workflow will lint, test, build, and create a GitHub Release.
If you add a repository secret PYPI_API_TOKEN (from PyPI), it will also publish to PyPI.
