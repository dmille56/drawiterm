---
name: requirements_v1_scope
description: Finalized v1 functional requirements and out-of-scope items for drawiterm
type: project
---

# V1 Scope (finalized 2026-03-27)

## Must Have
- Rectangle and ellipse drawing (click-drag to size)
- Arrow/connector drawing between two points
- Text labels (standalone and attached to shapes)
- Select, move, resize elements
- Delete elements
- Save to / load from .drawiterm JSON file
- Undo/redo (at least 50 levels)
- Pure character-cell rendering, SSH-compatible

## Out of Scope for V1
- Smart connectors that re-route around shapes
- Groups / containers
- Multiple canvases / pages
- Export to PNG, SVG, or any image format
- Collaboration / multiplayer
- Themes / style customization beyond basic line styles
- Plugin system
- Clipboard paste from external apps
- Freehand/pencil drawing

**Why:** V1 establishes the core drawing loop and proves the rendering model. Smart connectors and export are the most-requested follow-on features but add significant complexity.
