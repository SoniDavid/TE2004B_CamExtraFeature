#!/usr/bin/env python3
"""
Simple camera stream viewer without Streamlit.
Press keys to switch processing modes:
- 'o': Original (no processing)
- 'g': Grayscale
- 'e': Edge Detection
- 'b': Blur
- 's': Sharpen
- 'r': Brightness
- 'c': Contrast
- 't': Threshold
- 'q': Quit
- '+/-': Adjust parameters for current mode
"""

import cv2
import sys
import os

# Add parent directory to path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from camera_processing import CameraStreamClient, ProcessingMode, create_processor

def main():
    # Camera stream URL - change this to your camera IP
    stream_url = "http://10.22.209.148:4747/video"

    # Connect to camera
    print(f"Connecting to camera at {stream_url}...")
    client = CameraStreamClient(stream_url)

    if not client.connect():
        print(f"ERROR: Failed to connect to camera at {stream_url}")
        print("Please check:")
        print("1. The camera is on and streaming")
        print("2. The IP address is correct")
        print("3. Your computer is on the same network")
        return

    print("✅ Connected successfully!")
    print("\nControls:")
    print("  'o' - Original (no processing)")
    print("  'g' - Grayscale")
    print("  'e' - Edge Detection")
    print("  'b' - Blur")
    print("  's' - Sharpen")
    print("  'r' - Brightness")
    print("  'c' - Contrast")
    print("  't' - Threshold")
    print("  '+' - Increase parameter")
    print("  '-' - Decrease parameter")
    print("  'q' - Quit")
    print("\nPress any key in the video window to start...")

    # Initialize processor
    current_mode = ProcessingMode.ORIGINAL
    processor = create_processor(current_mode)

    # Parameters for different modes
    edge_threshold1 = 100
    edge_threshold2 = 200
    blur_ksize = 5
    brightness_value = 30
    contrast_alpha = 1.5
    threshold_value = 127

    frame_count = 0
    window_name = "Camera Stream - Press 'q' to quit"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    while True:
        # Get frame from camera
        frame = client.get_frame()

        if frame is None:
            print("Failed to get frame from camera")
            break

        # Process the frame
        processed_frame = processor.process(frame)

        # Add info overlay
        info_text = f"Mode: {current_mode.value} | Frame: {frame_count}"

        # Add mode-specific parameter info
        if current_mode == ProcessingMode.EDGE_DETECTION:
            info_text += f" | T1: {edge_threshold1}, T2: {edge_threshold2}"
        elif current_mode == ProcessingMode.BLUR:
            info_text += f" | Kernel: {blur_ksize}"
        elif current_mode == ProcessingMode.BRIGHTNESS:
            info_text += f" | Value: {brightness_value}"
        elif current_mode == ProcessingMode.CONTRAST:
            info_text += f" | Alpha: {contrast_alpha:.1f}"
        elif current_mode == ProcessingMode.THRESHOLD:
            info_text += f" | Threshold: {threshold_value}"

        # Draw text on frame
        cv2.putText(processed_frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display the frame
        cv2.imshow(window_name, processed_frame)

        frame_count += 1

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("\nQuitting...")
            break

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
            processor = create_processor(current_mode, threshold1=edge_threshold1, threshold2=edge_threshold2)
            print(f"Switched to: {current_mode.value}")

        elif key == ord('b'):
            current_mode = ProcessingMode.BLUR
            processor = create_processor(current_mode, ksize=blur_ksize)
            print(f"Switched to: {current_mode.value}")

        elif key == ord('s'):
            current_mode = ProcessingMode.SHARPEN
            processor = create_processor(current_mode)
            print(f"Switched to: {current_mode.value}")

        elif key == ord('r'):
            current_mode = ProcessingMode.BRIGHTNESS
            processor = create_processor(current_mode, value=brightness_value)
            print(f"Switched to: {current_mode.value}")

        elif key == ord('c'):
            current_mode = ProcessingMode.CONTRAST
            processor = create_processor(current_mode, alpha=contrast_alpha)
            print(f"Switched to: {current_mode.value}")

        elif key == ord('t'):
            current_mode = ProcessingMode.THRESHOLD
            processor = create_processor(current_mode, thresh_value=threshold_value)
            print(f"Switched to: {current_mode.value}")

        # Adjust parameters with +/-
        elif key == ord('+') or key == ord('='):
            if current_mode == ProcessingMode.EDGE_DETECTION:
                edge_threshold1 = min(255, edge_threshold1 + 10)
                edge_threshold2 = min(255, edge_threshold2 + 10)
                processor = create_processor(current_mode, threshold1=edge_threshold1, threshold2=edge_threshold2)
                print(f"Threshold: {edge_threshold1}/{edge_threshold2}")
            elif current_mode == ProcessingMode.BLUR:
                blur_ksize = min(15, blur_ksize + 2)
                processor = create_processor(current_mode, ksize=blur_ksize)
                print(f"Blur kernel: {blur_ksize}")
            elif current_mode == ProcessingMode.BRIGHTNESS:
                brightness_value = min(100, brightness_value + 10)
                processor = create_processor(current_mode, value=brightness_value)
                print(f"Brightness: {brightness_value}")
            elif current_mode == ProcessingMode.CONTRAST:
                contrast_alpha = min(3.0, contrast_alpha + 0.1)
                processor = create_processor(current_mode, alpha=contrast_alpha)
                print(f"Contrast: {contrast_alpha:.1f}")
            elif current_mode == ProcessingMode.THRESHOLD:
                threshold_value = min(255, threshold_value + 10)
                processor = create_processor(current_mode, thresh_value=threshold_value)
                print(f"Threshold: {threshold_value}")

        elif key == ord('-') or key == ord('_'):
            if current_mode == ProcessingMode.EDGE_DETECTION:
                edge_threshold1 = max(0, edge_threshold1 - 10)
                edge_threshold2 = max(0, edge_threshold2 - 10)
                processor = create_processor(current_mode, threshold1=edge_threshold1, threshold2=edge_threshold2)
                print(f"Threshold: {edge_threshold1}/{edge_threshold2}")
            elif current_mode == ProcessingMode.BLUR:
                blur_ksize = max(1, blur_ksize - 2)
                processor = create_processor(current_mode, ksize=blur_ksize)
                print(f"Blur kernel: {blur_ksize}")
            elif current_mode == ProcessingMode.BRIGHTNESS:
                brightness_value = max(-100, brightness_value - 10)
                processor = create_processor(current_mode, value=brightness_value)
                print(f"Brightness: {brightness_value}")
            elif current_mode == ProcessingMode.CONTRAST:
                contrast_alpha = max(0.5, contrast_alpha - 0.1)
                processor = create_processor(current_mode, alpha=contrast_alpha)
                print(f"Contrast: {contrast_alpha:.1f}")
            elif current_mode == ProcessingMode.THRESHOLD:
                threshold_value = max(0, threshold_value - 10)
                processor = create_processor(current_mode, thresh_value=threshold_value)
                print(f"Threshold: {threshold_value}")

    # Cleanup
    client.disconnect()
    cv2.destroyAllWindows()
    print(f"\nTotal frames processed: {frame_count}")
    print("Goodbye!")

if __name__ == "__main__":
    main()
