# Navigation Module

Modular navigation system for TE2004B Robot Car with switchable vision targets.

## Architecture

```
navigation/
├── base_navigation.py      # Base controller with BLE/motor logic
├── target_detectors.py     # Pluggable target detection strategies
├── unified_navigation.py   # Main viewer with target switching
├── aruco_navigation.py     # Standalone ArUco navigation
└── color_navigation.py     # Standalone color navigation
```

## Quick Start

### Unified Navigation (Recommended)

Switch between different targets in real-time:

```bash
python3 navigation/unified_navigation.py
```

**Controls:**
- `t` - Switch target type (ArUco ↔ Color)
- `p` - Pause/Resume autonomous mode
- `m` - Toggle manual override
- `w`/`s` - Manual throttle
- `a`/`d` - Manual steering
- `space` - Stop
- `q` - Quit

### Standalone Navigation

Run specific target detector:

```bash
# ArUco marker following
python3 navigation/aruco_navigation.py

# Color-based following
python3 navigation/color_navigation.py
```

## Target Detectors

### 1. ArUco Detector
- **Distance measurement:** Actual distance in cm
- **Navigation:** Maintains target distance (configurable)
- **Best for:** Precise positioning, known markers

### 2. Color Detector
- **Distance measurement:** Area-based proxy
- **Navigation:** Maintains target size ratio
- **Best for:** Following colored objects
- **Calibration:** Use `utils/calibrate_color_mask.py`

## Adding New Target Detectors

1. **Create detector class** in `target_detectors.py`:

```python
class MyTargetDetector(TargetDetector):
    def detect(self, frame):
        # Your detection logic here
        return {
            'detected': True/False,
            'center_x': float,
            'center_y': float,
            'distance_metric': float,
            'frame': annotated_frame,
            'info': {}
        }
```

2. **Register in unified_navigation.py**:

```python
self.detectors = {
    'aruco': ArucoTargetDetector(self.config),
    'color': ColorTargetDetector(self.config),
    'mydetector': MyTargetDetector(self.config)  # Add this
}
```

3. **Press `t` to cycle through detectors!**

## Configuration

All parameters in `config.yaml`:

```yaml
navigation:
  target_distance_cm: 50.0           # ArUco target distance
  max_steering: 1.0                   # Maximum steering
  steering_kp: 0.005                  # Steering gain
  base_throttle: 0.6                  # Forward speed
  backward_throttle_multiplier: 0.8   # Reverse speed
  steering_dead_zone: 0.1             # Center dead zone
  steering_quantization: 0.10         # Min steering change

color_tracking:
  hsv_lower: [0, 100, 100]           # HSV lower bound
  hsv_upper: [10, 255, 255]          # HSV upper bound
  target_area_ratio: 0.05            # Target size (5% of frame)
```

## BLE Communication

- **Frequency:** 4Hz (250ms intervals)
- **Protocol:** Single byte per command (0-255)
- **Optimization:** Only sends on value change
- **Target:** ESP32-C3 sensor hub

## Features

- ✅ Modular architecture (easy to add new detectors)
- ✅ Real-time target switching (like filter viewer)
- ✅ Shared BLE/motor control logic
- ✅ Quantization and dead zone for smooth control
- ✅ Ackermann steering (inverted when reversing)
- ✅ Manual override mode
- ✅ Simulation mode (works without BLE)
