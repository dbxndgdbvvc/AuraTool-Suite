import os
import sys
import shutil
import platform
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release")
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
            print(f"    Removed: {d}")

    for file in os.listdir(PROJECT_ROOT):
        if file.endswith(".spec"):
            spec_path = os.path.join(PROJECT_ROOT, file)
            try:
                os.remove(spec_path)
                print(f"    Removed: {spec_path}")
            except OSError:
                pass

def ensure_pyinstaller():
    """Ensures PyInstaller is installed in the current Python environment."""
    try:
        import PyInstaller
        print("[*] PyInstaller is installed and available.")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def find_wine_python():
    """Checks if Wine and Windows Python are installed on Linux for cross-compiling .exe files."""
    wine_path = shutil.which("wine")
    if not wine_path:
        return None

    # Check common Wine Python locations
    possible_paths = [
        os.path.expanduser("~/.wine/drive_c/Python310/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Python311/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Program Files/Python310/python.exe"),
        os.path.expanduser("~/.wine/drive_c/Program Files/Python311/python.exe"),
    ]

    for py_path in possible_paths:
        if os.path.exists(py_path):
            return py_path

    # Try running python inside wine directly
    try:
        res = subprocess.run(["wine", "python", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            return "python"
    except Exception:
        pass

    return None

def build_executable():
    """Bundles the entire application into a single executable (.exe for Windows or ELF for Linux)."""
    clean_build_artifacts()
    os.makedirs(RELEASE_DIR, exist_ok=True)

    current_os = platform.system().lower()
    entry_point = os.path.join(PROJECT_ROOT, "ui", "app.py")
    if not os.path.exists(entry_point):
        entry_point = os.path.join(PROJECT_ROOT, "auratool_factory.py")

    print(f"[*] Starting build process on platform: {platform.system()}")
    print(f"[*] Entry point: {entry_point}")
    print(f"[*] Output directory: {RELEASE_DIR}")

    if current_os == "linux":
        wine_python = find_wine_python()
        if wine_python:
            print("[*] Wine environment detected. Building Windows executable (.exe) on Ubuntu/Linux...")
            app_name = "AuraTool.exe"
            pyinstaller_cmd = [
                "wine", wine_python, "-m", "PyInstaller",
                "--onefile",
                "--name=AuraTool",
                "--distpath=" + RELEASE_DIR,
                "--workpath=" + BUILD_DIR,
                "--clean",
                "--noconfirm"
            ]
        else:
            print("[!] Wine / Windows Python environment not found on Linux.")
            print("[*] Building native Linux executable (AuraTool)...")
            ensure_pyinstaller()
            app_name = "AuraTool"
            pyinstaller_cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--name=AuraTool",
                "--distpath=" + RELEASE_DIR,
                "--workpath=" + BUILD_DIR,
                "--clean",
                "--noconfirm"
            ]
    else:
        ensure_pyinstaller()
        app_name = "AuraTool.exe"
        pyinstaller_cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--name=AuraTool",
            "--distpath=" + RELEASE_DIR,
            "--workpath=" + BUILD_DIR,
            "--clean",
            "--noconfirm"
        ]

    for imp in HIDDEN_IMPORTS:
        pyinstaller_cmd.extend(["--hidden-import", imp])

    pyinstaller_cmd.append(entry_point)

    print(f"[*] Executing build command: {' '.join(pyinstaller_cmd)}")
    result = subprocess.run(pyinstaller_cmd)

    if result.returncode == 0:
        output_path = os.path.join(RELEASE_DIR, app_name)
        print(f"\n[SUCCESS] Build complete! Target binary generated at:")
        print(f"          -> {output_path}")
    else:
        print("\n[ERROR] Build failed! Check PyInstaller output logs above.")

    clean_build_artifacts()

if __name__ == "__main__":
    build_executable()
