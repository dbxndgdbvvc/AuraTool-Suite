import os
import platform
import subprocess
import sys

def obfuscate_with_pyarmor():
    """Obfuscates source code using PyArmor if installed."""
    print("[*] Checking for PyArmor obfuscation tool...")
    try:
        subprocess.check_call(["pyarmor", "--version"])
        print("[*] PyArmor found. Generating obfuscated package...")
        pyarmor_cmd = ["pyarmor", "gen", "-O", "dist/obfuscated", "main.py", "core", "modules", "drivers", "ui"]
        subprocess.check_call(pyarmor_cmd)
        print("[+] Code obfuscation completed successfully.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] PyArmor not available or obfuscation skipped. Proceeding with standard build...")
        return False

def build_executable():
    """Builds a standalone executable using PyInstaller."""
    print("[*] Starting AuraTool-Suite compilation process...")
    
    use_obfuscation = obfuscate_with_pyarmor()
    os_type = platform.system()
    app_name = "AuraTool-Suite"
    entry_point = "dist/obfuscated/main.py" if use_obfuscation else "main.py"

    pyinstaller_args = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={app_name}",
        "--add-data=core:core",
        "--add-data=modules:modules",
        "--add-data=drivers:drivers",
        "--add-data=ui:ui",
        entry_point
    ]

    # Adjust path separator for Windows vs Posix data bindings
    if os_type == "Windows":
        pyinstaller_args[5] = "--add-data=core;core"
        pyinstaller_args[6] = "--add-data=modules;modules"
        pyinstaller_args[7] = "--add-data=drivers;drivers"
        pyinstaller_args[8] = "--add-data=ui;ui"

    print(f"[*] Executing PyInstaller command for {os_type}:")
    print(" ".join(pyinstaller_args))

    try:
        subprocess.check_call(pyinstaller_args)
        print(f"\n[+] Build successfully completed! Binary output located in dist/{app_name}/")
    except subprocess.CalledProcessError as e:
        print(f"\n[-] Build failed with error code: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
