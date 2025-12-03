# TE2004B Robot Control System

A modular robot control system with camera-based navigation and waypoint control for ESP32-C3 robot car.

## Project Structure

```
TE2004B_CamExtraFeature/
├── launch.py                  
├── on_board_cam/              # Camera-based navigation
│   ├── navigation/            # Autonomous navigation controllers
│   │   ├── unified_navigation.py    # Switchable detector (ArUco/Color)
│   │   ├── aruco_navigation.py      # ArUco-only navigation
│   │   └── base_navigation.py       # Base controller with BLE
│   ├── camera_processing/     # ArUco detection, image filters
│   ├── viewer/                # Camera viewers
│   ├── utils/                 # Calibration tools
│   └── config.yaml            # Camera & navigation settings
│
└── waypoint_marker/           # Waypoint control system
    ├── waypoints_gui.py       # Click-to-send GUI
    ├── ble_client.py          # BLE communication
    ├── config.yaml            # Waypoint settings
    └── test_ble_connection.py # Connection test
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `opencv-python` - Camera processing
- `numpy` - Numerical operations
- `pyyaml` - Configuration files
- `bleak` - BLE communication
- `tkinter` - GUI (usually pre-installed)

### Launch Commands

```bash
# Navigation only
python3 launch.py --navigation

# Waypoint GUI only
python3 launch.py --waypoint

# Both systems together
python3 launch.py --full
```

Or manually:

```bash
# Camera navigation
cd on_board_cam
python3 navigation/unified_navigation.py

# Waypoint control
cd waypoint_marker
python3 waypoints_gui.py
```

## Features

### Camera Navigation (on_board_cam)

- Real-time ArUco marker detection with distance estimation
- Color-based object tracking
- Autonomous navigation (approach/align to targets)
- Switchable detectors (press 't' to toggle)
- Manual override mode
- Multiple image processing modes

**Controls:**
- `t` - Switch detector (ArUco ↔ Color)
- `p` - Pause/Resume autonomous mode
- `m` - Toggle manual override
- `w`/`s` - Manual throttle forward/backward
- `a`/`d` - Manual steering left/right
- `space` - Emergency stop
- `q` - Quit

### Waypoint Control (waypoint_marker)

- Visual workspace (180cm × 120cm)
- Click-to-send waypoint coordinates
- Real-time coordinate display
- Simulation mode (works without robot)
- BLE status monitoring

**Usage:** Click anywhere on the canvas to send waypoint to robot.

## Configuration

### Camera Settings (on_board_cam/config.yaml)

```yaml
camera:
  url: "http://10.22.231.72:4747/video"  # Your camera stream URL
  buffer_size: 1                          # Low latency

aruco:
  dictionary_type: "DICT_6X6_250"
  marker_size_cm: 15.8                    # Measured marker size
  focal_length_px: 490.2                  # Camera focal length

navigation:
  target_distance_cm: 50.0    # Desired distance from marker
  max_steering: 1.0           # Maximum steering angle
  base_throttle: 0.6          # Forward speed
```

### Waypoint Settings (waypoint_marker/config.yaml)

```yaml
workspace:
  max_x: 180.0  # Width in cm
  max_y: 120.0  # Height in cm

waypoint:
  default_omega: 0.0              # Default rotation
  coordinate_precision: 1         # Decimal places
```

### Camera URL Examples

**IP Webcam (Android):**
```yaml
url: "http://<phone-ip>:4747/video"
```

**DroidCam:**
```yaml
url: "http://<phone-ip>:4747/mjpegfeed"
```

**ESP32-CAM:**
```yaml
url: "http://<esp-ip>/stream"
```

## Setup Guide

### 1. Generate ArUco Markers

```bash
cd on_board_cam
python3 utils/generate_aruco_markers.py
```

Print the generated `aruco_markers/printable_sheet.png`.

### 2. Calibrate System

**Measure marker size:**
1. Measure printed marker width in cm
2. Update `marker_size_cm` in `on_board_cam/config.yaml`

**Calibrate focal length:**
```bash
cd on_board_cam
python3 utils/calibrate_focal_length.py
```

**Calibrate color detection:**
```bash
cd on_board_cam
python3 utils/calibrate_color_mask.py
```

### 3. Configure Camera

Edit `on_board_cam/config.yaml` with your camera URL.

### 4. Test Connection

```bash
cd waypoint_marker
python3 test_ble_connection.py
```

## ROS2-Style Launch System

The `launch.py` script provides process management:

```bash
# Available options
python3 launch.py --navigation    # Navigation only
python3 launch.py --waypoint      # Waypoint only  
python3 launch.py --full          # Both systems
```

**Features:**
- Launches multiple processes simultaneously
- Graceful shutdown with Ctrl+C
- Proper cleanup on exit
- Process monitoring

## BLE Communication

**ESP32-C3 Robot:**
- Device name: `BLE_Sensor_Hub`
- Motor control via BLE characteristics
- Waypoint setting (x, y, omega)
- Sensor reading capabilities

**Protocol:**
- Values sent as byte arrays
- Throttle/Steering: -1.0 to 1.0 (float)
- Coordinates: cm values (float)

Both programs work in simulation mode if ESP32 is not available.

## ArUco Detection

### Distance Calculation

```
Distance = (Real_Marker_Size × Focal_Length) / Perceived_Size_in_Pixels
```

### Dictionary Types

- `DICT_4X4_50` - Small markers, fewer IDs
- `DICT_6X6_250` - Good balance (recommended)
- `DICT_7X7_1000` - More IDs, larger markers

### Marker Sizes

- **Small (5-10cm):** Close range (<1m)
- **Medium (10-20cm):** General purpose (1-3m)
- **Large (20-50cm):** Long range (3-10m)

## Troubleshooting

### Camera Issues

**Can't connect to camera:**
- Check camera URL in config.yaml
- Verify camera app is running
- Test URL in web browser first
- Check network connectivity

**Low frame rate:**
- Set `buffer_size: 1` in config
- Lower camera app resolution
- Use wired connection

### BLE Issues

**Can't connect to ESP32:**
- Check ESP32 is powered on
- Verify device name: `BLE_Sensor_Hub`
- Enable Bluetooth on computer
- Programs work in simulation mode without hardware

**Commands not received:**
- Verify ESP32 firmware is running
- Test with `test_ble_connection.py`
- Check Bluetooth connection quality

### ArUco Detection Issues

**Markers not detected:**
- Check lighting (avoid shadows)
- Ensure marker is flat with white border
- Verify correct dictionary type in config
- Try larger marker size

**Inaccurate distance:**
- Measure marker size accurately
- Update `marker_size_cm` in config
- Calibrate `focal_length_px`
- Ensure marker is perpendicular to camera

## Advanced Topics

### Adding Custom Target Detectors

1. Create detector class in `on_board_cam/navigation/target_detectors.py`
2. Implement `detect()` method
3. Register in `unified_navigation.py`
4. Press 't' to cycle through detectors

### Performance Optimization

**Camera latency:**
```python
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
```

**Processing speed:**
- Use grayscale instead of color
- Lower resolution
- Skip unnecessary processing

## File Locations

- Main launcher: `launch.py`
- Camera config: `on_board_cam/config.yaml`
- Waypoint config: `waypoint_marker/config.yaml`
- Generated markers: `on_board_cam/aruco_markers/`
- Utilities: `on_board_cam/utils/`

## License

Educational project for TE2004B course.

---

**Quick Reference:**
```bash
# Navigation
python3 launch.py --navigation

# Waypoint control
python3 launch.py --waypoint

# Both systems
python3 launch.py --full
```


