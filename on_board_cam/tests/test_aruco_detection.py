#!/usr/bin/env python3
"""
ArUco Detection Diagnostic Tool
================================

Tests ArUco marker detection with your camera and generated markers.
"""

import cv2
import sys
import os
import numpy as np

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import ArucoDetector


def test_marker_file():
    """Test detection on saved marker files."""
    print("\n" + "="*60)
    print("TEST 1: Detecting markers from saved files")
    print("="*60)
    
    marker_dir = os.path.join(parent_dir, "aruco_markers")
    
    if not os.path.exists(marker_dir):
        print(f"✗ Marker directory not found: {marker_dir}")
        return False
    
    # Test with DICT_6X6_250 (what we generated)
    detector = ArucoDetector(aruco_dict_type="DICT_6X6_250")
    
    marker_files = [f for f in os.listdir(marker_dir) if f.startswith("marker_") and f.endswith(".png")]
    
    if not marker_files:
        print(f"✗ No marker files found in {marker_dir}")
        return False
    
    detected_count = 0
    for marker_file in sorted(marker_files)[:3]:  # Test first 3
        marker_path = os.path.join(marker_dir, marker_file)
        print(f"\nTesting {marker_file}...")
        
        img = cv2.imread(marker_path)
        if img is None:
            print(f"  ✗ Could not load image")
            continue
        
        corners, ids, rejected = detector.detect(img)
        
        if ids is not None and len(ids) > 0:
            print(f"  ✓ Detected marker ID: {ids[0][0]}")
            detected_count += 1
        else:
            print(f"  ✗ No markers detected")
            if len(rejected) > 0:
                print(f"    - Found {len(rejected)} rejected candidates")
    
    print(f"\nResult: {detected_count}/{len(marker_files[:3])} markers detected from files")
    return detected_count > 0


def test_camera_detection():
    """Test detection on live camera."""
    print("\n" + "="*60)
    print("TEST 2: Live camera ArUco detection")
    print("="*60)
    
    CAMERA_URL = "http://10.22.227.47:4747/video"
    
    print(f"Connecting to camera: {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    
    if not cap.isOpened():
        print(f"✗ Cannot connect to camera")
        return False
    
    print("✓ Camera connected")
    
    # Test all common dictionaries
    dict_types = ["DICT_4X4_50", "DICT_5X5_50", "DICT_6X6_50", "DICT_6X6_250", "DICT_7X7_50"]
    
    print("\nTesting detection with different ArUco dictionaries...")
    print("Hold a marker in front of the camera now!")
    print("Testing for 5 seconds with each dictionary...\n")
    
    results = {}
    
    for dict_type in dict_types:
        print(f"Testing {dict_type}...")
        detector = ArucoDetector(aruco_dict_type=dict_type)
        
        detected_frames = 0
        test_frames = 50  # Test ~5 seconds at 10fps
        
        for i in range(test_frames):
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            
            corners, ids, rejected = detector.detect(frame)
            
            if ids is not None and len(ids) > 0:
                detected_frames += 1
                if i % 10 == 0:  # Print occasionally
                    print(f"  Frame {i}: Detected marker IDs: {[id[0] for id in ids]}")
        
        detection_rate = (detected_frames / test_frames) * 100
        results[dict_type] = detection_rate
        print(f"  Detection rate: {detection_rate:.1f}%\n")
    
    cap.release()
    
    print("="*60)
    print("DETECTION RESULTS BY DICTIONARY:")
    print("="*60)
    for dict_type, rate in results.items():
        status = "✓" if rate > 0 else "✗"
        print(f"{status} {dict_type:20s}: {rate:5.1f}% detection rate")
    
    best_dict = max(results, key=results.get)
    if results[best_dict] > 0:
        print(f"\n✓ Best dictionary: {best_dict} ({results[best_dict]:.1f}%)")
        return True
    else:
        print("\n✗ No markers detected with any dictionary")
        return False


def test_detection_parameters():
    """Test different detection parameters."""
    print("\n" + "="*60)
    print("TEST 3: Detection parameter tuning")
    print("="*60)
    
    CAMERA_URL = "http://10.22.227.47:4747/video"
    
    cap = cv2.VideoCapture(CAMERA_URL)
    if not cap.isOpened():
        print("✗ Cannot connect to camera")
        return False
    
    print("Testing with adjusted detection parameters...")
    print("Hold a marker in front of the camera!")
    
    # Create detector with adjusted parameters
    detector = ArucoDetector(aruco_dict_type="DICT_6X6_250")
    
    # Adjust detection parameters for better detection
    params = cv2.aruco.DetectorParameters()
    
    # Make detection more lenient
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 23
    params.adaptiveThreshWinSizeStep = 10
    params.adaptiveThreshConstant = 7
    params.minMarkerPerimeterRate = 0.03  # Lower = detect smaller markers
    params.maxMarkerPerimeterRate = 4.0   # Higher = detect larger markers
    params.polygonalApproxAccuracyRate = 0.05
    params.minCornerDistanceRate = 0.05
    params.minDistanceToBorder = 3
    params.minMarkerDistanceRate = 0.05
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.cornerRefinementWinSize = 5
    params.cornerRefinementMaxIterations = 30
    params.cornerRefinementMinAccuracy = 0.1
    
    # Update detector with new parameters
    detector.detector = cv2.aruco.ArucoDetector(detector.aruco_dict, params)
    
    detected_frames = 0
    test_frames = 50
    
    for i in range(test_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        
        # Try both color and grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        corners, ids, rejected = detector.detect(gray)
        
        if ids is not None and len(ids) > 0:
            detected_frames += 1
            if i % 10 == 0:
                print(f"  Frame {i}: Detected {len(ids)} marker(s)")
    
    cap.release()
    
    detection_rate = (detected_frames / test_frames) * 100
    print(f"\nDetection rate with tuned parameters: {detection_rate:.1f}%")
    
    if detection_rate > 0:
        print("✓ Detection working with tuned parameters!")
        return True
    else:
        print("✗ Still no detection even with tuned parameters")
        return False


def main():
    print("="*60)
    print("ARUCO DETECTION DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check OpenCV version
    print(f"\nOpenCV version: {cv2.__version__}")
    
    # Test 1: Saved marker files
    test1_passed = test_marker_file()
    
    # Test 2: Camera detection with different dictionaries
    test2_passed = test_camera_detection()
    
    # Test 3: Tuned parameters
    test3_passed = test_detection_parameters()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print(f"Test 1 (Marker Files):      {'✓ PASS' if test1_passed else '✗ FAIL'}")
    print(f"Test 2 (Live Detection):    {'✓ PASS' if test2_passed else '✗ FAIL'}")
    print(f"Test 3 (Tuned Parameters):  {'✓ PASS' if test3_passed else '✗ FAIL'}")
    
    if test1_passed and not test2_passed:
        print("\n⚠ DIAGNOSIS:")
        print("  - Markers are valid (detected in files)")
        print("  - Camera connection works")
        print("  - Possible issues:")
        print("    1. Wrong ArUco dictionary type")
        print("    2. Marker not printed or displayed clearly")
        print("    3. Poor lighting or camera focus")
        print("    4. Marker too small/large in frame")
        print("\n  RECOMMENDATIONS:")
        print("    - Ensure you're using markers from aruco_markers/ folder")
        print("    - Print markers at least 5cm x 5cm")
        print("    - Use good lighting and hold marker flat")
        print("    - Try displaying marker on a phone/monitor")
    
    elif not test1_passed:
        print("\n⚠ DIAGNOSIS:")
        print("  - Cannot detect even saved markers")
        print("  - Possible OpenCV or ArUco installation issue")
        print("\n  RECOMMENDATIONS:")
        print("    - Check OpenCV installation: pip install opencv-contrib-python")
        print("    - Verify ArUco module: python -c 'import cv2; print(cv2.aruco)'")


if __name__ == "__main__":
    main()
