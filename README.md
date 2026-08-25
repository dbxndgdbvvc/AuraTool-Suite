# AuraTool-Suite

![Build & Release](https://github.com/AuraTool-Suite/AuraTool-Suite/actions/workflows/build.yml/badge.svg)
![License](https://img.shields.io/badge/license-proprietary-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-brightgreen)
![Python](https://img.shields.io/badge/python-3.10+-yellow)

> **Universal Mobile Device Maintenance & Repair Framework**  
> Firmware flashing, account bypass, system recovery, and workshop management — all in one tool.

---

## Features

| Module | Description |
|--------|-------------|
| **Flashing Engine** | Universal firmware flashing for Samsung, Qualcomm EDL, MediaTek BROM |
| **Account Repair** | FRP & cloud account bypass algorithms |
| **Biometrics Fix** | Fingerprint and face unlock restoration |
| **Data Recovery** | Partition backup and restoration |
| **AI Assistant** | Aura AI diagnostic and repair guidance |
| **Ultimate Repair** | Bootloop, black screen, virus eradication |
| **Smart Devices** | Phone, tablet, smartwatch, smart glasses support |
| **Workshop Manager** | Tickets, clients, inventory, diagnostics |
| **Factory REST API** | HTTP API with API key auth, audit logging, TLS |
| **Chat Rooms** | Live technician chat |
| **Media Streaming** | Device screen mirroring |
| **E-Commerce** | Parts store integration |

## Quick Start

### Download

Grab the latest release for your platform from [Releases](https://github.com/AuraTool-Suite/AuraTool-Suite/releases).

| Platform | File | Install |
|----------|------|---------|
| 🐧 Linux x64 | `AuraTool-Suite-v*-Linux-x64.tar.gz` | Extract → `./install-desktop.sh` |
| 🪟 Windows x64 | `AuraTool-Suite-v*-Windows-x64.zip` | Extract → double-click `.exe` |

### Linux Desktop Integration

```bash
tar xzf AuraTool-Suite-v2.0.0-Linux-x64.tar.gz
cd AuraTool-Suite-v2.0.0-Linux-x64
./install-desktop.sh
```

This installs the binary, icons, and desktop entry to your system.  
Requires `sudo` for `/usr/local`, or installs to `~/.local` without it.

### Windows

Extract the `.zip` archive and run `AuraTool-Suite.exe`.  
No installation required — fully portable.

## Building from Source

### Prerequisites

```bash
pip install pyinstaller pillow
```

For Windows cross-compilation from Linux:
```bash
sudo apt install wine64 wine32
wine python-3.12.x-amd64.exe /quiet InstallAllUsers=1
wine python -m pip install pyinstaller
```

### Build Commands

```bash
# Both platforms (Linux + Windows via Wine)
python build.py

# Linux only
python build.py --linux-only

# Windows only
python build.py --windows-only

# Clean build artifacts
python build.py --clean-only
```

Output goes to `release_output/`:

```
release_output/
├── AuraTool-Suite-v2.0.0-Linux-x64.tar.gz    ← Linux archive
└── AuraTool-Suite-v2.0.0-Windows-x64.zip      ← Windows archive
```

See [CROSS_BUILD.md](CROSS_BUILD.md) for detailed cross-compilation instructions.

## Project Structure

```
├── main.py                    ← Application entry point
├── build.py                   ← Dual-platform build script
├── build_windows.py           ← Windows-specific build script
├── generate_icon.py           ← Icon generator (Pillow)
├── core/                      ← Core subsystems
│   ├── api.py                 ← Cloud sync & USB/EDL/BROM protocols
│   ├── licensing.py           ← License management
│   ├── license_manager.py     ← HWID-based license enforcement
│   ├── license_server.py      ← License activation server
│   ├── security.py            ← Security manager
│   ├── factory_api.py         ← REST API with auth & audit
│   ├── audit_log.py           ← API audit trail
│   ├── tls_utils.py           ← TLS/SSL utilities
│   └── api_key_cli.py         ← API key management CLI
├── modules/                   ← Feature modules
│   ├── flashing_engine.py     ← Firmware flashing
│   ├── aura_ai_assistant.py   ← AI diagnostics
│   ├── ultimate_repair.py     ← System repair
│   ├── android.py             ← Android device support
│   ├── apple.py               ← Apple device support
│   └── ...                    ← (15 modules total)
├── drivers/                   ← Device driver infrastructure
│   └── driver_manager.py
├── ui/                        ← Desktop GUI
│   └── app.py
├── assets/                    ← Icons and resources
│   ├── icon.ico               ← Windows ICO (6 sizes)
│   ├── icon.png               ← High-res PNG (512×512)
│   ├── icons/                 ← Linux icon theme (9 sizes)
│   └── auratool-suite.desktop ← Desktop entry
├── tests/                     ← Unit & integration tests
├── languages/                 ← Localization files
├── .github/workflows/
│   └── build.yml              ← CI/CD pipeline
└── release_output/            ← Build output (git-ignored)
```

## CI/CD Pipeline

Automated builds run on every push and PR via GitHub Actions:

| Job | Runner | Description |
|-----|--------|-------------|
| 🧪 **Tests** | Ubuntu | Unit tests with pytest |
| 🐧 **Linux x64** | Ubuntu | Native Linux binary + portable archive |
| 🪟 **Windows x64** | Windows | Native Windows `.exe` + portable archive |
| 🚀 **Release** | Ubuntu | Creates GitHub Release on version tags |

### Creating a Release

```bash
git tag v2.1.0
git push origin v2.1.0
```

This triggers the full pipeline: test → build → release with both binaries attached.

## API Server

Start the Factory REST API:

```bash
# With authentication (auto-generates bootstrap key)
python -m core.factory_api

# Without authentication (local dev)
python -m core.factory_api --no-auth

# With TLS
python -m core.factory_api --auto-ssl
```

API key management:
```bash
python -m core.api_key_cli list
python -m core.api_key_cli generate --role admin --label "production"
python -m core.api_key_cli stats
```

## License

AuraTool-Suite requires a valid license key for operation.  
Contact your distributor for license activation.

## Support

For technical support or feature requests, contact your distributor or open an issue on GitHub.

---

*Built with Python 3.10+ • PyInstaller • GitHub Actions CI/CD*
