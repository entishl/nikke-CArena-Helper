@echo off
echo [*] Syncing dependencies using uv...
uv sync
if %errorlevel% neq 0 (
    echo [!] uv sync failed. Please check error messages.
    pause
    exit /b %errorlevel%
)

echo [*] Building package with PyInstaller...
uv run pyinstaller --clean -y NIKKE_CArena_Helper.spec
if %errorlevel% neq 0 (
    echo [!] PyInstaller build failed. Please check error messages.
    pause
    exit /b %errorlevel%
)

echo [*] Copying config.json to output directory...
copy /y config.json dist\NIKKE_CArena_Helper\

echo [*] Build finished successfully. Check the dist/ directory.
pause
