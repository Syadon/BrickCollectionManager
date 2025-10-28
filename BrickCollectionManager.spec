# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Get the project root directory (current working directory)
project_root = Path.cwd()

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include UI files
        ('ui/*.py', 'ui'),
        # Include resources
        ('resources/*.png', 'resources'),
        ('resources/*.sql', 'resources'),
        ('resources/*.css', 'resources'),
        ('resources/*.qrc', 'resources'),
        # Include database schema
        ('resources/schema.sql', 'resources'),
        # Include any additional data files
        ('resources_rc.py', '.'),
    ],
    hiddenimports=[
        # Core PySide6 modules
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'PySide6.QtSql',
        # Camera support (rimuovi se non usi la camera)
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        # OpenCV headless
        'cv2',
        'numpy',
        # Other libraries
        'requests',
        'qt_material',
        'sqlite3',
        'src.mainWindow',
        'src.database',
        'src.widgets.colorLabel',
        'src.widgets',
        'src.imageProvider',
        'resources_rc',
        'ui',
        'ui.ui_addcontainerdialog',
        'ui.ui_addFromCameraWidget',
        'ui.ui_addFromFileWidget',
        'ui.ui_addManualWidget',
        'ui.ui_containerDetailDialog',
        'ui.ui_databaseWidget',
        'ui.ui_detailPartDialog',
        'ui.ui_searchManualWidget',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI frameworks
        'tkinter',
        'PyQt5',
        'PyQt6',
        'wxPython',
        # PySide6 modules non usati
        'PySide6.QtDesigner',
        # 'PySide6.QtUiTools',  # Richiesto da qt_material
        'PySide6.QtHelp',
        'PySide6.QtTest',
        'PySide6.QtQml',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtDBus',
        'PySide6.QtPrintSupport',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebChannel',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DAnimation',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtLocation',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtRemoteObjects',
        'PySide6.QtScxml',
        'PySide6.QtStateMachine',
        # Scientific computing (non usate)
        'matplotlib',
        'scipy',
        'pandas',
        'sklearn',
        # Development tools
        'IPython',
        'notebook',
        'jupyter',
        'pytest',
        'test',
        'unittest',
        'setuptools',
        'distutils',
        'pip',
        # Documentazione
        'pydoc',
        'doctest',
        # Network/Email non usati direttamente (ma email è richiesto da urllib3)
        # 'email',  # NON escludere - richiesto da urllib3/requests
        'ftplib',
        'smtplib',
        'poplib',
        'imaplib',
        # Altre librerie non necessarie
        'pycparser',
        'PIL.ImageQt',  # se non usi PIL/Pillow
    ],
    noarchive=False,
    optimize=0,  # Non usare optimize=2, causa problemi con numpy docstrings
)

pyz = PYZ(a.pure)

# Platform-specific configurations
if sys.platform == 'win32':
    icon_file = 'resources/app_icon.png'  # Windows .ico format
    console_mode = False
elif sys.platform == 'darwin':
    icon_file = 'resources/app_icon.png'  # macOS .icns format
    console_mode = False  # Disable console for normal macOS app
else:
    icon_file = 'resources/app_icon.png'  # Linux
    console_mode = False

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BrickCollectionManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Rimuove debug symbols (riduce dimensioni)
    upx=True,
    console=console_mode,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist',  # Camera and other permissions
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,  # Rimuove debug symbols
    upx=True,
    upx_exclude=[],
    name='BrickCollectionManager',
)

# macOS App Bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BrickCollectionManager.app',
        icon=icon_file,
        bundle_identifier='com.brickcollectionmanager.app',
        entitlements_file='entitlements.plist',  # Add entitlements to BUNDLE
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '0.2.1',
            'CFBundleVersion': '0.2.1',
            'CFBundleDisplayName': 'Brick Collection Manager',
            'CFBundleGetInfoString': 'Brick Collection Manager 0.2.1',
            'NSHumanReadableCopyright': 'Copyright © 2025 Brick Collection Manager Team',
            'LSMinimumSystemVersion': '10.13.0',
            'NSRequiresAquaSystemAppearance': False,
            'LSApplicationCategoryType': 'public.app-category.productivity',
            'CFBundleDocumentTypes': [],
            'NSSupportsAutomaticGraphicsSwitching': True,
            # Camera and Microphone permissions
            'NSCameraUsageDescription': 'This app uses the camera to recognize LEGO parts.',
            'NSMicrophoneUsageDescription': 'This app may use the microphone for camera functionality.',
        },
    )
