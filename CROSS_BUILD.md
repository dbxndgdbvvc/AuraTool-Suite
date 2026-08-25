# AuraTool-Suite — Cross-Platform Build Guide

## Quick Start

```bash
# Build both Linux + Windows from Ubuntu
python build.py

# Output goes to release_output/
#   AuraTool-Suite       (Linux x86_64 ELF binary)
#   AuraTool-Suite/      (Windows x64 directory with .exe)
```

## Build Options

### 1. Full Dual-Platform Build (Recommended)

Builds native Linux binary AND Windows .exe (via Wine) in one command:

```bash
python build.py
```

### 2. Linux Only

```bash
python build.py --linux-only
# or
python build.py --skip-windows
```

### 3. Windows Only

```bash
python build.py --windows-only
# or use the dedicated script:
python build_windows.py
```

### 4. Clean Only

Remove all build artifacts without building:

```bash
python build.py --clean-only
```

## Output

All binaries are placed in `release_output/`:

```
release_output/
├── AuraTool-Suite          # Linux x86_64 binary (~30 MB)
└── AuraTool-Suite/         # Windows x64 directory
    ├── AuraTool-Suite.exe  # Windows executable (~35 MB)
    └── ...                 # Supporting DLLs and files
```

No files are scattered across the desktop or project root.

## Requirements

### Linux Build

```bash
pip install pyinstaller
```

### Windows Cross-Compilation (Linux → Windows via Wine)

```bash
# 1. Install Wine
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install wine64 wine32

# 2. Download Windows Python installer
wget https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe

# 3. Install Python in Wine
wine python-3.12.5-amd64.exe /quiet InstallAllUsers=1 PrependPath=1

# 4. Install PyInstaller in Wine Python
wine python -m pip install pyinstaller
```

### Native Windows Build

```powershell
pip install pyinstaller
python build_windows.py
```

## How It Works

### Module Auto-Discovery

The build script automatically scans `core/`, `modules/`, `drivers/`, and `ui/`
directories to find all Python modules. This ensures PyInstaller bundles every
module even if it's not directly imported in the entry point chain.

### Data Bundling

The following directories are automatically bundled if they exist:
- `languages/` — Localization files
- `ui/` — UI resources
- `assets/` — Icons and images

### Hidden Imports

All discovered modules are added as `--hidden-import` flags to PyInstaller.
This prevents "module not found" errors at runtime for dynamically loaded
or conditionally imported modules.

## Build Script Architecture

```
build.py                  # Main orchestrator (Linux + Wine cross-compile)
build_windows.py          # Standalone Windows build script
release_output/           # All binaries land here
build/                    # Temporary PyInstaller build files (auto-cleaned)
dist/                     # Temporary PyInstaller dist files (auto-cleaned)
```

## Obfuscation (Optional)

PyArmor protects source code from reverse engineering:

```bash
pip install pyarmor
pyarmor reg <your-license-code>
python build.py
```

**PyArmor Trial:** Limited files, watermark, no BCC/RFT mode.  
**PyArmor Pro ($69/year):** Unlimited files, no watermark, full protection.

## GitHub Actions (CI/CD)

Push to `master` or create a tag to trigger automated builds:

```bash
git push origin master
# or
git tag v1.0.0 && git push origin v1.0.0
```

Both Windows and Linux executables are built automatically and
available as download artifacts.

## Troubleshooting

### "Wine or Windows Python not found"

Ensure Wine is installed and Python is available inside the Wine prefix:

```bash
wine python --version
# Should print: Python 3.12.x
```

### Hidden import errors at runtime

Run `python build.py` — it auto-discovers all modules. If a new module
is added to the project but not picked up, check that it's in `core/`,
`modules/`, `drivers/`, or `ui/`.

### Large binary size

The `--strip` flag is used on Linux to reduce binary size by removing
debug symbols. For further reduction, consider UPX compression:

```bash
sudo apt install upx
upx --best release_output/AuraTool-Suite
```
