#!/usr/bin/env python3
"""
Tool to find the correct camera stream URL by testing common endpoints.
"""

import requests
import sys

def test_url(base_url, port, endpoints):
    """Test different endpoints to find the video stream."""
    print(f"\nTesting camera at {base_url}:{port}")
    print("=" * 60)

    working_urls = []

    for endpoint in endpoints:
        url = f"http://{base_url}:{port}{endpoint}"
        try:
            print(f"\nTesting: {url}")
            response = requests.get(url, stream=True, timeout=3)

            content_type = response.headers.get('Content-Type', '')
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {content_type}")

            if response.status_code == 200:
                if 'multipart' in content_type.lower() or 'mjpeg' in content_type.lower():
                    print(f"  ✅ FOUND MJPEG STREAM!")
                    working_urls.append(url)
                elif 'image/jpeg' in content_type.lower():
                    print(f"  ✅ FOUND JPEG SNAPSHOT!")
                    working_urls.append(url)
                elif 'text/html' in content_type.lower():
                    print(f"  ⚠️  HTML page (not a video stream)")
                else:
                    print(f"  ⚠️  Unknown content type")

            response.close()

        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Connection refused")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    return working_urls

def main():
    # Common camera stream endpoints
    endpoints = [
        '/video',           # IP Webcam HTML page
        '/videofeed',       # IP Webcam MJPEG stream
        '/mjpegfeed',       # Alternative MJPEG
        '/shot.jpg',        # IP Webcam snapshot
        '/photoaf.jpg',     # IP Webcam autofocus snapshot
        '/stream',          # ESP32-CAM
        '/cam-hi.jpg',      # Some cameras
        '/cam-lo.jpg',      # Some cameras
        '/mjpg/video.mjpg', # Some cameras
        '/axis-cgi/mjpg/video.cgi',  # Axis cameras
    ]

    if len(sys.argv) >= 2:
        ip = sys.argv[1]
    else:
        ip = "10.22.209.148"

    if len(sys.argv) >= 3:
        port = sys.argv[2]
    else:
        port = "4747"

    print("\n" + "=" * 60)
    print("CAMERA STREAM URL FINDER")
    print("=" * 60)
    print(f"IP Address: {ip}")
    print(f"Port: {port}")

    working_urls = test_url(ip, port, endpoints)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if working_urls:
        print("\n✅ Found working URLs:")
        for url in working_urls:
            print(f"  - {url}")
        print(f"\nUse this URL in your viewer:")
        print(f"  {working_urls[0]}")
    else:
        print("\n❌ No working video stream URLs found")
        print("\nTroubleshooting:")
        print("  1. Make sure your camera app is running")
        print("  2. Check the IP address and port")
        print("  3. Make sure you're on the same network")
        print("  4. Check the camera app settings for the correct endpoint")

if __name__ == "__main__":
    main()
