import os
import sys
import shutil
import platform
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release_output")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")

HIDDEN_IMPORTS = [
    "core.factory_api",
    "core.licensing",
    "core.security",
    "drivers.driver_manager",
    "modules.account_repair",
    "modules.android",
    "modules.apple",
    "modules.aura_ai_assistant",
    "modules.biometrics_fix",
    "modules.chat_rooms",
    "modules.data_recovery",
    "modules.download",
    "modules.ecommerce",
    "modules.factory_export",
    "modules.flashing_engine",
    "modules.localization",
    "modules.media_stream",
    "modules.smart_devices",
    "modules.ultimate_repair",
    "auratool_factory"
]

def clean_build_artifacts():
    """Removes temporary build directories and spec files to maintain a clean workspace."""
    print("[*] Cleaning up build artifacts and temporary files...")
    dirs_to_remove = [BUILD_DIR, DIST_DIR]
    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"    Removed directory: {d}")

    for file in os.listdir(PROJECT_ROOT):
        if file.endswith(".spec"):
            spec_path = os.path.join(PROJECT_ROOT, file)
            try:
                os.remove(spec_path)
                print(f"    Removed spec file: {spec_path}")
            except OSError:
                pass

def ensure_pyinstaller():
    """Ensures PyInstaller is installed in the current Python environment."""
    try:
        import PyInstaller
        print("[*] Native PyInstaller is installed and ready.")
    except ImportError:
        print("[!] PyInstaller not found in Python environment. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def find_wine_python():
    """Locates Wine and Windows Python executable on Linux/Ubuntu system."""
    wine_path = shutil.which("wine")
    if not wine_path:
        return None

    possible_paths = [
        os.path.expanduser("~/.wine/drive_c/Python310/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Python311/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Python39/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Program Files/Python310/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Program Files/Python311/python.exe"),
    ]

    for py_path in possible_paths:
        if os.path.exists(py_path):
            return py_path

    try:
        res = subprocess.run(["wine", "python", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            return "python"
    except Exception:
        pass

    return None

def get_entry_point():
    """Determines the application entry point script."""
    entry_point = os.path.join(PROJECT_ROOT, "ui", "app.py")
    if not os.path.exists(entry_point):
        entry_point = os.path.join(PROJECT_ROOT, "auratool_factory.py")
    return entry_point

def build_linux_native(entry_point):
    """Builds single-file native Linux binary."""
    print("\n==================================================")
    print("[*] Building Native Linux Binary (--onefile)...")
    print("==================================================")
    ensure_pyinstaller()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name=AuraTool",
        "--distpath=" + RELEASE_DIR,
        "--workpath=" + BUILD_DIR,
        "--clean",
        "--noconfirm"
    ]
    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])
    cmd.append(entry_point)

    print(f"[*] Executing command: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"[SUCCESS] Linux Binary created: {os.path.join(RELEASE_DIR, 'AuraTool')}")
        return True
    else:
        print("[ERROR] Linux build failed.")
        return False

def build_windows_exe(entry_point):
    """Builds single-file Windows executable (.exe) via Wine or native environment."""
    print("\n==================================================")
    print("[*] Building Windows Executable (.exe)...")
    print("==================================================")

    current_os = platform.system().lower()

    if current_os == "windows":
        ensure_pyinstaller()
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--name=AuraTool.exe",
            "--distpath=" + RELEASE_DIR,
            "--workpath=" + BUILD_DIR,
            "--clean",
            "--noconfirm"
        ]
    else:
        wine_python = find_wine_python()
        if not wine_python:
            print("[!] Wine / Windows Python environment not detected on Linux.")
            print("    To cross-compile Windows .exe on Ubuntu, install Wine & Windows Python:")
            print("    sudo apt install wine64 && wine msiexec /i python- installer.msi")
            return False

        print(f"[*] Found Wine Python: {wine_python}")
        cmd = [
            "wine", wine_python, "-m", "PyInstaller",
            "--onefile",
            "--name=AuraTool.exe",
            "--distpath=" + RELEASE_DIR,
            "--workpath=" + BUILD_DIR,
            "--clean",
            "--noconfirm"
        ]

    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])
    cmd.append(entry_point)

    print(f"[*] Executing command: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"[SUCCESS] Windows Executable created: {os.path.join(RELEASE_DIR, 'AuraTool.exe')}")
        return True
    else:
        print("[ERROR] Windows build failed.")
        return False

def build_all():
    """Main build workflow for dual-platform release generation."""
    clean_build_artifacts()
    os.makedirs(RELEASE_DIR, exist_ok=True)

    entry_point = get_entry_point()
    print(f"[*] Target Release Folder: {RELEASE_DIR}")
    print(f"[*] Application Entry Point: {entry_point}")

    linux_status = build_linux_native(entry_point)
    win_status = build_windows_exe(entry_point)

    clean_build_artifacts()

    print("\n==================================================")
    print("BUILD SUMMARY & RELEASE STATUS")
    print("==================================================")
    print(f"Output Directory: {RELEASE_DIR}")
    print(f"Linux Binary  (AuraTool)    : {'SUCCESS' if linux_status else 'SKIPPED/FAILED'}")
    print(f"Windows Binary (AuraTool.exe): {'SUCCESS' if win_status else 'SKIPPED/FAILED'}")
    print("==================================================")

if __name__ == "__main__":
    build_all()
