#!/usr/bin/env python3
"""
Quick diagnostic tool for your camera stream issue.
"""

import cv2
import requests
import sys

print("="*70)
print("CAMERA STREAM DIAGNOSTIC TOOL")
print("="*70)

# The URL from your simple_camera_viewer.py
test_url = "http://10.22.209.148:4747/video"
print(f"\nTesting URL: {test_url}")
print("-"*70)

# Test 1: Can we reach the server at all?
print("\n[Test 1] Checking if server is reachable...")
try:
    response = requests.get(f"http://10.22.209.148:4747/", timeout=3)
    print(f"✓ Server is reachable!")
    print(f"  Status: {response.status_code}")
    print(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")
except requests.exceptions.ConnectionError:
    print("✗ CONNECTION REFUSED - Server is not running or not reachable")
    print("\n**SOLUTION:**")
    print("  This IP:Port looks like a phone camera app (DroidCam/IP Webcam)")
    print("  Make sure:")
    print("  1. The app is open and running on your phone")
    print("  2. The phone is connected to the same WiFi network")
    print("  3. The app shows this exact IP address")
    print("  4. WiFi is turned ON on the phone (not mobile data)")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 2: Try the specific video endpoint
print("\n[Test 2] Checking video endpoint...")
try:
    response = requests.get(test_url, stream=True, timeout=5)
    content_type = response.headers.get('Content-Type', 'unknown')
    print(f"  Status: {response.status_code}")
    print(f"  Content-Type: {content_type}")
    
    if 'text/html' in content_type:
        print("⚠️  This returns HTML, not video!")
        print("  Reading first 200 chars...")
        chunk = response.content[:200].decode('utf-8', errors='ignore')
        print(f"  {chunk}")
        
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Try OpenCV VideoCapture
print("\n[Test 3] Testing with OpenCV VideoCapture...")
cap = cv2.VideoCapture(test_url)

if cap.isOpened():
    print("✓ VideoCapture opened")
    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"✓ SUCCESS! Got frame: {frame.shape}")
        print("\n" + "="*70)
        print("GOOD NEWS: Your camera is working!")
        print("="*70)
        print("\nThe issue is that simple_camera_viewer.py uses a custom")
        print("CameraStreamClient that expects MJPEG format, but OpenCV")
        print("VideoCapture works fine with your stream.")
        print("\nSOLUTION: Use the simple_opencv_viewer.py script instead!")
    else:
        print("✗ VideoCapture opened but couldn't read frame")
else:
    print("✗ VideoCapture failed to open")

cap.release()

# Test common alternative URLs
print("\n[Test 4] Trying alternative URLs...")
alternatives = [
    "http://10.22.209.148:4747/mjpegfeed",
    "http://10.22.209.148:4747/cam/1/stream",
    "http://10.22.209.148:8080/video",
]

for alt_url in alternatives:
    try:
        cap = cv2.VideoCapture(alt_url)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✓ {alt_url} WORKS!")
            cap.release()
    except:
        pass

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)
print("\nYour current URL appears to be from a phone camera app.")
print("The best approach is:")
print("\n1. Use simple_opencv_viewer.py (uses cv2.VideoCapture)")
print("   OR")
print("2. Get an ESP32-CAM and use the ESP camera features")
print("\nTo use ESP32-CAM:")
print("  - Upload CameraWebServer.ino to ESP32-CAM")
print("  - Get the IP from Serial Monitor (e.g., 192.168.1.100)")
print("  - Use http://192.168.1.100/stream")
