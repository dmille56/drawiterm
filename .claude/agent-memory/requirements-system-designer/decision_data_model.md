---
name: decision_data_model
description: Internal data model and file format decisions for drawiterm
type: project
---

**Decision: JSON file format, Python dataclasses internally**

Core entities: Element (abstract), RectangleElement, EllipseElement, ArrowElement, TextElement, GroupElement.

File format: JSON with a top-level schema version field. Human-readable. One file per drawing (`.drawiterm` extension).

Coordinate system: Integer (col, row) character-cell coordinates. Origin (0,0) = top-left of canvas. No floating point — everything snaps to character grid.

**Why:** JSON is portable, human-readable, diffable in git, and trivially serializable from Python dataclasses. Character-cell integer coordinates are the natural unit for a terminal canvas — no sub-cell precision needed.

**How to apply:** All element positions and dimensions are stored as integer character-cell units. The renderer reads these coordinates directly to determine which cells to draw. No transformation layer needed between storage and render.
