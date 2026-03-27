---
name: project_constraints
description: Hard technology and platform constraints for drawiterm
type: project
---

- Language: Python (explicit user requirement)
- Rendering: Pure character-cell only — NO sixel, NO kitty graphics protocol, NO image rendering dependencies
- Must work over SSH (no terminal-specific graphics extensions)
- Target: standalone TUI application, not a library or web app
- Primary inspiration: Excalidraw (not a generic ASCII art tool)

**Why:** SSH compatibility is a hard constraint — the tool must work in any ANSI/VT100-compatible terminal over any transport.

**How to apply:** All rendering decisions must assume only ANSI escape codes + Unicode box-drawing characters are available. Test mental models against "does this work in a plain SSH session to a remote Linux box?"
