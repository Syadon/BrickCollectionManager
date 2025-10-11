#!/usr/bin/env python3
"""
Build script for Brick Collection Manager
Creates executable applications for different operating systems using PyInstaller
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def get_system_info():
    """Get system information for build configuration"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if system == "darwin":
        # macOS
        if arch in ["arm64", "aarch64"]:
            return "macos", "arm64"
        else:
            return "macos", "x64"
    elif system == "windows":
        # Windows
        if arch in ["amd64", "x86_64"]:
            return "windows", "x64"
        else:
            return "windows", "x86"
    elif system == "linux":
        # Linux
        if arch in ["aarch64", "arm64"]:
            return "linux", "arm64"
        elif arch in ["amd64", "x86_64"]:
            return "linux", "x64"
        else:
            return "linux", "x86"
    else:
        return system, arch

def install_dependencies():
    """Install PyInstaller and other build dependencies using uv"""
    print("Installing build dependencies...")
    
    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("✓ uv is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ uv is not installed. Please install uv first:")
        print("  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  Windows: https://astral.sh/uv/install")
        return False
    
    # Sync project dependencies
    try:
        subprocess.run(["uv", "sync"], check=True, capture_output=True)
        print("✓ Synced project dependencies")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to sync dependencies: {e}")
        return False
    
    # Add development dependencies for building
    dev_dependencies = ["pillow"]
    
    for dep in dev_dependencies:
        try:
            subprocess.run(["uv", "add", "--dev", dep], 
                         check=True, capture_output=True)
            print(f"✓ Added development dependency: {dep}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to add {dep}: {e}")
            # Continue with build even if some dev deps fail
    
    return True

def prepare_resources():
    """Prepare resources for packaging"""
    print("Preparing resources...")
    
    # Ensure resources directory exists
    resources_dir = Path("resources")
    if not resources_dir.exists():
        print("✗ Resources directory not found!")
        return False
    
    # Check for required resource files
    required_files = [
        "resources/schema.sql",
        "resources_rc.py",
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"✗ Required file not found: {file_path}")
            return False
    
    print("✓ Resources prepared")
    return True

def build_application():
    """Build the application using PyInstaller"""
    system, arch = get_system_info()
    print(f"Building for {system} {arch}...")
    
    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("✓ Cleaned dist directory")
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("✓ Cleaned build directory")
    
    # Run PyInstaller
    try:
        cmd = [
            "uv", "run", "pyinstaller",
            "--clean",
            "--noconfirm",
            "BrickCollectionManager.spec"
        ]
        
        print("Running PyInstaller with uv...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✓ Build completed successfully")
        
        # Show build output location
        if system == "macos":
            app_path = dist_dir / "BrickCollectionManager.app"
            if app_path.exists():
                print(f"✓ macOS app created: {app_path}")
        else:
            exe_name = "BrickCollectionManager.exe" if system == "windows" else "BrickCollectionManager"
            exe_path = dist_dir / exe_name
            if exe_path.exists():
                print(f"✓ Executable created: {exe_path}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def create_distribution_package():
    """Create distribution package with additional files"""
    system, arch = get_system_info()
    
    print("Creating distribution package...")
    
    dist_dir = Path("dist")
    package_dir = dist_dir / f"BrickCollectionManager-{system}-{arch}"
    
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    package_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy the built application
    if system == "macos":
        app_source = dist_dir / "BrickCollectionManager.app"
        app_dest = package_dir / "BrickCollectionManager.app"
        if app_source.exists():
            shutil.copytree(app_source, app_dest)
    else:
        exe_name = "BrickCollectionManager.exe" if system == "windows" else "BrickCollectionManager"
        exe_source = dist_dir / exe_name
        exe_dest = package_dir / exe_name
        if exe_source.exists():
            shutil.copy2(exe_source, exe_dest)
    
    # Copy additional files
    additional_files = [
        ("README.md", "README.md"),
        ("requirements.txt", "requirements.txt"),
    ]
    
    for src, dst in additional_files:
        src_path = Path(src)
        if src_path.exists():
            shutil.copy2(src_path, package_dir / dst)
    
    print(f"✓ Distribution package created: {package_dir}")
    return True

def main():
    """Main build process"""
    print("🔨 Building Brick Collection Manager")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    system, arch = get_system_info()
    print(f"System: {system} {arch}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    # Build steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Preparing resources", prepare_resources),
        ("Building application", build_application),
        ("Creating distribution package", create_distribution_package),
    ]
    
    for step_name, step_func in steps:
        print(f"📦 {step_name}...")
        if not step_func():
            print(f"❌ Failed at: {step_name}")
            sys.exit(1)
        print()
    
    print("🎉 Build completed successfully!")
    print("\nTo run the application:")
    
    if system == "macos":
        print("  - Double-click BrickCollectionManager.app")
        print("  - Or run: open dist/BrickCollectionManager-{system}-{arch}/BrickCollectionManager.app")
    elif system == "windows":
        print("  - Double-click BrickCollectionManager.exe")
        print(f"  - Or run: dist\\BrickCollectionManager-{system}-{arch}\\BrickCollectionManager.exe")
    else:
        print("  - Run: ./dist/BrickCollectionManager-{system}-{arch}/BrickCollectionManager")
        print("  - Make sure to set execute permissions: chmod +x BrickCollectionManager")

if __name__ == "__main__":
    main()