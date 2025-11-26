# Camera Processing System with ArUco Detection

A modular camera processing system for real-time video streaming and ArUco marker detection with depth estimation.

## 🚀 Quick Start

### 1. Generate ArUco Markers
```bash
python3 utils/generate_aruco_markers.py
```

This will generate printable ArUco markers in the `aruco_markers/` directory.

### 2. Run Camera Viewer with ArUco Detection
```bash
python3 viewer/camera_viewer_aruco.py
```

**Keyboard Controls:**
- `a` - Toggle ArUco detection ON/OFF
- `d` - Toggle distance display
- `i` - Toggle marker ID display  
- `g` - Grayscale mode
- `e` - Edge detection
- `o` - Original (no processing)
- `h` - Show help
- `q` - Quit

## 📁 Project Structure

```
espCamFeature/
├── camera_processing/          # Core processing modules
│   ├── __init__.py
│   ├── aruco_detector.py       # ArUco marker detection & depth estimation
│   ├── frame_processor.py      # Image processing filters
│   └── esp_camera_client.py    # Camera stream client (legacy)
│
├── viewer/                     # Viewer applications
│   ├── camera_viewer_aruco.py  # ✨ Main viewer with ArUco detection
│   ├── simple_opencv_viewer.py # Simple OpenCV viewer
│   ├── simple_camera_viewer.py # Custom MJPEG viewer
│   └── simple_capture_example.py
│
├── utils/                      # Utility scripts
│   └── generate_aruco_markers.py # Generate printable ArUco markers
│
├── tests/                      # Test & diagnostic scripts
│   ├── diagnose_camera.py
│   ├── test_esp_connection.py
│   └── find_camera_url.py
│
├── docs/                       # Documentation
│   ├── SETUP_GUIDE.md
│   ├── CURRENT_STATUS.md
│   └── README_SOLUTION.md
│
├── cam_server_page/            # Streamlit web app (optional)
│   ├── app_opencv.py
│   └── app.py
│
├── CameraWebServer/            # ESP32-CAM Arduino code (optional)
│   └── CameraWebServer.ino
│
└── requirements.txt
```

## 🎯 Features

### ArUco Marker Detection
- Real-time marker detection
- Distance/depth estimation based on marker size
- Multiple ArUco dictionary support (4x4, 5x5, 6x6, 7x7)
- Marker ID display
- Camera pose estimation (with calibration)

### Image Processing
- Grayscale conversion
- Edge detection (Canny)
- Gaussian blur
- Sharpen filter
- Brightness/contrast adjustment
- Binary threshold

### Camera Support
- DroidCam (Android/iOS camera apps)
- IP Webcam
- ESP32-CAM (future support)
- Any MJPEG/HTTP video stream

## 📝 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- opencv-python (with contrib for ArUco)
- numpy

### 2. Configure Camera URL

Edit `viewer/camera_viewer_aruco.py`:
```python
CAMERA_URL = "http://YOUR_CAMERA_IP:PORT/video"
MARKER_SIZE_CM = 10.0  # Real size of your printed marker
```

### 3. Camera Calibration (Optional, for better accuracy)

For precise distance estimation, calibrate your camera:
```python
from camera_processing import ArucoDetector
import numpy as np

# Your camera calibration matrix
camera_matrix = np.array([
    [fx, 0, cx],
    [0, fy, cy],
    [0, 0, 1]
])

detector = ArucoDetector(
    marker_size_cm=10.0,
    camera_matrix=camera_matrix,
    dist_coeffs=dist_coeffs
)
```

## 🔬 ArUco Depth Estimation

### How It Works

The distance to an ArUco marker is estimated using:

```
Distance = (Real_Marker_Size × Focal_Length) / Perceived_Marker_Size_in_Pixels
```

### Steps:
1. **Print markers**: Use `utils/generate_aruco_markers.py`
2. **Measure size**: Measure the printed marker in cm
3. **Update config**: Set `MARKER_SIZE_CM` in the viewer
4. **Run**: The viewer will show real-time distance estimates

### Improving Accuracy:
- Use camera calibration for best results
- Keep markers flat and well-lit
- Avoid glare and shadows
- Use larger markers for distant detection
- Calibrate focal length for your specific camera

## 💡 Usage Examples

### Basic ArUco Detection
```python
from camera_processing import ArucoDetector
import cv2

# Initialize detector
detector = ArucoDetector(
    aruco_dict_type="DICT_6X6_250",
    marker_size_cm=10.0,
    focal_length_px=1000.0
)

# Capture frame
cap = cv2.VideoCapture("http://10.22.209.148:4747/video")
ret, frame = cap.read()

# Detect markers
corners, ids, rejected = detector.detect(frame)

# Draw detections
frame = detector.draw_detections(frame, corners, ids)

# Get marker info
markers_info = detector.get_marker_info(corners, ids)
for marker in markers_info:
    print(f"Marker {marker['id']}: {marker['distance_cm']:.1f}cm away")
```

### Generate Custom Markers
```python
from camera_processing import save_aruco_marker

# Generate marker ID 42
save_aruco_marker(
    marker_id=42,
    filename="my_marker.png",
    marker_size=400,
    aruco_dict_type="DICT_6X6_250"
)
```

### With Image Processing
```python
from camera_processing import ArucoDetector, create_processor, ProcessingMode

detector = ArucoDetector(marker_size_cm=10.0)
processor = create_processor(ProcessingMode.GRAYSCALE)

# Process and detect
processed_frame = processor.process(frame)
corners, ids, _ = detector.detect(processed_frame)
```

## 🛠️ Configuration

### Camera URL Examples:
- **DroidCam**: `http://10.22.209.148:4747/video`
- **IP Webcam**: `http://192.168.1.100:8080/video`
- **ESP32-CAM**: `http://192.168.1.100/stream`

### ArUco Dictionary Types:
- `DICT_4X4_50` - Good for small markers, fewer IDs
- `DICT_6X6_250` - **Recommended** - good balance
- `DICT_7X7_1000` - More unique IDs, larger markers

### Marker Sizes:
- **Small (5-10cm)**: Good for close range (< 1m)
- **Medium (10-20cm)**: General purpose (1-3m)
- **Large (20-50cm)**: Long range (3-10m)

## 📊 Performance Tips

1. **Lower latency**: Set buffer size to 1
   ```python
   cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
   ```

2. **Better detection**: Use good lighting and avoid shadows

3. **Faster processing**: Use grayscale instead of color

4. **Multiple markers**: Use unique IDs for each marker

## 🐛 Troubleshooting

### "Failed to connect to camera"
- Check camera URL is correct
- Ensure camera app is running
- Verify same WiFi network

### "No markers detected"
- Ensure good lighting
- Check marker is printed clearly
- Verify correct ArUco dictionary type
- Marker should be flat and visible

### "Inaccurate distance"
- Measure marker size accurately
- Adjust `MARKER_SIZE_CM` value
- Consider camera calibration
- Adjust `FOCAL_LENGTH_PX` value

## 📚 Documentation

- **Setup Guide**: `docs/SETUP_GUIDE.md`
- **Current Status**: `docs/CURRENT_STATUS.md`
- **Solution Details**: `docs/README_SOLUTION.md`

## 🎓 Learning Resources

### ArUco Markers:
- Official OpenCV ArUco documentation
- Camera calibration tutorials
- Pose estimation guides

### Depth Estimation:
- Pinhole camera model
- Focal length calculation
- Camera calibration techniques

## 🤝 Contributing

Feel free to extend the system with:
- Additional image processing filters
- More marker detection algorithms
- Camera calibration tools
- 3D pose visualization

## 📄 License

Open source - use for educational and project purposes.

---

**Happy marker detecting! 📷✨**
