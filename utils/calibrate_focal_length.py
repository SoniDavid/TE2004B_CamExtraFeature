#!/usr/bin/env python3
"""
Focal Length Calibration Tool
==============================

This tool helps you calibrate the focal length for accurate depth measurement.

How it works:
1. Place a marker at a KNOWN distance (measure with a ruler/tape)
2. Run this tool and enter the actual distance
3. It calculates the correct focal length for your camera
4. Use this focal length in aruco_viewer.py
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import ArucoDetector
import cv2
import numpy as np


def calibrate_focal_length(camera_url, marker_size_cm, aruco_dict_type="DICT_6X6_250"):
    """
    Interactive calibration to find the correct focal length.
    
    Formula: focal_length = (perceived_width_px × actual_distance_cm) / marker_size_cm
    """
    
    print("="*70)
    print("FOCAL LENGTH CALIBRATION TOOL")
    print("="*70)
    print("\nInstructions:")
    print("  1. Place your ArUco marker at a KNOWN distance from the camera")
    print("  2. Measure the distance from camera lens to marker (use ruler/tape)")
    print("  3. Make sure the marker is clearly visible and well-lit")
    print("  4. Keep the marker flat and perpendicular to the camera")
    print("\n" + "="*70)
    
    # Connect to camera
    print(f"\nConnecting to camera: {camera_url}")
    cap = cv2.VideoCapture(camera_url)
    
    if not cap.isOpened():
        print("✗ Cannot connect to camera")
        return None
    
    print("✓ Camera connected")
    
    # Create detector with a default focal length (we'll calibrate this)
    detector = ArucoDetector(
        aruco_dict_type=aruco_dict_type,
        marker_size_cm=marker_size_cm,
        focal_length_px=1000.0  # Initial guess
    )
    
    measurements = []
    
    print("\n" + "="*70)
    print("Starting calibration...")
    print("="*70)
    
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("✗ Failed to read frame")
            continue
        
        # Detect markers
        corners, ids, rejected = detector.detect(frame)
        
        # Draw detection
        display_frame = frame.copy()
        
        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(display_frame, corners, ids)
            
            # Calculate perceived width in pixels
            for i, corner in enumerate(corners):
                top_edge = np.linalg.norm(corner[0][0] - corner[0][1])
                bottom_edge = np.linalg.norm(corner[0][2] - corner[0][3])
                perceived_width_px = (top_edge + bottom_edge) / 2.0
                
                # Draw info
                center = corner[0].mean(axis=0).astype(int)
                cv2.putText(display_frame, f"ID: {ids[i][0]}", 
                           (center[0], center[1] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Width: {perceived_width_px:.1f}px", 
                           (center[0], center[1] + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.putText(display_frame, "MARKER DETECTED - Press SPACE to calibrate", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(display_frame, "NO MARKER DETECTED", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        cv2.putText(display_frame, "Press 'q' to finish calibration", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Calibration - Position marker at known distance", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        
        elif key == ord(' '):  # Space bar
            if ids is None or len(ids) == 0:
                print("✗ No marker detected! Position marker in view and try again.")
                continue
            
            # Get actual distance from user
            print("\n" + "-"*70)
            actual_distance = input("Enter the ACTUAL distance from camera to marker (in cm): ").strip()
            
            try:
                actual_distance_cm = float(actual_distance)
            except ValueError:
                print("✗ Invalid input. Please enter a number.")
                continue
            
            # Calculate perceived width
            corner = corners[0]
            top_edge = np.linalg.norm(corner[0][0] - corner[0][1])
            bottom_edge = np.linalg.norm(corner[0][2] - corner[0][3])
            perceived_width_px = (top_edge + bottom_edge) / 2.0
            
            # Calculate focal length
            # Formula: distance = (marker_size × focal_length) / perceived_width
            # Rearranged: focal_length = (perceived_width × distance) / marker_size
            focal_length = (perceived_width_px * actual_distance_cm) / marker_size_cm
            
            measurements.append({
                'actual_distance': actual_distance_cm,
                'perceived_width': perceived_width_px,
                'focal_length': focal_length
            })
            
            print(f"✓ Measurement recorded:")
            print(f"  - Actual distance: {actual_distance_cm} cm")
            print(f"  - Perceived width: {perceived_width_px:.2f} px")
            print(f"  - Calculated focal length: {focal_length:.2f} px")
            print(f"\nTotal measurements: {len(measurements)}")
            print("Position marker at a DIFFERENT distance and press SPACE again,")
            print("or press 'q' to finish calibration.")
            print("-"*70)
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Calculate final focal length
    if len(measurements) == 0:
        print("\n✗ No measurements taken. Calibration failed.")
        return None
    
    print("\n" + "="*70)
    print("CALIBRATION RESULTS")
    print("="*70)
    
    focal_lengths = [m['focal_length'] for m in measurements]
    avg_focal_length = np.mean(focal_lengths)
    std_focal_length = np.std(focal_lengths)
    
    print(f"\nMeasurements taken: {len(measurements)}")
    print("\nIndividual measurements:")
    for i, m in enumerate(measurements, 1):
        print(f"  {i}. Distance: {m['actual_distance']:6.1f} cm → Focal length: {m['focal_length']:7.2f} px")
    
    print(f"\n{'='*70}")
    print(f"CALIBRATED FOCAL LENGTH: {avg_focal_length:.2f} px")
    print(f"Standard deviation: {std_focal_length:.2f} px")
    print(f"{'='*70}")
    
    print("\n✓ Calibration complete!")
    print("\nNext steps:")
    print(f"  1. Open viewer/aruco_viewer.py")
    print(f"  2. Change this line:")
    print(f"       FOCAL_LENGTH_PX = {avg_focal_length:.2f}")
    print(f"  3. Run: python3 viewer/aruco_viewer.py")
    
    return avg_focal_length


def main():
    # Configuration
    CAMERA_URL = "http://10.22.227.47:4747/video"
    MARKER_SIZE_CM = 15.0  # Your actual marker size
    ARUCO_DICT_TYPE = "DICT_6X6_250"
    
    print("\nConfiguration:")
    print(f"  Camera URL: {CAMERA_URL}")
    print(f"  Marker size: {MARKER_SIZE_CM} cm")
    print(f"  ArUco dict: {ARUCO_DICT_TYPE}")
    
    change = input("\nUse these settings? (y/n): ").strip().lower()
    
    if change == 'n':
        CAMERA_URL = input(f"Camera URL [{CAMERA_URL}]: ").strip() or CAMERA_URL
        marker_input = input(f"Marker size in cm [{MARKER_SIZE_CM}]: ").strip()
        if marker_input:
            MARKER_SIZE_CM = float(marker_input)
    
    calibrate_focal_length(CAMERA_URL, MARKER_SIZE_CM, ARUCO_DICT_TYPE)


if __name__ == "__main__":
    main()
