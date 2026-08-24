import os
import sys
import shutil
import platform
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")

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
            os.remove(spec_path)
            print(f"    Removed: {spec_path}")

def ensure_pyinstaller():
    """Ensures PyInstaller is installed in the current Python environment."""
    try:
        import PyInstaller
        print("[*] PyInstaller is installed and available.")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_executable():
    """Bundles the entire application into a single executable located inside the release directory."""
    clean_build_artifacts()
    ensure_pyinstaller()

    os.makedirs(RELEASE_DIR, exist_ok=True)
    
    os_name = platform.system().lower()
    app_name = "AuraTool.exe" if os_name == "windows" else "AuraTool"
    entry_point = os.path.join(PROJECT_ROOT, "ui", "app.py")
    if not os.path.exists(entry_point):
        entry_point = os.path.join(PROJECT_ROOT, "auratool_factory.py")

    print(f"[*] Starting build process for platform: {platform.system()}")
    print(f"[*] Entry point: {entry_point}")
    print(f"[*] Output directory: {RELEASE_DIR}")

    # Define module hidden imports to ensure all submodules are included in single-file mode
    hidden_imports = [
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

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name=" + os.path.splitext(app_name)[0],
        "--distpath=" + RELEASE_DIR,
        "--workpath=" + BUILD_DIR,
        "--clean",
        "--noconfirm"
    ]

    for imp in hidden_imports:
        pyinstaller_cmd.extend(["--hidden-import", imp])

    pyinstaller_cmd.append(entry_point)

    print(f"[*] Executing command: {' '.join(pyinstaller_cmd)}")
    result = subprocess.run(pyinstaller_cmd)

    if result.returncode == 0:
        output_path = os.path.join(RELEASE_DIR, app_name)
        print(f"\n[SUCCESS] Build complete! Executable generated successfully:")
        print(f"          -> {output_path}")
    else:
        print("\n[ERROR] Build failed! Check PyInstaller output logs above.")

    # Post-build cleanup of intermediate files
    clean_build_artifacts()

if __name__ == "__main__":
    build_executable()
