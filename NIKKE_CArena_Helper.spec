# -*- mode: python ; coding: utf-8 -*-


import os

# --- Helper function to find mode modules ---
def get_hidden_imports_for_modes(modes_dir='modes'):
   hidden = []
   if os.path.isdir(modes_dir):
       for filename in os.listdir(modes_dir):
           if filename.startswith('mode') and filename.endswith('.py'):
               module_name = f"{modes_dir}.{filename[:-3]}"
               hidden.append(module_name)
   return hidden

# --- Get mode hidden imports ---
mode_hidden_imports = get_hidden_imports_for_modes()

import os

# --- Define data files ---
data_files = [('config.json', '.'), ('icon.ico', '.')]

# --- Define hidden imports ---
# Add modes, potentially core modules, and library specifics
hidden_imports = [
   'PIL._tkinter_finder', # Often needed for Pillow with Tkinter GUIs
   'PIL.ImageTk',
   'PIL.Image',
   'keyboard._winkeyboard', # For keyboard library on Windows
   # Add core modules explicitly if needed (usually not, but safe)
   'core.constants',
   'core.utils',
   'core.match_processing',
   'core.player_processing',
   # Add other potential hidden imports if issues arise
   # 'pygetwindow', # If used by core.utils
] + mode_hidden_imports # Add the dynamically found mode modules


a = Analysis(
   ['gui_app.py'],
   pathex=['.'], # Explicitly add current directory to path
   binaries=[],
   datas=data_files,
   hiddenimports=hidden_imports, # Use the defined hidden_imports list
   hookspath=[],
   hooksconfig={},
   runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NIKKE_CArena_Helper',
    debug=False,
    bootloader_ignore_signals=False,
   strip=False,
   upx=True,
   console=False, # Set back to False for release
   disable_windowed_traceback=False,
   argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    uac_admin=False)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    Tree('assets', prefix='assets'),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NIKKE_CArena_Helper',
)
