#!/usr/bin/env python3
"""
Simple camera stream viewer using OpenCV's built-in VideoCapture.
Press 'q' to quit.
"""

import cv2
import sys

def main():
    # Camera stream URL
    stream_url = "http://10.22.209.148:4747/video"

    print(f"Connecting to camera at {stream_url}...")

    # Use OpenCV's VideoCapture which handles MJPEG streams natively
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print(f"ERROR: Failed to open camera stream at {stream_url}")
        print("Please check:")
        print("1. The camera is on and streaming")
        print("2. The IP address is correct")
        print("3. Your computer is on the same network")
        return

    print("✅ Connected successfully!")
    print("\nPress 'q' in the video window to quit")

    frame_count = 0
    window_name = "Camera Stream - Press 'q' to quit"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

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
