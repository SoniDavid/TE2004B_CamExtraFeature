# Camera Processing System with ArUco Detection

A modular camera processing system for real-time video streaming, ArUco marker detection with depth estimation, and autonomous robot navigation.

## Quick Start

### 1. Configure Settings

Edit `config.yaml` with your camera URL settings:

### 2. Generate ArUco Markers
```bash
python3 utils/generate_aruco_markers.py
```

This will generate printable ArUco markers in the `aruco_markers/` directory.

### 3. Run Camera Viewer with ArUco Detection
```bash
python3 viewer/aruco_viewer.py
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

### 4. Run Autonomous Navigation (TE2004B Robot)
```bash
python3 aruco_navigation.py
```

Autonomous navigation system that controls the TE2004B robot car based on ArUco marker detection.

**Features:**
- Maintains target distance from marker (default: 25cm)
- Auto-steers to keep marker centered
- CAN bus integration (ID 0x125)
- Manual override mode

**Controls:**
- `p` - Pause/Resume autonomous mode
- `m` - Toggle manual mode
- `w`/`s` - Manual throttle
- `a`/`d` - Manual steering
- `q` - Quit

See [docs/ARUCO_NAVIGATION.md](docs/ARUCO_NAVIGATION.md) for detailed documentation.

## Project Structure

```
TE2004B_CamExtraFeature/
├── config.yaml                 # Main configuration file
├── requirements.txt            # Python dependencies
├── aruco_navigation.py         # Autonomous navigation controller
├── QUICKSTART.md               # Quick reference guide
├── README.md                   # This file
│
├── camera_processing/          # Core processing modules
│   ├── __init__.py             # Module exports
│   ├── aruco_detector.py       # ArUco marker detection & depth estimation
│   └── image_filters.py        # Image processing filters
│
├── viewer/                     # Viewer applications
│   ├── aruco_viewer.py         # Main viewer with ArUco detection
│   └── camera_viewer.py        # Simple camera viewer
│
├── utils/                      # Utility scripts
│   ├── generate_aruco_markers.py   # Generate printable ArUco markers
│   ├── calibrate_focal_length.py   # Focal length calibration tool
│   └── check_stream_quality.py     # Camera stream diagnostics
│
├── tests/                      # Test & diagnostic scripts
│   ├── diagnose_camera.py          # Camera connection diagnostics
│   ├── test_aruco_detection.py     # ArUco detection tests
│   └── test_aruco_simple.py        # Simple ArUco test
│
├── docs/                       # Documentation
│   ├── ARUCO_NAVIGATION.md         # Navigation system documentation
│   ├── SETUP_GUIDE.md              # Setup instructions
│   └── README_SOLUTION.md          # Technical details
│
├── docs/                       # Documentation
│   ├── SETUP_GUIDE.md              # Detailed setup instructions
│   ├── CONFIGURATION.md            # Configuration guide
│   ├── CURRENT_STATUS.md           # Current system status
│   └── PROJECT_REORGANIZATION.md   # Project changes documentation
│
├── cam_server_page/            # Streamlit web app (TODO)
│   ├── app_opencv.py
│   ├── app.py
│   └── README.md
│
└── aruco_markers/              # Generated ArUco markers (created at runtime)
```

## Features

### ArUco Marker Detection
- Real-time marker detection
- Distance/depth estimation based on marker size
- Multiple ArUco dictionary support (4x4, 5x5, 6x6, 7x7)
- Marker ID display
- Camera pose estimation (with calibration)

### Image Processing Filters
- Grayscale conversion
- Edge detection (Canny)
- Gaussian blur
- Sharpen filter
- Brightness/contrast adjustment
- Binary threshold

### Camera Support
- DroidCam
- IP Webcam
- MJPEG/HTTP video stream
- Built-in webcams

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Camera Calibration 

For precise distance estimation, calibrate camera with `utils/calibrate_focal_length.py`


## ArUco Depth Estimation

### How It Works

The distance to an ArUco marker is estimated using:

```
Distance = (Real_Marker_Size × Focal_Length) / Perceived_Marker_Size_in_Pixels
```

## Usage Examples

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

### ArUco Dictionary Types:
- `DICT_4X4_50` - Good for small markers, fewer IDs
- `DICT_6X6_250` - Good balance
- `DICT_7X7_1000` - More unique IDs, larger markers

### Marker Sizes:
- **Small (5-10cm)**: Good for close range (< 1m)
- **Medium (10-20cm)**: General purpose (1-3m)
- **Large (20-50cm)**: Long range (3-10m)

## Performance Tips

1. **Lower latency**: Set buffer size to 1
   ```python
   cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
   ```

2. **Better detection**: Use good lighting and avoid shadows

3. **Faster processing**: Use grayscale instead of color

4. **Multiple markers**: Use unique IDs for each marker


