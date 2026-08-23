"""
AuraTool-Suite — Build & Packaging Script
===========================================
Compiles the entire project into standalone executables for:
  - Windows (x64) via PyInstaller
  - Linux Ubuntu (x64) via PyInstaller
  - Optional PyArmor obfuscation for source code protection
"""

import glob
import os
import platform
import shutil
import subprocess
import sys


APP_NAME = "AuraTool-Suite"
ENTRY_POINT = "main.py"

# All packages to include
PACKAGES = ["core", "modules", "drivers", "ui", "languages"]

# Data directories to bundle
DATA_DIRS = [
    ("core", "core"),
    ("modules", "modules"),
    ("drivers", "drivers"),
    ("ui", "ui"),
]


def clean_build_artifacts():
    """Remove previous build artifacts."""
    print("[*] Cleaning previous build artifacts...")
    for dirname in ["build", "dist", "__pycache__"]:
        if os.path.isdir(dirname):
            shutil.rmtree(dirname)
            print(f"    Removed: {dirname}/")
    for spec_file in glob.glob("*.spec"):
        os.remove(spec_file)
        print(f"    Removed: {spec_file}")
    print("[+] Clean complete.\n")


def ensure_pyinstaller():
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller  # noqa: F401
        print("[+] PyInstaller found.")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[+] PyInstaller installed.\n")


def obfuscate_with_pyarmor():
    """Obfuscate source code using PyArmor if available."""
    print("[*] Checking for PyArmor obfuscation tool...")
    try:
        # Resolve pyarmor CLI: prefer venv script, fall back to PATH
        pyarmor_bin = os.path.join(os.path.dirname(sys.executable), "pyarmor")
        if not os.path.isfile(pyarmor_bin):
            pyarmor_bin = "pyarmor"
        subprocess.check_call([pyarmor_bin, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[*] PyArmor found. Generating obfuscated package...")

        os.makedirs("dist/obfuscated", exist_ok=True)
        pyarmor_cmd = [
            pyarmor_bin,
            "gen",
            "-O", "dist/obfuscated",
            "-r",
            "--mix-str",
            ENTRY_POINT,
        ] + PACKAGES

        subprocess.check_call(pyarmor_cmd)
        print("[+] Code obfuscation completed successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] PyArmor not available — proceeding with standard build (no obfuscation).\n")
        return False


def build_executable():
    """Build standalone executable using PyInstaller."""
    print("=" * 60)
    print(f"  AuraTool-Suite Build — {platform.system()} ({platform.machine()})")
    print("=" * 60)

    clean_build_artifacts()
    ensure_pyinstaller()

    use_obfuscation = obfuscate_with_pyarmor()
    os_type = platform.system()
    separator = ";" if os_type == "Windows" else ":"

    entry = "dist/obfuscated/main.py" if use_obfuscation else ENTRY_POINT

    # Build --add-data arguments
    add_data_args = []
    for src, dst in DATA_DIRS:
        add_data_args.extend([f"--add-data={src}{separator}{dst}"])

    # Platform-specific icon handling
    icon_args = []
    icon_file = "assets/icon.ico" if os_type == "Windows" else "assets/icon.png"
    if os.path.isfile(icon_file):
        icon_args = [f"--icon={icon_file}"]

    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={APP_NAME}",
        "--strip",
    ] + icon_args + add_data_args + [
        "--hidden-import=core",
        "--hidden-import=core.api",
        "--hidden-import=core.security",
        "--hidden-import=core.licensing",
        "--hidden-import=core.license_manager",
        "--hidden-import=modules",
        "--hidden-import=modules.flashing_engine",
        "--hidden-import=modules.biometrics_fix",
        "--hidden-import=modules.localization",
        "--hidden-import=modules.smart_devices",
        "--hidden-import=modules.data_recovery",
        "--hidden-import=modules.account_repair",
        "--hidden-import=modules.aura_ai_assistant",
        "--hidden-import=modules.ultimate_repair",
        "--hidden-import=modules.android",
        "--hidden-import=modules.apple",
        "--hidden-import=modules.download",
        "--hidden-import=drivers",
        "--hidden-import=drivers.driver_manager",
        "--hidden-import=ui",
        "--hidden-import=ui.app",
        entry,
    ]

    print(f"\n[*] Executing PyInstaller for {os_type}:")
    print("    " + " ".join(pyinstaller_args) + "\n")

    try:
        subprocess.check_call(pyinstaller_args)
        print(f"\n[+] Build SUCCESS!")
        print(f"    Output: dist/{APP_NAME}/")

        # Print final size
        dist_path = os.path.join("dist", APP_NAME)
        if os.path.isdir(dist_path):
            total_size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, files in os.walk(dist_path)
                for f in files
            )
            size_mb = total_size / (1024 * 1024)
            print(f"    Total size: {size_mb:.1f} MB")

        print("\n[+] To run:")
        if os_type == "Windows":
            print(f"    dist\\{APP_NAME}\\{APP_NAME}.exe")
        else:
            print(f"    ./dist/{APP_NAME}/{APP_NAME}")

    except subprocess.CalledProcessError as e:
        print(f"\n[-] Build FAILED with error code: {e.returncode}")
        sys.exit(1)


def create_spec_file():
    """Generate a PyInstaller .spec file for advanced customisation."""
    print("[*] Generating .spec file for advanced configuration...")

    datas = []
    for src, dst in DATA_DIRS:
        datas.append(f"('{src}', '{dst}')")

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
# AuraTool-Suite PyInstaller Spec File
# Generated by build.py

a = Analysis(
    ['{ENTRY_POINT}'],
    pathex=[],
    binaries=[],
    datas=[{', '.join(datas)}],
    hiddenimports=[
        'core', 'core.api', 'core.security', 'core.licensing', 'core.license_manager',
        'modules.flashing_engine', 'modules.biometrics_fix',
        'modules.localization', 'modules.smart_devices',
        'modules.data_recovery', 'modules.account_repair',
        'modules.aura_ai_assistant', 'modules.ultimate_repair',
        'modules.android', 'modules.apple', 'modules.download',
        'drivers.driver_manager', 'ui.app',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='{APP_NAME}',
)
"""
    with open(f"{APP_NAME}.spec", "w") as f:
        f.write(spec_content)
    print(f"[+] Spec file written: {APP_NAME}.spec\n")


if __name__ == "__main__":
    create_spec_file()
    build_executable()
