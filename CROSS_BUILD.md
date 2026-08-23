# AuraTool-Suite — Cross-Platform Build Guide

## Build Options

### 1. Native Linux Build (Current Machine)
```bash
# Install PyInstaller in venv
venv/bin/pip install pyinstaller

# Build
venv/bin/python build.py

# Output: dist/AuraTool-Suite/AuraTool-Suite (ELF x86_64)
```

### 2. Native Windows Build
```powershell
# On Windows with Python installed
pip install pyinstaller

# Build
python build_windows.py

# Output: dist\AuraTool-Suite\AuraTool-Suite.exe
```

### 3. GitHub Actions (Automated CI/CD)
Push to `master` or create a tag to trigger automated builds:
```bash
git push origin master
# or
git tag v1.0.0
git push origin v1.0.0
```

Both Windows and Linux executables are built automatically and
available as download artifacts.

### 4. Wine Cross-Compilation (Linux → Windows)
```bash
# Install Wine
sudo apt install wine64

# Install Windows Python in Wine
wine msiexec /i python-3.12.msi

# Install PyInstaller in Wine Python
wine ~/.wine/drive_c/Python312/python.exe -m pip install pyinstaller

# Build Windows .exe from Linux
wine ~/.wine/drive_c/Python312/python.exe build_windows.py
```

## Build Output

| Platform | File | Size |
|----------|------|------|
| Linux x64 | `dist/AuraTool-Suite/AuraTool-Suite` | ~31 MB |
| Windows x64 | `dist\AuraTool-Suite\AuraTool-Suite.exe` | ~35 MB |

## Obfuscation (Optional)

PyArmor protects source code from reverse engineering:
```bash
# Install PyArmor
pip install pyarmor

# Register license (required for full obfuscation)
pyarmor reg <your-license-code>

# Build with obfuscation (automatic in build scripts)
python build.py
```

**PyArmor Trial Limitations:**
- Limited number of files
- Watermark in output
- No BCC/RFT mode

**PyArmor Pro ($69/year):**
- Unlimited files
- No watermark
- Full BCC/RFT protection
- Hardware binding
