#!/usr/bin/env python3
"""
Camera Viewer with ArUco Marker Detection
==========================================

Features:
- Live camera streaming
- ArUco marker detection
- Real-time depth/distance estimation
- Keyboard controls for different modes

Controls:
  'a' - Toggle ArUco detection ON/OFF
  'd' - Toggle distance display
  'i' - Toggle marker ID display
  'g' - Grayscale mode
  'e' - Edge detection
  'o' - Original (no processing)
  'q' - Quit
  'h' - Show help
"""

import cv2
import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import ArucoDetector, ProcessingMode, create_processor


def print_help():
    """Print help information."""
    print("\n" + "="*60)
    print("CAMERA VIEWER WITH ARUCO DETECTION")
    print("="*60)
    print("\nKeyboard Controls:")
    print("  'a' - Toggle ArUco detection ON/OFF")
    print("  'd' - Toggle distance display")
    print("  'i' - Toggle marker ID display")
    print("  'g' - Grayscale mode")
    print("  'e' - Edge detection")
    print("  'o' - Original (no processing)")
    print("  'h' - Show this help")
    print("  'q' - Quit")
    print("\nArUco Marker Setup:")
    print("  1. Generate markers: python3 -m camera_processing.aruco_detector")
    print("  2. Print the generated markers")
    print("  3. Measure the printed marker size in cm")
    print("  4. Update MARKER_SIZE_CM in this script")
    print("="*60 + "\n")


def main():
    # Configuration
    CAMERA_URL = "http://10.22.227.47:4747/video"  # Change to your camera URL
    MARKER_SIZE_CM = 15.0  # Real-world size of your printed marker in cm
    ARUCO_DICT_TYPE = "DICT_6X6_250"
    FOCAL_LENGTH_PX = 490.20  # Calibrated focal length for accurate depth measurement
    
    print_help()
    
    print(f"Connecting to camera at {CAMERA_URL}...")
    cap = cv2.VideoCapture(CAMERA_URL)
    
    if not cap.isOpened():
        print(f"✗ ERROR: Failed to connect to camera")
        print(f"  URL: {CAMERA_URL}")
        return
    
    print("✓ Connected successfully!")
    
    # Set buffer size for lower latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Initialize ArUco detector
    aruco_detector = ArucoDetector(
        aruco_dict_type=ARUCO_DICT_TYPE,
        marker_size_cm=MARKER_SIZE_CM,
        focal_length_px=FOCAL_LENGTH_PX
    )
    
    # Initialize frame processor (optional)
    current_mode = ProcessingMode.ORIGINAL
    processor = create_processor(current_mode)
    
    # State flags
    aruco_enabled = True
    show_distance = True
    show_id = True
    
    # Window setup
    window_name = "Camera Viewer - ArUco Detection (Press 'h' for help)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    
    frame_count = 0
    markers_detected = 0
    
    print("\nStarting stream... Press 'h' for help, 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print("\n✗ Failed to read frame from camera")
            break
        
        # Apply image processing if not in original mode
        if current_mode != ProcessingMode.ORIGINAL:
            frame = processor.process(frame)
        
        # Detect ArUco markers
        if aruco_enabled:
            corners, ids, rejected = aruco_detector.detect(frame)
            
            if ids is not None and len(ids) > 0:
                markers_detected = len(ids)
                # Draw detections
                frame = aruco_detector.draw_detections(
                    frame,
                    corners,
                    ids,
                    show_distance=show_distance,
                    show_id=show_id
                )
                
                # Get detailed marker info
                markers_info = aruco_detector.get_marker_info(corners, ids)
                
                # Print info for first marker (optional)
                if frame_count % 30 == 0:  # Every 30 frames
                    for info in markers_info:
                        print(f"  Marker ID {info['id']}: {info['distance_cm']:.1f}cm away")
            else:
                markers_detected = 0
        
        # Add status overlay
        status_y = 30
        cv2.putText(frame, f"Frame: {frame_count} | Markers: {markers_detected}",
                   (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        status_y += 25
        cv2.putText(frame, f"ArUco: {'ON' if aruco_enabled else 'OFF'} | Mode: {current_mode.value}",
                   (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display frame
        cv2.imshow(window_name, frame)
        frame_count += 1
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\nQuitting...")
            break
        
        elif key == ord('h'):
            print_help()
        
        elif key == ord('a'):
            aruco_enabled = not aruco_enabled
            print(f"ArUco detection: {'ON' if aruco_enabled else 'OFF'}")
        
        elif key == ord('d'):
            show_distance = not show_distance
            print(f"Distance display: {'ON' if show_distance else 'OFF'}")
        
        elif key == ord('i'):
            show_id = not show_id
            print(f"ID display: {'ON' if show_id else 'OFF'}")
        
        elif key == ord('o'):
            current_mode = ProcessingMode.ORIGINAL
            processor = create_processor(current_mode)
            print(f"Switched to: {current_mode.value}")
        
        elif key == ord('g'):
            current_mode = ProcessingMode.GRAYSCALE
            processor = create_processor(current_mode)
            print(f"Switched to: {current_mode.value}")
        
        elif key == ord('e'):
            current_mode = ProcessingMode.EDGE_DETECTION
            processor = create_processor(current_mode, threshold1=100, threshold2=200)
            print(f"Switched to: {current_mode.value}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal frames processed: {frame_count}")
    print("Goodbye!")


if __name__ == "__main__":
    main()
