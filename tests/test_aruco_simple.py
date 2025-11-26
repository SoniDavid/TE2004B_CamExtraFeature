#!/usr/bin/env python3
"""
Simple ArUco Detection Test
============================

Quick test to verify ArUco detection is working.
Displays a marker on screen and tries to detect it.
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import ArucoDetector
import cv2

def main():
    print("="*60)
    print("SIMPLE ARUCO DETECTION TEST")
    print("="*60)
    
    # Load a marker
    marker_path = os.path.join(parent_dir, "aruco_markers", "marker_0.png")
    
    if not os.path.exists(marker_path):
        print(f"✗ Marker not found: {marker_path}")
        return
    
    marker_img = cv2.imread(marker_path)
    
    if marker_img is None:
        print(f"✗ Could not load marker image")
        return
    
    print(f"✓ Loaded marker from: {marker_path}")
    
    # Create detector
    detector = ArucoDetector(aruco_dict_type="DICT_6X6_250", marker_size_cm=10.0)
    
    # Detect
    corners, ids, rejected = detector.detect(marker_img)
    
    if ids is not None and len(ids) > 0:
        print(f"✓ SUCCESS! Detected marker ID: {ids[0][0]}")
        
        # Draw detection
        result = detector.draw_detections(
            marker_img.copy(),
            corners,
            ids,
            show_distance=True,
            show_id=True
        )
        
        # Show result
        cv2.imshow("ArUco Detection Test - Press any key to exit", result)
        print("\nDisplaying result... Press any key in the window to exit.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print(f"✗ No markers detected")
        print(f"  Rejected candidates: {len(rejected)}")
    
    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)
    print("\nNext step: Run viewer with live camera")
    print("  python3 viewer/aruco_viewer.py")


if __name__ == "__main__":
    main()
