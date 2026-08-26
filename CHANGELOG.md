# Changelog

All notable changes to AuraTool-Suite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2.1.0] — 2026-08-26

### Added
- **Device locale methods** in `LocalizationManager`:
  - `apply_locale_to_device()` — push language config to device via ADB/fastboot
  - `configure_csc()` — set Country Specific Code for regional features
  - `unhide_system_languages()` — unlock carrier/OEM-restricted languages
- **Unit tests** for all 3 new localization methods (33 tests in `test_localization.py`)
- Improved error handling across core modules — replaced silent `pass` blocks with proper logging

### Fixed
- `test_key_activation_updates_tier` — clean up stale temp directory before each run
- `test_account_diagnostics_then_repair` — accept both "NORMAL" and "LOCKED" sync status

### Changed
- `core/license_manager.py` — HWID collection now logs debug messages on fallback paths
- `core/licensing.py` — license state save failures are now logged as warnings
- `core/audit_log.py` — log read/rotation failures are now logged as warnings
- `core/license_server.py` — key save failures are now logged as warnings
- `ui/app.py` — icon loading failures are now logged as debug messages

---

## [2.0.0] — 2026-08-25

### Added
- **Factory REST API** with API key authentication and audit logging (`core/factory_api.py`)
- **TLS/SSL utilities** for HTTPS server deployment (`core/tls_utils.py`)
- **API key management CLI** for generating and managing API keys (`core/api_key_cli.py`)
- **Audit logging** for all API requests (`core/audit_log.py`)
- **License server** with online activation, validation, and deactivation (`core/license_server.py`)
- **HWID-based license enforcement** with anti-clock-rollback protection
- **PyInstaller build system** for Linux and Windows desktop apps
- **Wine cross-compilation** support for building Windows binary on Linux
- **GitHub Actions CI/CD** pipeline with automated testing and release creation
- **Linux desktop integration** installer with icons and `.desktop` entry
- **UPX compression** for smaller release binaries

### Changed
- Full dual-platform build pipeline (Linux + Windows via Wine)
- Expanded PyInstaller excludes for smaller binary size

---

## [1.0.0] — 2026-08-22

### Added
- **Aura AI Assistant** — voice/text command processing, device diagnosis, log analysis
- **Ultimate Repair Module** — bootloop, black screen, virus eradication, memory corruption
- **Flashing Engine** — universal firmware flashing (Samsung, Qualcomm EDL, MediaTek BROM)
- **Account Repair** — FRP bypass, cloud sync repair, EFS backup/restore
- **Biometrics Fix** — fingerprint and face unlock restoration
- **Smart Device Manager** — phone, tablet, smartwatch, smart glasses, AR/VR support
- **Data Recovery** — partition backup and restoration
- **Android Device Manager** — Samsung, Xiaomi, Huawei, generic Android support
- **Apple Device Manager** — iPhone, iPad, Apple Watch, DFU restore, activation lock check
- **Download Manager** — firmware download with integrity verification
- **Device Driver Manager** — driver infrastructure
- **Chat Rooms** — live technician chat
- **Media Streaming** — device screen mirroring
- **E-Commerce** — parts store integration
- **Localization System** — Arabic RTL support with reshaping, English, Spanish, French, German, Russian, Chinese, Japanese, Turkish, Hindi
- **License Manager** — 15-day trial, 6-month professional, 1-year VIP tiers
- **Desktop GUI** — tkinter-based interface with multi-tab layout
- **38 end-to-end integration tests**
- **127 unit tests** across all modules
- Workshop & factory management system with PDF/CSV export

---

## [Unreleased]

### Planned
- Multi-brand device support expansion
- Real-time device monitoring
- Cloud-based firmware repository
- Plugin system for third-party extensions
- Mobile companion app
