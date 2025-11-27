# ArUco-Based Autonomous Navigation

This document explains the autonomous navigation system that integrates ArUco marker detection with the TE2004B robot car.

## Overview

The `aruco_navigation.py` script provides autonomous navigation capabilities where the robot car:
- Detects ArUco markers using the DroidCam camera
- Maintains a target distance from the marker (default: 25cm)
- Auto-steers to keep the marker centered in the camera frame
- Sends motor control commands via BLE to the ESP32-C3 sensor hub

## System Architecture

```
┌─────────────────┐
│  DroidCam       │
│  (Camera Feed)  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ ArUco Detection │
│ & Processing    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Navigation     │
│  Controller     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  BLE Connection │
│  (ESP32-C3)     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  TE2004B Robot  │
│  (STM32H7)      │
└─────────────────┘
```

## Control Algorithm

### Distance Control (Throttle)
```
distance_error = measured_distance - target_distance

if |distance_error| > tolerance:
    if distance_error > 0:
        throttle = +base_throttle    # Move forward
    else:
        throttle = -base_throttle/2  # Move backward slowly
else:
    throttle = 0.0                   # Stop (at target)
```

### Alignment Control (Steering)
```
frame_center = frame_width / 2
error = marker_center_x - frame_center

steering = -error × steering_kp

steering = clamp(steering, -max_steering, +max_steering)
```

Negative steering because:
- Marker right of center (error > 0) → Steer left (negative)
- Marker left of center (error < 0) → Steer right (positive)

## BLE Protocol

### Motor Control via BLE Characteristics

**Device**: BLE_Sensor_Hub (ESP32-C3)
**Service UUID**: 12345678-1234-5678-1234-56789abcdef0

**Characteristics**:
- Throttle: 12345678-1234-5678-1234-56789abcdef2
- Steering: 12345678-1234-5678-1234-56789abcdef3

**Format**:
```
Value: Single byte (0-255)
  0 = -1.0 (full backward / full left)
  127 = 0.0 (neutral)
  255 = +1.0 (full forward / full right)

Conversion: byte = int((value + 1.0) × 127.5)
```

Example:
```python
throttle = 0.3   →  byte = int((0.3 + 1) × 127.5) = 165
steering = -0.15 →  byte = int((-0.15 + 1) × 127.5) = 108
```

## Configuration Parameters

All parameters are configurable in `config.yaml` under the `navigation` section:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `target_distance_cm` | 25.0 | Target distance to maintain from marker |
| `distance_tolerance_cm` | 3.0 | Stop if within this range of target |
| `max_steering` | 0.6 | Maximum steering angle (0.0-1.0) |
| `steering_kp` | 0.003 | Proportional gain for steering control |
| `base_throttle` | 0.3 | Throttle speed when moving forward |
| `frame_center_tolerance` | 50 | Pixel tolerance for center alignment |
| `ble.device_name` | "BLE_Sensor_Hub" | BLE device name to connect to |

## Usage

### Basic Usage
```bash
python aruco_navigation.py
```

### Controls

**Autonomous Mode:**
- `p` - Pause/Resume autonomous navigation
- `q` - Quit

**Manual Override:**
- `m` - Toggle manual mode
- `w` - Increase throttle (forward)
- `s` - Decrease throttle (backward)
- `a` - Steer left
- `d` - Steer right
- `space` - Stop (zero throttle/steering)

### Display Information

The video display shows:
- Live camera feed with ArUco marker detection
- Distance measurement and marker ID
- Current throttle and steering values
- Mode indicator (AUTONOMOUS / MANUAL / PAUSED)
- Center line (blue) and marker center (yellow dot)

## Hardware Requirements

### BLE Setup

1. **Power on ESP32-C3 Sensor Hub**
   - Ensure the BLE_Sensor_Hub is powered and advertising
   - LED should indicate BLE is active

2. **Check Bluetooth on Linux:**
```bash
# Ensure Bluetooth is enabled
sudo systemctl status bluetooth

# Scan for BLE devices
sudo hcitool lescan
```

3. **Python BLE Library:**
   - Uses `bleak` library (cross-platform)
   - No special permissions required
   - Works on Linux, Windows, macOS

### Without BLE Hardware

If BLE device is not available, the script will run in "simulation mode":
- All navigation logic works normally
- Motor commands are calculated but not sent
- Console displays warnings about BLE unavailability

## Tuning Guide

### If the robot overshoots the target:
- Decrease `base_throttle` (e.g., 0.2)
- Increase `distance_tolerance_cm` (e.g., 5.0)

### If steering is too aggressive:
- Decrease `steering_kp` (e.g., 0.002)
- Decrease `max_steering` (e.g., 0.4)

### If steering is too slow:
- Increase `steering_kp` (e.g., 0.004)
- Increase `max_steering` (e.g., 0.8)

### If the robot oscillates around center:
- Decrease `steering_kp`
- Add damping (requires PID controller - not yet implemented)

## Advanced: PID Controller

The current implementation uses proportional control (P-only). For better performance, consider implementing PID:

```python
class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp  # Proportional
        self.ki = ki  # Integral
        self.kd = kd  # Derivative
        self.last_error = 0.0
        self.integral = 0.0
    
    def calculate(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.last_error = error
        return output
```

## Troubleshooting

### Camera not connecting
- Check DroidCam IP address in `config.yaml`
- Verify DroidCam app is running on phone
- Test URL in browser: `http://10.22.227.47:4747/video`

### No markers detected
- Ensure proper lighting
- Check marker has white border
- Verify marker size matches `marker_size_cm` in config
- Check focal length calibration

### BLE connection errors
```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# Restart Bluetooth
sudo systemctl restart bluetooth

# Scan for devices
sudo hcitool lescan
```

### Robot doesn't move
- Check BLE connection to ESP32-C3
- Verify sensor hub firmware is running
- Check motor power supply
- Verify BLE characteristics are writable

## Safety Notes

- Always test in a safe, open area
- Keep emergency stop button accessible
- Start with low `base_throttle` values
- Use manual mode for initial testing
- Monitor the robot at all times during autonomous operation

## Integration with TE2004B

This system integrates with the existing TE2004B architecture:
- **ESP32-C3 Sensor Hub**: Receives BLE commands, relays to STM32 via CAN
- **STM32H7 CM7**: Controls motors based on commands from ESP32-C3
- **BLE Controller**: Uses same protocol, can coexist or be replaced
- **Encoders**: Provide odometry feedback (future enhancement)

## Future Enhancements

- [ ] PID controller for smoother control
- [ ] Multiple marker tracking
- [ ] Path planning with waypoints
- [ ] Integration with encoder odometry
- [ ] Obstacle avoidance
- [ ] Speed adaptation based on distance
- [ ] Recording and replay of navigation sessions
