# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run in development
uv run python main.py

# Install dependencies
uv sync

# Build distributable
./build.sh          # macOS/Linux
build.bat           # Windows

# Rebuild Qt UI files from .ui sources
./buildUI.sh        # macOS/Linux
buildUI.bat         # Windows
```

## Architecture

Desktop app for organizing LEGO brick collections. Fully local/offline — SQLite database, no cloud sync.

**Stack:** Python 3.11+, PySide6 (Qt), SQLite, qt-material theme, PyInstaller

**Entry point:** `main.py` → initializes DB, theme, launches `src/mainWindow.py`

**Layers:**
- `src/mainWindow.py` — 6-tab stacked layout (toolbar nav)
- `src/widgets/` — one widget per tab (container list, search, add manual, camera, file import, DB management)
- `src/database.py` — all SQLite access; schema defined in `resources/schema.sql`
- `src/partsFileParser.py` — BrickLink XML import
- `src/brickRecongnition.py` — Brickognize API integration for camera-based part ID
- `src/imageProvider.py` — part image caching/retrieval
- `config.py` — paths, constants, `DEBUG_MODE` flag

**Database tables:** `colors`, `categories`, `parts`, `colors_parts`, `containers`, `parts_collection`

**Path resolution:** Dev mode uses project root; packaged builds use platform user dirs (macOS: `~/Library/Application Support/BrickCollectionManager`, Windows: `%APPDATA%/BrickCollectionManager`, Linux: `~/.local/share/BrickCollectionManager`). Logic in `config.py`.

## UI Files

Qt Designer `.ui` files live in `ui/` and compile to `ui/ui_*.py`. **Never edit `ui_*.py` directly** — regenerate via `buildUI.sh`/`buildUI.bat` after changing `.ui` files.

## External Dependencies

- **Brickognize API** (`api.brickognize.com`) — brick recognition from camera images
- **BrickLink** — source of part catalog XML files (user-imported)
