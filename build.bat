@echo off
chcp 65001 >nul
title Build Clipboard Image Saver Installers
echo ============================================
echo  Building Clipboard Image Saver - EN + ZH
echo ============================================
echo.

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 pause & exit /b 1
echo.

echo [2/3] Building EXE with PyInstaller...
pyinstaller clipboard_image_saver.spec
if %errorlevel% neq 0 pause & exit /b 1
echo.

echo [3/3] Compiling installers with Inno Setup...
echo  - English: installer_en.iss
echo  - Chinese: installer_zh.iss
iscc installer_en.iss
iscc installer_zh.iss
echo.

echo ============================================
echo  Done! Output files:
echo   dist\ClipboardImageSaver_Setup_EN_1.0.0.exe
echo   dist\ClipboardImageSaver_Setup_ZH_1.0.0.exe
echo ============================================
pause
