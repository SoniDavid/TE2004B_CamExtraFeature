#!/usr/bin/env python3
"""
Simple camera stream viewer using OpenCV's built-in VideoCapture.
Loads configuration from config.yaml file.
Press 'q' to quit.
"""

import cv2
import sys
import os
import yaml


def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    # Get the parent directory (project root)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    config_file = os.path.join(parent_dir, config_path)
    
    if not os.path.exists(config_file):
        print(f"Warning: Config file not found: {config_file}")
        print("Using default configuration.")
        return {
            'camera': {'url': 'http://10.22.227.47:4747/video', 'buffer_size': 1},
            'display': {'window_width': 1280, 'window_height': 720}
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
            'display': {'window_width': 1280, 'window_height': 720}
        }


def main():
    # Load configuration from YAML file
    config = load_config()
    
    # Extract configuration values
    stream_url = config['camera']['url']
    buffer_size = config['camera']['buffer_size']
    window_width = config['display']['window_width']
    window_height = config['display']['window_height']
    
    print(f"\nConfiguration:")
    print(f"  Camera URL: {stream_url}")
    
    print(f"\nConnecting to camera at {stream_url}...")

    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print(f"✗ ERROR: Failed to open camera stream at {stream_url}")
        print("Please check:")
        print("1. The camera is on and streaming")
        print("2. The IP address is correct")
        print("3. Your computer is on the same network")
        return

    print("✓ Connected successfully")
    print("\nPress 'q' in the video window to quit")
    
    # Set buffer size for lower latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)

    frame_count = 0
    window_name = "Camera Stream - Press 'q' to quit"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, window_width, window_height)

    while True:
        # Read frame from camera
        ret, frame = cap.read()

        if not ret or frame is None:
            print(f"Failed to read frame (frame count: {frame_count})")
            # Try to reconnect
            print("Attempting to reconnect...")
            cap.release()
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                print("Failed to reconnect. Exiting...")
                break
            continue

        frame_count += 1

        # Add frame counter overlay
        info_text = f"Frame: {frame_count}"
        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display the frame
        cv2.imshow(window_name, frame)

        # Handle keyboard input (1ms delay)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\nQuitting...")
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal frames processed: {frame_count}")
    print("Goodbye!")

if __name__ == "__main__":
    main()
