#!/usr/bin/env python3
"""
Camera Viewer with ArUco Marker Detection
==========================================

Features:
- Live camera streaming
- ArUco marker detection
- Real-time depth/distance estimation
- Keyboard controls for different modes
- Configuration via YAML file

Controls:
  'a' - Toggle ArUco detection ON/OFF
  'd' - Toggle distance display
  'i' - Toggle marker ID display
  'g' - Grayscale mode
  'e' - Edge detection
  'o' - Original (no processing)
  'q' - Quit
  'h' - Show help

Usage:
  python3 aruco_viewer.py
"""

import cv2
import sys
import os
import yaml
import argparse

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from camera_processing import ArucoDetector, ProcessingMode, create_processor


def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    config_file = os.path.join(parent_dir, config_path)
    
    if not os.path.exists(config_file):
        print(f" Warning: Config file not found: {config_file}")
        print("Using default configuration.")
        return {
            'camera': {'url': 'http://10.22.227.47:4747/video', 'buffer_size': 1},
            'aruco': {'dictionary_type': 'DICT_6X6_250', 'marker_size_cm': 15.0, 'focal_length_px': 490.20},
            'display': {'window_width': 1280, 'window_height': 720, 'aruco_enabled': True, 
                       'show_distance': True, 'show_id': True, 'processing_mode': 'original'}
        }
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ Loaded configuration from: {config_path}")
        return config
    except Exception as e:
        print(f"✗ Error loading config file: {e}")
        print("Using default configuration.")
        return {
            'camera': {'url': 'http://10.22.227.47:4747/video', 'buffer_size': 1},
            'aruco': {'dictionary_type': 'DICT_6X6_250', 'marker_size_cm': 15.0, 'focal_length_px': 490.20},
            'display': {'window_width': 1280, 'window_height': 720, 'aruco_enabled': True, 
                       'show_distance': True, 'show_id': True, 'processing_mode': 'original'}
        }


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
    # Load configuration from YAML file
    config = load_config()
    
    # Extract configuration values
    CAMERA_URL = config['camera']['url']
    BUFFER_SIZE = config['camera']['buffer_size']
    
    ARUCO_DICT_TYPE = config['aruco']['dictionary_type']
    MARKER_SIZE_CM = config['aruco']['marker_size_cm']
    FOCAL_LENGTH_PX = config['aruco']['focal_length_px']
    
    WINDOW_WIDTH = config['display']['window_width']
    WINDOW_HEIGHT = config['display']['window_height']
    aruco_enabled = config['display']['aruco_enabled']
    show_distance = config['display']['show_distance']
    show_id = config['display']['show_id']
    
    # Map processing mode string to enum
    mode_map = {
        'original': ProcessingMode.ORIGINAL,
        'grayscale': ProcessingMode.GRAYSCALE,
        'edge_detection': ProcessingMode.EDGE_DETECTION
    }
    current_mode = mode_map.get(config['display']['processing_mode'], ProcessingMode.ORIGINAL)
    
    print_help()
    
    print(f"\nConfiguration:")
    print(f"  Camera URL: {CAMERA_URL}")
    print(f"  Marker size: {MARKER_SIZE_CM} cm")
    print(f"  Focal length: {FOCAL_LENGTH_PX} px")
    print(f"  ArUco dict: {ARUCO_DICT_TYPE}")
    
    print(f"\nConnecting to camera at {CAMERA_URL}...")
    cap = cv2.VideoCapture(CAMERA_URL)
    
    if not cap.isOpened():
        print(f" ERROR: Failed to connect to camera")
        print(f" URL: {CAMERA_URL}")
        return
    
    print("CONNECTED SUCCESSFULLY!")
    
    # Set buffer size for lower latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, BUFFER_SIZE)
    
    # Initialize ArUco detector
    aruco_detector = ArucoDetector(
        aruco_dict_type=ARUCO_DICT_TYPE,
        marker_size_cm=MARKER_SIZE_CM,
        focal_length_px=FOCAL_LENGTH_PX
    )
    
    # Initialize frame processor
    processor = create_processor(current_mode)
    
    # Window setup
    window_name = "Camera Viewer - ArUco Detection (Press 'h' for help)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, WINDOW_WIDTH, WINDOW_HEIGHT)
    
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
