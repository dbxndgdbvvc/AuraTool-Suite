"""
AuraTool-Suite — Build & Packaging Script
===========================================
Compiles the entire project into standalone executable desktop apps:
  - Windows (x64) via PyInstaller (.exe)
  - Linux Ubuntu (x64) via PyInstaller
Outputs a ready-to-use desktop application directory for direct execution.
"""

import os
import platform
import shutil
import subprocess
import sys

APP_NAME = "AuraTool-Suite"
ENTRY_POINT = "main.py"

DATA_DIRS = [
    ("core", "core"),
    ("modules", "modules"),
    ("drivers", "drivers"),
    ("ui", "ui"),
]


def clean_build_artifacts():
    print("[*] Cleaning previous build artifacts...")
    for dirname in ["build", "dist", "__pycache__"]:
        if os.path.isdir(dirname):
            shutil.rmtree(dirname)
            print(f"    Removed: {dirname}/")
    print("[+] Clean complete.\n")


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        print("[+] PyInstaller found.")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[+] PyInstaller installed.\n")


def build_executable():
    print("=" * 60)
    print(f"  AuraTool-Suite Build — {platform.system()} ({platform.machine()})")
    print("=" * 60)

    clean_build_artifacts()
    ensure_pyinstaller()

    os_type = platform.system()
    separator = ";" if os_type == "Windows" else ":"

    add_data_args = []
    for src, dst in DATA_DIRS:
        add_data_args.extend([f"--add-data={src}{separator}{dst}"])

    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={APP_NAME}",
        "--clean",
    ] + add_data_args + [
        "--hidden-import=core",
        "--hidden-import=core.api",
        "--hidden-import=core.security",
        "--hidden-import=core.licensing",
        "--hidden-import=modules",
        "--hidden-import=modules.flashing_engine",
        "--hidden-import=modules.biometrics_fix",
        "--hidden-import=modules.localization",
        "--hidden-import=modules.smart_devices",
        "--hidden-import=modules.data_recovery",
        "--hidden-import=modules.account_repair",
        "--hidden-import=modules.aura_ai_assistant",
        "--hidden-import=modules.ultimate_repair",
        "--hidden-import=modules.chat_rooms",
        "--hidden-import=modules.media_stream",
        "--hidden-import=modules.ecommerce",
        "--hidden-import=drivers",
        "--hidden-import=drivers.driver_manager",
        "--hidden-import=ui",
        "--hidden-import=ui.app",
        ENTRY_POINT,
    ]

    print(f"\n[*] Executing PyInstaller command for {os_type}:")
    print("    " + " ".join(pyinstaller_args) + "\n")

    try:
        subprocess.check_call(pyinstaller_args)
        print(f"\n[+] Build SUCCESS!")
        print(f"    Output directory: dist/{APP_NAME}/")

        dist_path = os.path.join("dist", APP_NAME)
        if os.path.isdir(dist_path):
            total_size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, files in os.walk(dist_path)
                for f in files
            )
            size_mb = total_size / (1024 * 1024)
            print(f"    Application bundle size: {size_mb:.1f} MB")

        print("\n[+] Direct launcher path:")
        if os_type == "Windows":
            print(f"    dist\\{APP_NAME}\\{APP_NAME}.exe")
        else:
            print(f"    ./dist/{APP_NAME}/{APP_NAME}")

    except subprocess.CalledProcessError as e:
        print(f"\n[-] Build FAILED with error code: {e.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
