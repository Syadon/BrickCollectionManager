# Building Brick Collection Manager

This document explains how to build executable applications for different operating systems using PyInstaller and uv.

## Prerequisites

- Python 3.11 or higher
- [uv](https://astral.sh/uv/) - Modern Python package manager
- Git (for cloning the repository)

### Installing uv

#### macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows:
Download and install from: https://astral.sh/uv/install

Or use PowerShell:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Quick Start

### For macOS/Linux:
```bash
chmod +x build.sh
./build.sh
```

### For Windows:
```cmd
build.bat
```

### Manual Build:
```bash
uv run python build.py
```

## Build Process

The build system automatically:

1. **Validates uv installation**: Ensures uv package manager is available
2. **Syncs dependencies**: Uses `uv sync` to install all project dependencies
3. **Installs build tools**: Adds development dependencies like Pillow
4. **Prepares resources**: Validates and prepares all necessary files
5. **Builds application**: Uses PyInstaller with optimized settings via uv
6. **Creates package**: Generates distribution-ready package

## Output

After successful build, you'll find:

### macOS:
- `dist/BrickCollectionManager.app` - macOS application bundle
- `dist/BrickCollectionManager-macos-{arch}/` - Distribution package

### Windows:
- `dist/BrickCollectionManager.exe` - Windows executable
- `dist/BrickCollectionManager-windows-{arch}/` - Distribution package

### Linux:
- `dist/BrickCollectionManager` - Linux executable
- `dist/BrickCollectionManager-linux-{arch}/` - Distribution package

## Platform-Specific Features

### macOS:
- Native .app bundle
- High-resolution display support
- macOS-style application info
- Code signing ready (when configured)

### Windows:
- Windows executable with icon
- No console window (GUI mode)
- Windows manifest included
- UPX compression for smaller size

### Linux:
- Native Linux executable
- Desktop integration ready
- Multiple icon sizes
- Standard Linux application structure

## Customization

### Icons:
Replace `resources/placeholder_icon.png` with your application icon:
- Windows: Convert to .ico format
- macOS: Convert to .icns format  
- Linux: Use PNG format

### Build Configuration:
Edit `BrickCollectionManager.spec` to customize:
- Hidden imports
- Excluded modules
- Data files
- Build options

### Build Settings:
Modify `build.toml` for additional configuration options.

## uv Commands Reference

### Development Setup:
```bash
# Sync all dependencies
uv sync

# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Run Python with uv environment
uv run python script.py

# Run PyInstaller
uv run pyinstaller BrickCollectionManager.spec
```

### Project Management:
```bash
# Update all dependencies
uv sync --upgrade

# Install specific dependency group
uv sync --group build

# Show dependency tree
uv tree

# Export requirements
uv export > requirements.txt
```

## Troubleshooting

### Common Issues:

1. **uv not found**: Install uv using the installation commands above
2. **Permission denied**: Ensure uv is in your PATH after installation
3. **Dependency conflicts**: Use `uv sync --upgrade` to resolve
4. **Missing dependencies**: Ensure all required packages are in pyproject.toml
5. **Resource files not found**: Check that all files in `resources/` exist
6. **Import errors**: Add missing modules to `hiddenimports` in .spec file
7. **Large file size**: Enable UPX compression and exclude unnecessary modules

### Debug Build:
To create a debug build with console output:
```bash
uv run pyinstaller --debug=all BrickCollectionManager.spec
```

### Clean Build:
To completely clean and rebuild:
```bash
# Remove build artifacts
rm -rf build/ dist/ __pycache__/

# Clean uv cache if needed
uv cache clean

# Rebuild
./build.sh
```

### Build Logs:
Check `build.log` for detailed build information and error messages.

## Distribution

### Creating Installers:

#### macOS:
Use `create-dmg` or similar tools to create .dmg installer:
```bash
# Install create-dmg
brew install create-dmg

# Create DMG
create-dmg \
  --volname "Brick Collection Manager" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --app-drop-link 450 120 \
  "BrickCollectionManager.dmg" \
  "dist/BrickCollectionManager.app"
```

#### Windows:
Use NSIS or Inno Setup to create installer:
```bash
# Using pynsist
pip install pynsist
pynsist installer.cfg
```

#### Linux:
Create .deb, .rpm, or AppImage:
```bash
# Using fpm for .deb/.rpm
gem install fpm

# Create .deb
fpm -s dir -t deb -n brick-collection-manager -v 1.0.0 \
    --description "LEGO Brick Collection Manager" \
    dist/BrickCollectionManager-linux-x64/=/usr/local/bin/
```

## GitHub Actions

For automated builds across platforms, see `.github/workflows/build.yml` (if available).

## Support

For build issues:
1. Check this documentation
2. Review build logs
3. Check PyInstaller documentation
4. Open an issue with build details