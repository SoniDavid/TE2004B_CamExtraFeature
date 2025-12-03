# Unified Robot Control GUI

**All-in-one control interface for your robot with multiple operating modes!**

## Features

The Unified Control GUI combines all control methods into a single interface:

### 🎮 **Mode 1: Manual Control**
- **Keyboard/Gamepad control** with WASD + QE for omega (differential turning)
- Real-time throttle, steering, and omega display
- LED toggle with X key
- Emergency stop with ESC
- Supports Xbox/PS4 controllers

### 📍 **Mode 2: Waypoint**
- Visual workspace (180cm × 120cm default)
- Click anywhere to send waypoint coordinates
- Real-time waypoint visualization
- Confirmation feedback

### 🎯 **Mode 3: Navigation**
- **ArUco Marker following** - Track and approach markers
- **Color Target following** - Follow colored objects
- Live camera feed with detection overlay
- Automatic throttle/steering commands

### 🔍 **Mode 4: Filters**
- **Color Mask** - HSV-based color segmentation
- **Canny Edge** - Edge detection visualization
- Useful for debugging and calibration

## Usage

### Quick Start

```bash
# From project root
cd /home/soni/reto_embebidos/TE2004B_CamExtraFeature

# Launch unified control (RECOMMENDED)
python3 launch.py --unified

# Or direct launch
cd waypoint_marker
python3 unified_control_gui.py
```

### Requirements

Install dependencies:
```bash
pip install bleak opencv-python numpy pillow pynput inputs pyyaml
```

### Controls

#### Manual Mode
- **W/S** - Forward/Backward (Throttle)
- **A/D** - Left/Right (Steering)
- **Q/E** - Rotate Left/Right (Omega - differential turning)
- **X** - Toggle LED
- **ESC** - Emergency stop
- **Gamepad**: LY=throttle, RX=steering, D-pad=omega

#### Waypoint Mode
- **Click** on canvas to send waypoint
- Coordinates shown in cm

#### Navigation Mode
- Select **ArUco** or **Color** target type
- Camera feed shows live detection
- Commands sent automatically

#### Filter Mode
- Select **Color Mask** or **Canny Edge**
- View processed camera feed

## Architecture

```
Unified GUI
    ├── Single BLE Connection (ESP32)
    ├── Mode: Manual → sends throttle/steering/omega
    ├── Mode: Waypoint → sends x,y coordinates
    ├── Mode: Navigation → sends throttle/steering (from vision)
    └── Mode: Filters → display only (no commands)
```

**Key Feature**: All modes share one BLE connection - switch seamlessly without reconnecting!

## BLE Protocol

### Device
- **Name**: `BLE_Sensor_Hub`
- **Service UUID**: `12345678-1234-5678-1234-56789abcdef0`

### Characteristics
| Char | UUID | Purpose | Format |
|------|------|---------|--------|
| LED | ...def1 | LED control | uint8 (0/1) |
| Throttle | ...def2 | Forward/Back | uint8 (0-255, bipolar) |
| Steering | ...def3 | Left/Right | uint8 (0-255, bipolar) |
| Omega | ...def4 | Rotation | uint8 (0-255, bipolar) |
| Waypoint | ...def5 | Target position | 6 bytes (x,y,omega as int16) |

## Modes Explained

### When to use Manual Mode
- Direct control needed
- Testing basic movement
- Emergency override
- Differential turning (omega) for precise rotation

### When to use Waypoint Mode
- Navigate to specific coordinates
- Pre-planned paths
- Position-based control
- Works with ceiling camera positioning

### When to use Navigation Mode
- Visual target tracking
- ArUco marker approach
- Color-based following
- Autonomous operation

### When to use Filter Mode
- Debug camera settings
- Calibrate color masks
- Verify edge detection
- Check camera quality

## Troubleshooting

### BLE Connection Issues
- Check ESP32 is powered and running `sensor_hub.ino`
- Verify device name is `BLE_Sensor_Hub`
- GUI supports **simulation mode** if BLE unavailable

### Camera Not Working
- Check camera is connected (USB or IP)
- Verify permissions: `sudo usermod -a -G video $USER`
- Default is camera 0, modify in code if needed

### Manual Control Not Working
- Ensure `combined_input.py` and `scales.txt` exist
- Check keyboard/gamepad permissions
- Test inputs with `python3 combined_input.py`

### Navigation Not Detecting
- Check lighting conditions
- Calibrate color masks if using color mode
- Verify ArUco markers are visible and correct size

## Scaling Configuration

Edit `scales.txt` to adjust control sensitivity:
```
1.0    # Throttle scale (0.0 - 1.0)
0.8    # Steering scale (0.0 - 1.0)
0.8    # Omega scale (0.0 - 1.0)
```

## Advanced

### Custom Waypoint Workspace
Edit in `unified_control_gui.py`:
```python
self.max_x = 180.0  # Width in cm
self.max_y = 120.0  # Height in cm
```

### Camera Source
For IP camera, modify:
```python
self.camera_cap = cv2.VideoCapture("http://ip:port/stream")
```

## Integration

This GUI integrates with:
- ✅ ESP32-C3 Sensor Hub (BLE server)
- ✅ STM32H7 (via CAN from ESP32)
- ✅ Ceiling camera positioning system
- ✅ On-board camera (ArUco/Color detection)

## Support

For issues or questions, check:
1. ESP32 serial output for BLE debugging
2. Camera feed quality
3. BLE characteristic values
4. Control scales in `scales.txt`

**Enjoy unified control of your robot! 🚗🎮**
