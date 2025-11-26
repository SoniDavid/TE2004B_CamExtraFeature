#!/usr/bin/env python3
"""
Simple example: Retrieve frames from ESP32-CAM, process them, and save.
This demonstrates the flow: ESP → Processing → Output
"""

import sys
import cv2
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from camera_processing import ESPCameraClient, FrameProcessor, ProcessingMode, create_processor


def main():
    # Step 1: Configure ESP32-CAM IP
    ESP_IP = "192.168.1.100"  # Change this to your ESP32-CAM's IP
    
    print(f"Connecting to ESP32-CAM at {ESP_IP}...")
    
    # Step 2: Create client and connect
    client = ESPCameraClient(ESP_IP)
    
    if not client.connect():
        print("Failed to connect to ESP32-CAM!")
        print(f"Make sure your ESP32-CAM is running and accessible at http://{ESP_IP}")
        return
    
    print("Connected successfully!")
    
    # Step 3: Create processor with edge detection
    processor = create_processor(
        mode=ProcessingMode.EDGE_DETECTION,
        threshold1=100,
        threshold2=200
    )
    
    # Step 4: Capture and process a frame
    print("Capturing frame...")
    frame = client.get_frame()
    
    if frame is None:
        print("Failed to capture frame!")
        client.disconnect()
        return
    
    print(f"Captured frame: {frame.shape}")
    
    # Step 5: Process the frame
    processed_frame = processor.process(frame)
    
    # Step 6: Save both original and processed frames
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    cv2.imwrite(str(output_dir / "original.jpg"), frame)
    cv2.imwrite(str(output_dir / "processed.jpg"), processed_frame)
    
    print(f"Saved frames to {output_dir}/")
    print("  - original.jpg")
    print("  - processed.jpg")
    
    # Step 7: Disconnect
    client.disconnect()
    print("Done!")


if __name__ == "__main__":
    main()
