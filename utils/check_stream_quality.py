#!/usr/bin/env python3
"""
Check DroidCam Stream Quality
Shows the actual resolution and properties of your camera stream
"""

import cv2

def check_stream_quality(stream_url):
    """
    Check and display the quality parameters of a camera stream.

    Args:
        stream_url: The URL of the camera stream
    """
    print("="*60)
    print("CAMERA STREAM QUALITY CHECK")
    print("="*60)

    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print(f"\nFailed to connect to: {stream_url}")
        return

    print(f"\n✓ Connected to: {stream_url}")

    # Get stream properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

    # Convert fourcc to string
    fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

    print("\nStream Properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  Aspect Ratio: {width/height:.2f}")
    print(f"  FPS: {fps}")
    print(f"  Codec (FourCC): {fourcc_str}")

    # Read a test frame
    ret, frame = cap.read()

    if ret and frame is not None:
        print(f"\nFrame Details:")
        print(f"  Frame shape: {frame.shape}")
        print(f"  Color channels: {frame.shape[2] if len(frame.shape) > 2 else 1}")
        print(f"  Data type: {frame.dtype}")
        print(f"  Frame size: {frame.nbytes / 1024:.2f} KB")

        # Estimate quality
        total_pixels = width * height
        megapixels = total_pixels / 1_000_000

        print(f"\nQuality Assessment:")
        print(f"  Total pixels: {total_pixels:,}")
        print(f"  Megapixels: {megapixels:.2f} MP")

        if width <= 640:
            quality_tier = "SD (Standard Definition)"
        elif width <= 1280:
            quality_tier = "HD Ready (720p)"
        elif width <= 1920:
            quality_tier = "Full HD (1080p)"
        else:
            quality_tier = "Ultra HD"

        print(f"  Quality Tier: {quality_tier}")

        # Check if free or paid version
        if width <= 640 and height <= 480:
            print("\n Note: This appears to be DroidCam free version (480p limit)")
            print("   Consider DroidCam X (paid) for 720p/1080p")

    else:
        print("\n Failed to read frame from stream")

    cap.release()

    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    print("\n1. In DroidCam App:")
    print("   • Check Video Quality setting (Low/Medium/High)")
    print("   • Ensure good WiFi signal")
    print("   • Close other apps using camera")
    print("\n2. Network:")
    print("   • Use 5GHz WiFi if available (less interference)")
    print("   • Stay close to WiFi router")
    print("   • Avoid network congestion")
    print("\n3. Alternative:")
    print("   • Try IP Webcam app (may offer different quality options)")
    print("   • Use USB connection with DroidCam (better quality)")


if __name__ == "__main__":
    # Default DroidCam URL
    CAMERA_URL = "http://10.22.209.148:4747/video"

    print("\nChecking DroidCam stream quality...")
    print(f"URL: {CAMERA_URL}\n")

    check_stream_quality(CAMERA_URL)

    print("\n To check a different camera, edit CAMERA_URL in this script")
