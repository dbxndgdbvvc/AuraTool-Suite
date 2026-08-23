"""
AuraTool-Suite — Windows Build Script
=======================================
Run this on Windows with Python + PyInstaller installed.
Produces a standalone .exe for Windows x64.

Usage:
    python build_windows.py

Requirements (Windows):
    pip install pyinstaller pyarmor
"""

import glob
import os
import platform
import shutil
import subprocess
import sys


APP_NAME = "AuraTool-Suite"
ENTRY_POINT = "main.py"

PACKAGES = ["core", "modules", "drivers", "ui", "languages"]

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
    for spec_file in glob.glob("*.spec"):
        os.remove(spec_file)
        print(f"    Removed: {spec_file}")
    print("[+] Clean complete.\n")


def obfuscate_with_pyarmor():
    print("[*] Checking for PyArmor...")
    pyarmor_bin = "pyarmor"
    try:
        subprocess.check_call([pyarmor_bin, "--version"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[*] PyArmor found. Obfuscating source code...")

        os.makedirs("dist/obfuscated", exist_ok=True)
        cmd = [
            pyarmor_bin, "gen",
            "-O", "dist/obfuscated",
            "-r", "--mix-str",
            ENTRY_POINT,
        ] + PACKAGES

        subprocess.check_call(cmd)
        print("[+] Obfuscation complete.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[!] PyArmor not available or license exhausted: {e}")
        print("[!] Proceeding with standard build (no obfuscation).\n")
        return False


def build_executable():
    print("=" * 60)
    print(f"  AuraTool-Suite Windows Build — {platform.machine()}")
    print("=" * 60)

    clean_build_artifacts()

    use_obfuscation = obfuscate_with_pyarmor()
    separator = ";"  # Windows path separator
    entry = "dist/obfuscated/main.py" if use_obfuscation else ENTRY_POINT

    # Build --add-data arguments
    add_data_args = []
    for src, dst in DATA_DIRS:
        add_data_args.append(f"--add-data={src}{separator}{dst}")

    # Icon
    icon_args = []
    if os.path.isfile("assets/icon.ico"):
        icon_args = ["--icon=assets/icon.ico"]

    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={APP_NAME}",
    ] + icon_args + add_data_args + [
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
        "--hidden-import=modules.android",
        "--hidden-import=modules.apple",
        "--hidden-import=modules.download",
        "--hidden-import=drivers",
        "--hidden-import=drivers.driver_manager",
        "--hidden-import=ui",
        "--hidden-import=ui.app",
        entry,
    ]

    print(f"\n[*] Executing PyInstaller for Windows:")
    print("    " + " ".join(pyinstaller_args) + "\n")

    try:
        subprocess.check_call(pyinstaller_args)
        print(f"\n[+] Build SUCCESS!")
        print(f"    Output: dist\\{APP_NAME}\\")
        print(f"    Executable: dist\\{APP_NAME}\\{APP_NAME}.exe")

        # Size report
        dist_path = os.path.join("dist", APP_NAME)
        if os.path.isdir(dist_path):
            total_size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, files in os.walk(dist_path)
                for f in files
            )
            print(f"    Total size: {total_size / (1024*1024):.1f} MB")

    except subprocess.CalledProcessError as e:
        print(f"\n[-] Build FAILED with error code: {e.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    if platform.system() != "Windows":
        print("[!] This script is designed for Windows.")
        print("[!] For Linux builds, use: python build.py")
        print("[!] For cross-compilation, use the GitHub Actions workflow.")
        sys.exit(1)
    build_executable()
