#!/usr/bin/env python3
"""
AuraTool-Suite — Unified Build Script (Linux + Windows)
========================================================
Single command to build both platforms with full verification.

Usage:
    python build_all.py                    # Build both platforms
    python build_all.py --linux-only       # Linux only
    python build_all.py --windows-only     # Windows only (needs Wine or Windows)
    python build_all.py --verify-only      # Verify existing builds
    python build_all.py --clean            # Clean and rebuild all
    python build_all.py --no-verify        # Skip verification tests
"""

import argparse
import glob
import hashlib
import importlib
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "AuraTool-Suite"
APP_VERSION = "3.0.0"
ENTRY_POINT = "main.py"
MODULE_DIRS = ["core", "modules", "drivers", "ui"]
DATA_DIRS = ["languages", "assets"]

# Build locations
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release_output"

# Test modules for verification
TEST_MODULES = [
    "core.config", "core.licensing", "core.license_manager",
    "core.license_server", "core.audit_log", "core.security",
    "modules.localization", "modules.download", "modules.aura_ai_assistant",
    "modules.ultimate_repair", "modules.flashing_engine",
    "modules.biometrics_fix", "modules.smart_devices",
    "modules.data_recovery", "modules.account_repair",
    "modules.chat_rooms", "modules.media_stream", "modules.ecommerce",
    "modules.device_drivers", "auratool_factory", "ui.app",
    "drivers.driver_manager",
]

# ============================================================================
# ANSI Colors
# ============================================================================

class Colors:
    RESET = "\033[0m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"

def c(text, color):
    return f"{color}{text}{Colors.RESET}"

# ============================================================================
# Logging
# ============================================================================

def banner(text):
    width = 60
    print()
    print(c("╔" + "═" * (width - 2) + "╗", Colors.CYAN))
    print(c("║" + text.center(width - 2) + "║", Colors.CYAN))
    print(c("╚" + "═" * (width - 2) + "╝", Colors.CYAN))
    print()

def section(text):
    print()
    print(c(f"  {'─' * 50}", Colors.BLUE))
    print(c(f"  {text}", Colors.BOLD))
    print(c(f"  {'─' * 50}", Colors.BLUE))

def step(msg):
    print(c(f"  ▸ {msg}", Colors.CYAN))

def ok(msg):
    print(c(f"  ✅ {msg}", Colors.GREEN))

def warn(msg):
    print(c(f"  ⚠️  {msg}", Colors.YELLOW))

def err(msg):
    print(c(f"  ❌ {msg}", Colors.RED))

def info(msg):
    print(c(f"  ℹ️  {msg}", Colors.BLUE))

# ============================================================================
# Helpers
# ============================================================================

def run_cmd(cmd, cwd=None, check=True, capture=False):
    """Run a command and optionally capture output."""
    result = subprocess.run(
        cmd, cwd=cwd or PROJECT_ROOT,
        check=check, capture_output=capture, text=True
    )
    return result

def discover_modules():
    """Scan for Python modules to add as hidden imports."""
    hidden = []
    for mod_dir in MODULE_DIRS:
        dir_path = PROJECT_ROOT / mod_dir
        if not dir_path.is_dir():
            continue
        for py_file in sorted(dir_path.glob("*.py")):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue
            hidden.append(f"{mod_dir}.{py_file.stem}")
    for py_file in sorted(PROJECT_ROOT.glob("*.py")):
        if py_file.name in (ENTRY_POINT, "build.py", "build_all.py",
                            "build_windows.py", "generate_icon.py",
                            "setup.py", "pyproject.toml"):
            continue
        if py_file.name.startswith("_"):
            continue
        hidden.append(py_file.stem)
    return hidden

def discover_data_dirs():
    """Find data directories to bundle."""
    data = []
    for d in DATA_DIRS:
        src = PROJECT_ROOT / d
        if src.is_dir() and any(src.iterdir()):
            data.append((str(src), d))
    return data

def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    return hashlib.md5(open(filepath, "rb").read()).hexdigest()

def get_file_size(filepath):
    """Get human-readable file size."""
    size = os.path.getsize(filepath)
    if size >= 1024 * 1024:
        return f"{size / (1024*1024):.1f} MB"
    elif size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"

# ============================================================================
# Git Operations
# ============================================================================

def git_pull():
    """Pull latest changes from remote."""
    section("خطوة 1: سحب أحدث التحديثات")
    try:
        result = run_cmd(["git", "pull", "origin", "main"], capture=True)
        if "Already up to date" in result.stdout:
            info("المستودع محدّث بالفعل")
        else:
            ok(f"تم سحب التحديثات:\n{result.stdout.strip()}")
        return True
    except Exception as e:
        warn(f"فشل سحب التحديثات: {e}")
        return False

# ============================================================================
# Clean
# ============================================================================

def clean_build():
    """Remove all build artifacts."""
    section("خطوة 2: تنظيف البناء القديم")
    for d in [BUILD_DIR, DIST_DIR, RELEASE_DIR]:
        if d.exists():
            shutil.rmtree(d)
            step(f"حذف {d.name}/")
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
        step(f"حذف {spec.name}")
    ok("تم التنظيف بنجاح")

# ============================================================================
# Linux Build
# ============================================================================

def build_linux():
    """Build Linux x86_64 binary."""
    section("خطوة 3: بناء حزمة Linux x86_64")

    start_time = time.time()

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile", "--console", "--strip",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "linux"),
        "--specpath", str(PROJECT_ROOT),
    ]

    # Icon
    png_icon = PROJECT_ROOT / "assets" / "icon.png"
    if png_icon.exists():
        cmd.extend(["--icon", str(png_icon)])

    # Data
    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src}:{dest}"])

    # Hidden imports
    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    step("تشغيل PyInstaller...")
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        err("فشل بناء Linux")
        return False, {}

    binary = DIST_DIR / APP_NAME
    if not binary.exists():
        err(f"الملف التنفيذي غير موجود: {binary}")
        return False, {}

    elapsed = time.time() - start_time
    size = os.path.getsize(binary)
    md5 = get_file_hash(binary)

    ok(f"بناء Linux مكتمل ({elapsed:.1f}s)")
    step(f"الحجم: {size / (1024*1024):.1f} MB | MD5: {md5[:12]}...")

    # Create release package
    release_name = f"{APP_NAME}-v{APP_VERSION}-Linux-x64"
    release_path = RELEASE_DIR / release_name
    RELEASE_DIR.mkdir(exist_ok=True)
    if release_path.exists():
        shutil.rmtree(release_path)
    release_path.mkdir(parents=True)

    shutil.copy2(binary, release_path / APP_NAME)
    os.chmod(release_path / APP_NAME, 0o755)

    # Copy supporting files
    for fname in ["install-desktop.sh", "auratool-suite.desktop"]:
        src = PROJECT_ROOT / "assets" / fname if fname.endswith(".desktop") else release_path.parent.parent / fname if False else PROJECT_ROOT / fname
        # Try release_output first, then project root
        alt_src = release_path.parent / "AuraTool-Suite-v2.0.0-Linux-x64" / fname
        for s in [alt_src, PROJECT_ROOT / fname, PROJECT_ROOT / "assets" / fname]:
            if s.exists():
                shutil.copy2(s, release_path / fname)
                break

    if png_icon.exists():
        shutil.copy2(png_icon, release_path / "icon.png")

    icons_src = PROJECT_ROOT / "assets" / "icons"
    if icons_src.is_dir():
        shutil.copytree(icons_src, release_path / "icons", dirs_exist_ok=True)

    # Create tar.gz
    step("إنشاء الأرشيف...")
    archive_path = RELEASE_DIR / f"{release_name}.tar.gz"
    run_cmd(["tar", "czf", str(archive_path), "-C", str(RELEASE_DIR), release_name])

    # Create ZIP
    zip_path = RELEASE_DIR / f"{release_name}.zip"
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", RELEASE_DIR, release_name)

    return True, {
        "binary": str(binary),
        "size": size / (1024*1024),
        "md5": md5,
        "elapsed": elapsed,
        "release": str(release_path),
        "tar.gz": str(archive_path),
        "zip": str(zip_path),
    }

# ============================================================================
# Windows Build
# ============================================================================

def build_windows():
    """Build Windows x64 package."""
    section("خطوة 4: بناء حزمة Windows x64")

    start_time = time.time()

    # Check for Wine
    wine = shutil.which("wine64") or shutil.which("wine")

    if wine:
        step("تم العثور على Wine — البناء عبر Wine...")
        return _build_windows_wine(wine)
    elif platform.system() == "Windows":
        step("نظام Windows — البناء الأصلي...")
        return _build_windows_native()
    else:
        warn("Wine غير مثبت — تخطي بناء Windows")
        warn("للتثبيت: sudo apt install wine64 wine32")
        warn("أو استخدم: ./build_windows_wine.sh")
        return False, {}

def _build_windows_native():
    """Build on native Windows."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onedir", "--noconsole",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR / "windows"),
        "--workpath", str(BUILD_DIR / "windows"),
        "--specpath", str(PROJECT_ROOT),
    ]

    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src};{dest}"])

    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    step("تشغيل PyInstaller (Windows)...")
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        err("فشل بناء Windows")
        return False, {}

    return _package_windows()

def _build_windows_wine(wine):
    """Build via Wine cross-compilation."""
    # Generate Windows spec
    spec_content = _generate_windows_spec()
    spec_path = PROJECT_ROOT / "auratool-suite-windows.spec"
    spec_path.write_text(spec_content)

    # Convert paths for Wine
    wine_root = str(PROJECT_ROOT).replace("/mnt/", "Z:\\\\").replace("/", "\\\\\\\\")

    cmd = [
        wine, "python", "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onedir", "--noconsole",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR / "windows"),
        "--workpath", str(BUILD_DIR / "windows"),
        "--specpath", str(PROJECT_ROOT),
    ]

    ico_icon = PROJECT_ROOT / "assets" / "icon.ico"
    if ico_icon.exists():
        cmd.extend(["--icon", str(ico_icon)])

    for src, dest in discover_data_dirs():
        cmd.extend(["--add-data", f"{src};{dest}"])

    for mod in discover_modules():
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT_ROOT / ENTRY_POINT))

    step("تشغيل PyInstaller عبر Wine...")
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        err("فشل بناء Windows عبر Wine")
        return False, {}

    return _package_windows()

def _package_windows():
    """Package Windows build."""
    win_dist = DIST_DIR / "windows" / APP_NAME
    if not win_dist.exists():
        # Try alternate path
        win_dist = DIST_DIR / APP_NAME
        if not win_dist.exists():
            err("مجلد بناء Windows غير موجود")
            return False, {}

    elapsed = time.time() - time.time()  # Placeholder

    release_name = f"{APP_NAME}-v{APP_VERSION}-Windows-x64"
    release_path = RELEASE_DIR / release_name
    RELEASE_DIR.mkdir(exist_ok=True)
    if release_path.exists():
        shutil.rmtree(release_path)

    shutil.copytree(win_dist, release_path)

    # Create README
    readme = release_path / "README.txt"
    readme.write_text(f"""{APP_NAME} v{APP_VERSION} — Windows Portable Edition
{'='*50}

To run: Double-click AuraTool-Suite.exe
To install: Copy the entire folder to your preferred location.

Requirements:
  - Windows 10/11 x64
  - USB device drivers for target devices

License: See license agreement included with the application.
""")

    # Create ZIP
    step("إنشاء ZIP...")
    zip_path = RELEASE_DIR / f"{release_name}.zip"
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", RELEASE_DIR, release_name)

    exe_path = release_path / f"{APP_NAME}.exe"
    size = os.path.getsize(exe_path) / (1024*1024) if exe_path.exists() else 0

    ok(f"بناء Windows مكتمل")
    step(f"الحجم: {size:.1f} MB")

    return True, {
        "size": size,
        "release": str(release_path),
        "zip": str(zip_path),
    }

def _generate_windows_spec():
    """Generate Windows PyInstaller spec file."""
    hidden = discover_modules()
    data_entries = discover_data_dirs()
    hidden_str = ",\n        ".join(f'"{m}"' for m in hidden)
    data_str = ",\n        ".join(f'(r"{s}", r"{d}")' for s, d in data_entries)
    entry = str(PROJECT_ROOT / ENTRY_POINT)

    return textwrap.dedent(f"""\
# -*- mode: python ; coding: utf-8 -*-
# Auto-generated Windows spec for {APP_NAME}
import os, sys

block_cipher = None

a = Analysis(
    [r'{entry}'],
    pathex=[r'{PROJECT_ROOT}'],
    binaries=[],
    datas=[{data_str}] if '{data_str}' else [],
    hiddenimports=[{hidden_str}],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[],
    excludes=['tkinter.test', 'unittest', 'test', 'numpy', 'pandas',
              'scipy', 'matplotlib', 'notebook', 'ipython', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], a.binaries, a.zipfiles, a.datas, [],
    name='{APP_NAME}', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
    icon=r'{PROJECT_ROOT / "assets" / "icon.ico"}' if os.path.exists(r'{PROJECT_ROOT / "assets" / "icon.ico"}') else None,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False,
    upx=True, upx_exclude=[], name='{APP_NAME}',
)
""")

# ============================================================================
# Verification
# ============================================================================

def verify_builds():
    """Run comprehensive verification tests."""
    section("خطوة 5: اختبارات التحقق")
    results = {"passed": 0, "failed": 0, "details": []}

    # Test 1: Unit tests
    step("اختبارات الوحدة...")
    result = run_cmd(
        [sys.executable, "-m", "pytest", "tests/", "--tb=no", "-q"],
        capture=True, check=False
    )
    if result.returncode == 0:
        summary = result.stdout.strip().split("\n")[-1]
        ok(f"Unit Tests: {summary}")
        results["passed"] += 1
        results["details"].append(("Unit Tests", "✅", summary))
    else:
        err("Unit Tests FAILED")
        results["failed"] += 1
        results["details"].append(("Unit Tests", "❌", "Failed"))

    # Test 2: Module imports
    step("استيراد الوحدات...")
    import_passed = 0
    for mod in TEST_MODULES:
        try:
            importlib.import_module(mod)
            import_passed += 1
        except Exception as e:
            err(f"  {mod}: {e}")

    ok(f"Module Imports: {import_passed}/{len(TEST_MODULES)}")
    if import_passed == len(TEST_MODULES):
        results["passed"] += 1
        results["details"].append(("Module Imports", "✅", f"{import_passed}/{len(TEST_MODULES)}"))
    else:
        results["failed"] += 1
        results["details"].append(("Module Imports", "❌", f"{import_passed}/{len(TEST_MODULES)}"))

    # Test 3: Linux binary
    linux_bin = DIST_DIR / APP_NAME
    if linux_bin.exists():
        step("الملف التنفيذي Linux...")
        size = os.path.getsize(linux_bin) / (1024*1024)
        md5 = get_file_hash(linux_bin)
        ok(f"Linux Binary: {size:.1f} MB | MD5: {md5[:12]}...")
        results["passed"] += 1
        results["details"].append(("Linux Binary", "✅", f"{size:.1f} MB"))
    else:
        warn("Linux binary not found, skipping")

    # Test 4: Package integrity
    step("سلامة الحزمة...")
    release_name = f"{APP_NAME}-v{APP_VERSION}-Linux-x64"
    release_path = RELEASE_DIR / release_name
    required_files = [APP_NAME, "auratool-suite.desktop", "icon.png"]
    pkg_ok = all((release_path / f).exists() for f in required_files)

    if pkg_ok:
        ok("Package Integrity: All files present")
        results["passed"] += 1
        results["details"].append(("Package Integrity", "✅", "All files"))
    else:
        err("Package Integrity: Missing files")
        results["failed"] += 1
        results["details"].append(("Package Integrity", "❌", "Missing files"))

    # Test 5: Archives
    step("الأرشيفات...")
    tar_path = RELEASE_DIR / f"{release_name}.tar.gz"
    zip_path = RELEASE_DIR / f"{release_name}.zip"
    archives_ok = tar_path.exists() and zip_path.exists()

    if archives_ok:
        tar_size = os.path.getsize(tar_path) / (1024*1024)
        zip_size = os.path.getsize(zip_path) / (1024*1024)
        ok(f"Archives: tar.gz={tar_size:.1f}MB, zip={zip_size:.1f}MB")
        results["passed"] += 1
        results["details"].append(("Archives", "✅", f"tar.gz+zip"))
    else:
        err("Archives: Missing")
        results["failed"] += 1
        results["details"].append(("Archives", "❌", "Missing"))

    return results

# ============================================================================
# Summary
# ============================================================================

def print_summary(linux_result, windows_result, verify_result, total_time):
    """Print final build summary."""
    banner("ملخص البناء النهائي")

    # Build status
    print(c("  ╔═══════════════════════════════════════════════════╗", Colors.CYAN))
    print(c("  ║  المنصة           الحالة         الحجم           ║", Colors.CYAN))
    print(c("  ╠═══════════════════════════════════════════════════╣", Colors.CYAN))

    linux_ok, linux_info = linux_result
    if linux_ok:
        print(c(f"  ║  🐧 Linux        ✅ Success     {linux_info.get('size', 0):.1f} MB          ║", Colors.CYAN))
    else:
        print(c(f"  ║  🐧 Linux        ❌ Failed      -               ║", Colors.CYAN))

    win_ok, win_info = windows_result
    if win_ok:
        print(c(f"  ║  🪟 Windows      ✅ Success     {win_info.get('size', 0):.1f} MB          ║", Colors.CYAN))
    else:
        print(c(f"  ║  🪟 Windows      ⏭️  Skipped    -               ║", Colors.CYAN))

    print(c("  ╚═══════════════════════════════════════════════════╝", Colors.CYAN))

    # Verification results
    if verify_result:
        print()
        print(c("  ╔═══════════════════════════════════════════════════╗", Colors.GREEN))
        print(c("  ║  اختبارات التحقق                                ║", Colors.GREEN))
        print(c("  ╠═══════════════════════════════════════════════════╣", Colors.GREEN))
        for name, status, detail in verify_result["details"]:
            print(c(f"  ║  {status} {name:<25} {detail:<20}  ║", Colors.GREEN))
        print(c("  ╠═══════════════════════════════════════════════════╣", Colors.GREEN))
        total = verify_result["passed"] + verify_result["failed"]
        print(c(f"  ║  المجموع: {verify_result['passed']}/{total} نجح                                  ║", Colors.GREEN))
        print(c("  ╚═══════════════════════════════════════════════════╝", Colors.GREEN))

    # Release files
    print()
    step("ملفات الإصدار:")
    for f in sorted(RELEASE_DIR.iterdir()):
        if f.is_file():
            print(f"    📦 {f.name} ({get_file_size(f)})")

    # Total time
    print()
    step(f"وقت البناء الإجمالي: {total_time:.1f} ثانية")
    print()

# ============================================================================
# Main
# ============================================================================

def _update_version(version):
    global APP_VERSION
    APP_VERSION = version


def main():
    parser = argparse.ArgumentParser(
        description=f"Unified build script for {APP_NAME}"
    )
    parser.add_argument("--linux-only", action="store_true",
                        help="Build Linux only")
    parser.add_argument("--windows-only", action="store_true",
                        help="Build Windows only")
    parser.add_argument("--verify-only", action="store_true",
                        help="Run verification only")
    parser.add_argument("--clean", action="store_true",
                        help="Clean and rebuild")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip verification")
    parser.add_argument("--version", default=APP_VERSION,
                        help=f"Version (default: {APP_VERSION})")
    args = parser.parse_args()

    _update_version(args.version)

    start_time = time.time()

    banner(f"{APP_NAME} v{APP_VERSION} — Unified Build System")

    # Pull updates
    git_pull()

    # Clean if requested
    if args.clean:
        clean_build()

    # Verify only
    if args.verify_only:
        verify_builds()
        return

    # Build
    do_linux = not args.windows_only
    do_windows = not args.linux_only

    linux_result = (False, {})
    windows_result = (False, {})

    if do_linux:
        linux_result = build_linux()

    if do_windows:
        windows_result = build_windows()

    # Verify
    verify_result = None
    if not args.no_verify:
        verify_result = verify_builds()

    # Summary
    total_time = time.time() - start_time
    print_summary(linux_result, windows_result, verify_result, total_time)

    # Exit code
    all_ok = linux_result[0]
    if verify_result and verify_result["failed"] > 0:
        all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
