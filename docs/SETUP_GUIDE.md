# Camera Setup Guide

This guide explains how to set up and use DroidCam or other camera sources with Python processing and ArUco marker detection.

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   DroidCam      │ HTTP │  camera_processing│      │  viewer apps    │
│  (Phone Camera) │─────>│   (Python)        │─────>│   (OpenCV)      │
│                 │      │                   │      │                 │
│ • Captures video│      │ • Fetches frames  │      │ • Live display  │
│ • WiFi stream   │      │ • ArUco detection │      │ • ArUco overlay │
│ • /video        │      │ • Processes images│      │ • Depth info    │
│                 │      │ • Depth estimation│      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

## Setup Steps

### 1. Setup Camera Source (DroidCam)

1. **Install DroidCam on your phone:**
   - Android: Install from Google Play Store
   - iOS: Install from App Store

2. **Connect to WiFi:**
   - Ensure your phone and computer are on the **same WiFi network**

3. **Start DroidCam:**
   - Open DroidCam app on your phone
   - Note the WiFi IP address shown, e.g.: `http://10.22.209.148:4747`

4. **Test Connection:**
   - Open the IP address in your browser
   - You should see a web interface with video controls
   - The video stream URL will be: `http://YOUR_IP:4747/video`

### 2. Test Camera Connection

Run the diagnostic script to verify everything is working:

```bash
python3 tests/diagnose_camera.py
```

This will:
- Check Python imports
- Test connection to your camera
- Capture a test frame
- Verify OpenCV can read the stream

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- streamlit - Web interface
- opencv-python - Image processing
- numpy - Array operations
- Pillow - Image handling
- requests - HTTP client for ESP32-CAM

### 4. Try the Simple Example

Test frame capture and processing:

### 4. Generate ArUco Markers

Create printable markers for detection:

```bash
python3 utils/generate_aruco_markers.py
```

This will generate markers in the `aruco_markers/` folder.

### 5. Run Camera Viewers

**Simple viewer (no ArUco):**
```bash
python3 viewer/camera_viewer.py
```

**ArUco detection viewer:**
```bash
python3 viewer/aruco_viewer.py
```

Update the camera URL in the viewer files before running:
```python
CAMERA_URL = "http://YOUR_IP:4747/video"
```

## Project Structure

```
espCamFeature/
├── camera_processing/        # Python processing module
│   ├── __init__.py           # Module exports
│   ├── aruco_detector.py     # ArUco marker detection & depth
│   └── image_filters.py      # Image processing pipeline
│
├── viewer/                   # Viewer applications
│   ├── aruco_viewer.py       # ArUco detection viewer
│   └── camera_viewer.py      # Simple camera viewer
│
├── utils/                    # Utility scripts
│   └── generate_aruco_markers.py
│
├── tests/                    # Test scripts
│   └── diagnose_camera.py
│
├── cam_server_page/          # Streamlit web app (optional)
│   ├── app_opencv.py
│   └── app.py
│
├── aruco_markers/            # Generated ArUco markers
└── requirements.txt          # Python dependencies
```

## How It Works

### 1. Camera Source (DroidCam)

DroidCam on your phone:
- Streams video over WiFi
- Provides HTTP endpoint at `/video`
- Works with OpenCV's VideoCapture

### 2. camera_processing (Python Module)

**ArucoDetector**: Detects ArUco markers and estimates distance
```python
from camera_processing import ArucoDetector
import cv2

detector = ArucoDetector(marker_size_cm=10.0)
cap = cv2.VideoCapture("http://10.22.209.148:4747/video")

ret, frame = cap.read()
corners, ids, rejected = detector.detect(frame)
markers_info = detector.get_marker_info(corners, ids)
```

**FrameProcessor**: Processes images with various filters
```python
from camera_processing import FrameProcessor, ProcessingMode, create_processor

# Use predefined processor
processor = create_processor(ProcessingMode.EDGE_DETECTION, threshold1=100, threshold2=200)
processed = processor.process(frame)

# Build custom pipeline
processor = FrameProcessor()
processor.add_processing_step(convert_to_grayscale)
processor.add_processing_step(apply_blur)
processed = processor.process(frame)
```

### 3. Viewer Applications

The viewers provide:
- Live camera streaming with OpenCV
- Real-time ArUco marker detection
- Distance estimation overlay
- Multiple processing modes (grayscale, edge detection, etc.)

## Troubleshooting

### "Failed to connect to camera"

**Check:**
1. DroidCam app is running on your phone
2. Phone and computer are on the same WiFi network
3. IP address is correct (check DroidCam app display)
4. Try accessing the IP in a web browser
5. Firewall isn't blocking the connection

### "Import error" in Python

**Fix:**
```bash
# Make sure you're in the project root directory
cd /home/soni/reto_embebidos/espCamFeature

# Install dependencies
pip install -r requirements.txt

# Test imports
python3 tests/diagnose_camera.py
```

### "No markers detected"

**Check:**
1. Camera module is properly connected
2. Correct board configuration in `board_config.h`
3. Sufficient power supply (camera needs good power)
4. Try pressing the reset button

### Slow frame rate

**Optimize:**
1. Reduce frame size in .ino file:
   ```cpp
   s->set_framesize(s, FRAMESIZE_QVGA);  // Smaller = faster
   ```
2. Increase JPEG quality (lower number):
   ```cpp
   config.jpeg_quality = 10;  // 0-63, lower = better quality
   ```
3. Use simpler processing modes (Original or Grayscale)

## Understanding IP Addresses

**Important:** The ESP32-CAM does NOT create "localhost"!

- **localhost** (`127.0.0.1`) = Your computer
- **ESP32-CAM IP** (e.g., `192.168.1.100`) = The ESP device on your WiFi network

When you upload the .ino code:
1. ESP32-CAM connects to your WiFi
2. Your router assigns it an IP address
3. This IP is printed in the Serial Monitor
4. You use this IP to connect from Python

## Advanced Usage

### Custom Processing Pipeline

```python
from camera_processing import FrameProcessor
import cv2

processor = FrameProcessor()

# Add custom function
def my_custom_filter(frame):
    # Your processing code
    return cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

processor.add_processing_step(my_custom_filter)
processed = processor.process(frame)
```

### Continuous Stream Processing

```python
client = ESPCameraClient("192.168.1.100")
client.connect()

try:
    while True:
        frame = client.get_frame()
        if frame is not None:
            processed = processor.process(frame)
            cv2.imshow("Processed", processed)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
finally:
    client.disconnect()
    cv2.destroyAllWindows()
```

## Next Steps

1. ✅ Upload .ino code to ESP32-CAM
2. ✅ Get ESP IP from Serial Monitor
3. ✅ Run `python test_esp_connection.py`
4. ✅ Try `python simple_capture_example.py`
5. ✅ Launch Streamlit app: `cd cam_server_page && streamlit run app.py`
6. 🎉 Enjoy your ESP32-CAM system!

## Support

If you encounter issues:
1. Check Serial Monitor output from ESP32-CAM
2. Verify network connectivity
3. Test ESP IP in web browser first
4. Run test_esp_connection.py for diagnostics
