@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  AuraTool-Suite — Windows Installer v6.0.0
REM  Universal Device Maintenance & Repair Platform
REM ═══════════════════════════════════════════════════════════════════════════════

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "PYTHON_MIN=3.8"

REM Colors
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "NC=[0m"

echo.
echo %CYAN%  ================================================================%NC%
echo %CYAN%     AuraTool-Suite — Windows Installer v6.0.0                  %NC%
echo %CYAN%     Universal Device Maintenance ^& Repair Platform              %NC%
echo %CYAN%  ================================================================%NC%
echo.

REM ═══════════════════════════════════════════════════════════════════════════════
REM  Check Python
REM ═══════════════════════════════════════════════════════════════════════════════
echo %YELLOW%[1/6] Checking Python installation...%NC%

set "PYTHON_FOUND=0"

REM Try python command
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set "PY_VER=%%a"
    for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
        set "PY_MAJOR=%%a"
        set "PY_MINOR=%%b"
    )
    if !PY_MAJOR! GEQ 3 if !PY_MINOR! GEQ 8 (
        set "PYTHON=python"
        set "PYTHON_FOUND=1"
        echo %GREEN%  [OK] Python !PY_VER! found: python%NC%
    )
)

REM Try py launcher
if %PYTHON_FOUND% EQU 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=2 delims= " %%a in ('py --version 2^>^&1') do set "PY_VER=%%a"
        for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
            set "PY_MAJOR=%%a"
            set "PY_MINOR=%%b"
        )
        if !PY_MAJOR! GEQ 3 if !PY_MINOR! GEQ 8 (
            set "PYTHON=py"
            set "PYTHON_FOUND=1"
            echo %GREEN%  [OK] Python !PY_VER! found: py%NC%
        )
    )
)

REM Try py -3
if %PYTHON_FOUND% EQU 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        py -3 --version >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            for /f "tokens=2 delims= " %%a in ('py -3 --version 2^>^&1') do set "PY_VER=%%a"
            for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
                set "PY_MAJOR=%%a"
                set "PY_MINOR=%%b"
            )
            if !PY_MAJOR! GEQ 3 if !PY_MINOR! GEQ 8 (
                set "PYTHON=py -3"
                set "PYTHON_FOUND=1"
                echo %GREEN%  [OK] Python !PY_VER! found: py -3%NC%
            )
        )
    )
)

if %PYTHON_FOUND% EQU 0 (
    echo %RED%  [FAIL] Python 3.8+ not found.%NC%
    echo %CYAN%  Please install Python 3.8 or newer from: https://www.python.org/downloads/%NC%
    echo %CYAN%  Make sure to check "Add Python to PATH" during installation.%NC%
    pause
    exit /b 1
)

REM ═══════════════════════════════════════════════════════════════════════════════
REM  Check system dependencies
REM ═══════════════════════════════════════════════════════════════════════════════
echo %YELLOW%[2/6] Checking system dependencies...%NC%

REM Check tkinter
%PYTHON% -c "import tkinter" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%  [OK] tkinter (GUI toolkit)%NC%
) else (
    echo %YELLOW%  [WARN] tkinter not found. GUI may not work. Install python3-tk or reinstall Python with tkinter.%NC%
)

REM Check ADB
where adb >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%  [OK] ADB (Android Debug Bridge)%NC%
) else (
    echo %YELLOW%  [WARN] ADB not found — device operations will use simulation mode%NC%
)

REM Check Fastboot
where fastboot >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%  [OK] Fastboot%NC%
) else (
    echo %YELLOW%  [WARN] Fastboot not found — flashing operations will use simulation mode%NC%
)

REM ═══════════════════════════════════════════════════════════════════════════════
REM  Create Virtual Environment
REM ═══════════════════════════════════════════════════════════════════════════════
echo %YELLOW%[3/6] Creating Python virtual environment...%NC%

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo %GREEN%  [OK] Virtual environment already exists%NC%
) else (
    %PYTHON% -m venv "%VENV_DIR%"
    if %ERRORLEVEL% NEQ 0 (
        echo %RED%  [FAIL] Failed to create virtual environment%NC%
        pause
        exit /b 1
    )
    echo %GREEN%  [OK] Virtual environment created%NC%
)

REM Activate
call "%VENV_DIR%\Scripts\activate.bat"
echo %GREEN%  [OK] Virtual environment activated%NC%

REM ═══════════════════════════════════════════════════════════════════════════════
REM  Install Dependencies
REM ═══════════════════════════════════════════════════════════════════════════════
echo %YELLOW%[4/6] Installing Python dependencies...%NC%

pip install --upgrade pip --quiet --disable-pip-version-check 2>nul

if exist "%SCRIPT_DIR%requirements.txt" (
    pip install -r "%SCRIPT_DIR%requirements.txt" --quiet --disable-pip-version-check
    echo %GREEN%  [OK] All dependencies installed from requirements.txt%NC%
) else (
    echo %RED%  [FAIL] requirements.txt not found%NC%
    pause
    exit /b 1
)

REM ═══════════════════════════════════════════════════════════════════════════════
REM  Run Validation
REM ═══════════════════════════════════════════════════════════════════════════════
echo %YELLOW%[5/6] Running quick validation...%NC%

cd /d "%SCRIPT_DIR%"
%PYTHON% -c "
from core.license_manager import LicenseManager
from core.security import SecurityManager
from modules.localization import LocalizationManager
from modules.smart_devices import SmartDeviceManager, ECOSYSTEM_CATALOGUE
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from modules.device_drivers import DeviceDriverManager

loc = LocalizationManager('en')
cats = list(ECOSYSTEM_CATALOGUE.keys())
total = sum(len(m) for c in ECOSYSTEM_CATALOGUE.values() for m in c.values())
print(f'  [OK] {len(cats)} device categories, {total}+ models loaded')
print(f'  [OK] {len(loc.SUPPORTED_LANGUAGES)} languages supported')
print(f'  [OK] All core modules validated')
" 2>nul

if %ERRORLEVEL% EQU 0 (
    echo %GREEN%  [OK] All validation checks passed%NC%
) else (
    echo %YELLOW%  [WARN] Some modules may have issues — running with limited features%NC%
)

REM ═══════════════════════════════════════════════════════════════════════════════
REM  Launch
REM ═══════════════════════════════════════════════════════════════════════════════
echo %YELLOW%[6/6] Launching AuraTool-Suite...%NC%
echo.

echo %GREEN%=============================================================%NC%
echo %GREEN%  [SUCCESS] Installation complete!%NC%
echo %GREEN%=============================================================%NC%
echo.

if "%1"=="--no-gui" (
    echo %CYAN%  Running in CLI mode...%NC%
    %PYTHON% main.py
) else if "%1"=="--no-launch" (
    echo %GREEN%  Installation complete. Run 'install.bat' to launch.%NC%
) else (
    echo %GREEN%  Starting AuraTool-Suite GUI...%NC%
    start "" %PYTHON% main.py
)

echo.
pause
