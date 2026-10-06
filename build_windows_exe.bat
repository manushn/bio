@echo off
setlocal EnableDelayedExpansion
title NICETECH_biometric - Windows EXE Builder

echo =========================================================================
echo   NICETECH_biometric - One-Click Windows EXE Builder
echo =========================================================================
echo.

:: 1. Check Python installation
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to your Windows PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [*] Python detected:
python --version
echo.

:: 2. Upgrade pip and install build dependencies
echo [*] Installing required packages (ReportLab, PyInstaller)...
python -m pip install --upgrade pip
python -m pip install reportlab pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies via pip.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.
echo.

:: 3. Clean prior build artifacts
echo [*] Cleaning previous build folders...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
echo.

:: 4. Build standalone Windows executable
echo [*] Compiling standalone NICETECH_biometric.exe...
echo [*] Please wait a moment while PyInstaller packages the system...
python -m PyInstaller --clean NICETECH_biometric.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed! Review the error log above.
    pause
    exit /b 1
)
echo.

:: 5. Organize output
if exist "dist\NICETECH_biometric.exe" (
    if not exist "Ready_To_Distribute" mkdir "Ready_To_Distribute"
    copy /y "dist\NICETECH_biometric.exe" "Ready_To_Distribute\NICETECH_biometric.exe" >nul
    
    echo =========================================================================
    echo   BUILD SUCCESSFUL!
    echo =========================================================================
    echo.
    echo   Your standalone executable is ready:
    echo   Location: Ready_To_Distribute\NICETECH_biometric.exe
    echo.
    echo   HOW TO SHARE:
    echo   1. Simply share "NICETECH_biometric.exe" (Email, USB, Google Drive).
    echo   2. On any Windows PC, double-click "NICETECH_biometric.exe" to run.
    echo   3. On first launch, it automatically creates a fresh database with:
    echo      - Default Admin: niadmin
    echo      - Default Password: ni2027
    echo      - Zero staff and zero punch logs (pristine fresh install)
    echo   4. No Python, no drivers, and no installation required on the client PC!
    echo.
    echo =========================================================================
) else (
    echo [ERROR] NICETECH_biometric.exe was not found in the dist folder.
)

pause
