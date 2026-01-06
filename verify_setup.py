#!/usr/bin/env python3
"""
Quick setup and verification script for the Chess Opening Explorer
"""

import sys
import subprocess

def check_dependencies():
    """Check if all required packages are installed"""
    required = ['shiny', 'chess', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} missing")
            missing.append(package)
    
    return len(missing) == 0

def main():
    print("Chess Opening Explorer - Setup Verification\n")
    print("=" * 50)
    
    print("\n1. Checking Python version...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("   ⚠ Warning: Python 3.8+ recommended")
    else:
        print("   ✓ Version OK")
    
    print("\n2. Checking dependencies...")
    if check_dependencies():
        print("   ✓ All dependencies installed")
    else:
        print("\n   To install missing packages, run:")
        print("   pip install -r requirements.txt")
        return 1
    
    print("\n3. Verifying app structure...")
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            if 'def server' in content and 'app_ui' in content:
                print("   ✓ app.py structure valid")
            else:
                print("   ✗ app.py may be incomplete")
                return 1
    except FileNotFoundError:
        print("   ✗ app.py not found")
        return 1
    
    print("\n" + "=" * 50)
    print("\n✓ Setup verification complete!\n")
    print("To run the app locally:")
    print("  shiny run app.py --reload")
    print("\nTo deploy to GitHub Pages:")
    print("  1. Commit and push to main branch")
    print("  2. Enable GitHub Pages in repository settings")
    print("  3. Set source to 'GitHub Actions'")
    print("\nFor more information, see README.md")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
