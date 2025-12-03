#!/usr/bin/env python3
"""
Quick test to verify unified control GUI dependencies and setup
"""

import sys
from pathlib import Path

def test_imports():
    """Test all required imports."""
    print("Testing imports...\n")
    
    results = []
    
    # Core dependencies
    tests = [
        ("tkinter", "Tkinter (GUI framework)"),
        ("asyncio", "Asyncio (async support)"),
        ("threading", "Threading"),
        ("PIL", "Pillow (image handling)"),
        ("cv2", "OpenCV (camera/vision)"),
        ("numpy", "NumPy (arrays)"),
        ("yaml", "PyYAML (config)"),
        ("bleak", "Bleak (BLE)"),
    ]
    
    for module, description in tests:
        try:
            __import__(module)
            results.append((module, description, True, None))
            print(f"✓ {description:<30} OK")
        except ImportError as e:
            results.append((module, description, False, str(e)))
            print(f"✗ {description:<30} MISSING")
    
    print()
    
    # Optional dependencies
    print("Testing optional imports...\n")
    
    optional_tests = [
        ("pynput", "PyNput (manual keyboard control)"),
        ("inputs", "Inputs (gamepad support)"),
    ]
    
    for module, description in optional_tests:
        try:
            __import__(module)
            results.append((module, description, True, None))
            print(f"✓ {description:<30} OK")
        except ImportError as e:
            results.append((module, description, False, str(e)))
            print(f"⚠ {description:<30} MISSING (optional)")
    
    print()
    return results


def test_files():
    """Test required files exist."""
    print("Testing required files...\n")
    
    waypoint_dir = Path(__file__).parent
    
    files = [
        ("unified_control_gui.py", "Main GUI script"),
        ("ble_client.py", "BLE client module"),
        ("waypoints_gui.py", "Original waypoint GUI"),
        ("test_ble_connection.py", "BLE test script"),
        ("scales.txt", "Control scaling config"),
        ("combined_input.py", "Manual control module"),
    ]
    
    results = []
    
    for filename, description in files:
        filepath = waypoint_dir / filename
        exists = filepath.exists()
        results.append((filename, description, exists))
        
        if exists:
            print(f"✓ {description:<30} {filename}")
        else:
            print(f"✗ {description:<30} {filename} NOT FOUND")
    
    print()
    return results


def test_launch_system():
    """Test launch.py has unified option."""
    print("Testing launch system...\n")
    
    launch_path = Path(__file__).parent.parent / "launch.py"
    
    if not launch_path.exists():
        print("✗ launch.py not found")
        return False
    
    with open(launch_path, 'r') as f:
        content = f.read()
    
    if "launch_unified_control" in content and "--unified" in content:
        print("✓ launch.py has --unified option")
        return True
    else:
        print("✗ launch.py missing --unified option")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("  Unified Control GUI - Setup Verification")
    print("="*60)
    print()
    
    # Test imports
    import_results = test_imports()
    
    # Test files
    file_results = test_files()
    
    # Test launch system
    launch_ok = test_launch_system()
    
    # Summary
    print("="*60)
    print("  SUMMARY")
    print("="*60)
    print()
    
    # Count results
    core_ok = all(r[2] for r in import_results if r[0] not in ['pynput', 'inputs'])
    optional_ok = all(r[2] for r in import_results if r[0] in ['pynput', 'inputs'])
    files_ok = all(r[2] for r in file_results)
    
    if core_ok and files_ok and launch_ok:
        print("✓ ALL CORE REQUIREMENTS MET")
        print()
        print("You can launch the unified control GUI with:")
        print("  python3 launch.py --unified")
        print()
        
        if not optional_ok:
            print("⚠ Optional features (manual control) require:")
            print("  pip install pynput inputs")
            print()
    else:
        print("✗ MISSING REQUIREMENTS")
        print()
        
        if not core_ok:
            print("Install missing core dependencies with:")
            print("  pip install -r ../requirements.txt")
            print()
        
        if not files_ok:
            print("Some required files are missing. Check installation.")
            print()
    
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
