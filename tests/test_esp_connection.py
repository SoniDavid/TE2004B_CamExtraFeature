#!/usr/bin/env python3
"""
Test script to verify ESP32-CAM connection and camera_processing module.
Run this first to ensure your ESP32-CAM is accessible.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("ESP32-CAM Connection Test")
print("=" * 60)

# Test 1: Import camera_processing module
print("\n[1/4] Testing camera_processing imports...")
try:
    from camera_processing import ESPCameraClient, FrameProcessor, ProcessingMode, create_processor
    print("✓ Successfully imported camera_processing modules")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test 2: Get ESP IP from user
print("\n[2/4] ESP32-CAM IP Configuration")
print("Have you uploaded the .ino code to your ESP32-CAM? (yes/no)")
uploaded = input(">>> ").strip().lower()

if uploaded != "yes":
    print("\n⚠️  Please upload CameraWebServer.ino to your ESP32-CAM first!")
    print("Steps:")
    print("  1. Open Arduino IDE")
    print("  2. Open CameraWebServer/CameraWebServer.ino")
    print("  3. Update WiFi credentials in the .ino file:")
    print("     const char *ssid = \"YOUR_WIFI_NAME\";")
    print("     const char *password = \"YOUR_WIFI_PASSWORD\";")
    print("  4. Upload to ESP32-CAM")
    print("  5. Open Serial Monitor (115200 baud)")
    print("  6. Note the IP address printed (e.g., 192.168.1.100)")
    sys.exit(0)

print("\nEnter the ESP32-CAM IP address from Serial Monitor")
print("(Press Enter to use default: 192.168.1.100)")
esp_ip = input("ESP IP >>> ").strip()
if not esp_ip:
    esp_ip = "192.168.1.100"

# Test 3: Connect to ESP32-CAM
print(f"\n[3/4] Connecting to ESP32-CAM at {esp_ip}...")
client = ESPCameraClient(esp_ip)

if client.connect(timeout=10):
    print(f"✓ Successfully connected to ESP32-CAM at {esp_ip}")
else:
    print(f"✗ Failed to connect to ESP32-CAM at {esp_ip}")
    print("\nTroubleshooting:")
    print("  - Ensure ESP32-CAM is powered on and running")
    print("  - Check that your computer is on the same WiFi network")
    print("  - Verify the IP address is correct from Serial Monitor")
    print(f"  - Try opening http://{esp_ip} in your web browser")
    sys.exit(1)

# Test 4: Capture a test frame
print("\n[4/4] Capturing test frame...")
try:
    frame = client.get_frame()
    if frame is not None:
        height, width = frame.shape[:2]
        print(f"✓ Successfully captured frame: {width}x{height}")
        
        # Test processing
        processor = create_processor(ProcessingMode.ORIGINAL)
        processed = processor.process(frame)
        print("✓ Successfully processed frame")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Your ESP32-CAM setup is working correctly!")
        print("=" * 60)
        print(f"\nYou can now run the Streamlit app with:")
        print(f"  cd cam_server_page")
        print(f"  streamlit run app.py")
        print(f"\nThen enter the IP address: {esp_ip}")
        
    else:
        print("✗ Received None frame from ESP32-CAM")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Error capturing frame: {e}")
    sys.exit(1)

finally:
    client.disconnect()
    print("\nDisconnected from ESP32-CAM")
