# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for NICETECH_biometric
Produces a clean, standalone, zero-installation Windows executable: NICETECH_biometric.exe

Ensures NO historical database files are bundled so every installation
starts with a 100% fresh, clean database containing ONLY the administrator account.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Project paths
project_root = os.path.abspath(os.path.curdir)
app_dir = os.path.join(project_root, 'college_attendance_app')

# Explicitly collect non-database assets only (ensures pristine fresh database on every install)
datas = []
for root, dirs, files in os.walk(app_dir):
    for f in files:
        if not f.endswith(('.db', '.db-wal', '.db-shm', '.bak', '.pyc', '.pre_restore_bak')):
            full_src = os.path.join(root, f)
            rel_folder = os.path.relpath(root, project_root)
            datas.append((full_src, rel_folder))

# Add ReportLab font and data assets
datas += collect_data_files('reportlab')

# Comprehensive hidden imports
hidden_imports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'sqlite3',
    'hashlib',
    'shutil',
    'socket',
    'struct',
    'csv',
    'datetime',
    'threading',
    'time',
    'reportlab',
    'reportlab.platypus',
    'reportlab.lib',
    'reportlab.pdfgen',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'reportlab.lib.colors',
    'app',
    'database',
    'device_driver',
    'attendance_engine',
    'pdf_generator'
]
hidden_imports += collect_submodules('reportlab')

a = Analysis(
    ['run_app.py'],
    pathex=[project_root, app_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'IPython', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NICETECH_biometric',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                  # Hides the black terminal / cmd window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,                # Standard user permissions
    icon=None
)
