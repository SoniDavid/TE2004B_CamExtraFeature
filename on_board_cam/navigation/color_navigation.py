#!/usr/bin/env python3
"""
Color-Based Autonomous Navigation for TE2004B Robot Car
========================================================

This script uses color detection to follow a colored object instead of ArUco markers.
Uses HSV color space for robust color tracking.

Features:
- Detects specific color in camera frame
- Moves toward the colored object
- Auto-steers to center the color target in camera frame
- Sends commands via BLE to ESP32-C3 sensor hub

Controls:
- 'q' - Quit
- 'p' - Pause/Resume autonomous mode
- 'm' - Toggle manual override
- 'c' - Recalibrate color (pick new color from frame)
- WASD - Manual control (when in manual mode)
"""

import cv2
import sys
import os
import yaml
import time
import asyncio
import numpy as np
from bleak import BleakScanner, BleakClient

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def to_byte(val):
    """Convert value from -1.0 to +1.0 to byte (0-255)."""
    return int((val + 1) * 127.5)


class ColorNavigationController:
    """Controller for color-based autonomous navigation via BLE."""
    
    def __init__(self, config_path=None):
        """Initialize the navigation controller."""
        if config_path is None:
            # Default to config.yaml in parent directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(os.path.dirname(script_dir), 'config.yaml')
        self.config = self.load_config(config_path)
        
        # Extract configuration
        camera_cfg = self.config['camera']
        nav_cfg = self.config.get('navigation', {})
        color_cfg = self.config.get('color_tracking', {})
        
        # Camera setup
        self.camera_url = camera_cfg['url']
        self.cap = None
        
        # Color tracking parameters
        self.hsv_lower = np.array(color_cfg.get('hsv_lower', [0, 100, 100]))
        self.hsv_upper = np.array(color_cfg.get('hsv_upper', [10, 255, 255]))
        self.min_contour_area = color_cfg.get('min_contour_area', 500)
        self.target_area_ratio = color_cfg.get('target_area_ratio', 0.05)  # Target object size as ratio of frame
        
        # Navigation parameters
        self.max_steering = nav_cfg.get('max_steering', 0.6)
        self.steering_kp = nav_cfg.get('steering_kp', 0.003)
        self.base_throttle = nav_cfg.get('base_throttle', 0.3)
        
        # Steering quantization and dead zone
        self.steering_dead_zone = nav_cfg.get('steering_dead_zone', 0.1)
        self.steering_quantization = nav_cfg.get('steering_quantization', 0.05)
        
        # BLE setup
        ble_cfg = nav_cfg.get('ble', {})
        self.ble_device_name = ble_cfg.get('device_name', 'BLE_Sensor_Hub')
        self.ble_service_uuid = ble_cfg.get('service_uuid', '12345678-1234-5678-1234-56789abcdef0')
        self.ble_throttle_uuid = ble_cfg.get('char_throttle_uuid', '12345678-1234-5678-1234-56789abcdef2')
        self.ble_steering_uuid = ble_cfg.get('char_steering_uuid', '12345678-1234-5678-1234-56789abcdef3')
        
        # State
        self.autonomous_mode = True
        self.manual_mode = False
        self.running = True
        self.frame_width = None
        self.frame_height = None
        
        # BLE client
        self.ble_client = None
        
        # Manual control state
        self.manual_throttle = 0.0
        self.manual_steering = 0.0
        
        # Current commands
        self.current_throttle = 0.0
        self.current_steering = 0.0
        
    def load_config(self, config_path):
        """Load configuration from YAML file."""
        if not os.path.exists(config_path):
            print(f"Warning: Config file not found: {config_path}")
            return self._default_config()
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"Loaded configuration from: {config_path}")
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._default_config()
    
    def _default_config(self):
        """Return default configuration."""
        return {
            'camera': {'url': 'http://10.22.227.47:4747/video', 'buffer_size': 1},
            'color_tracking': {
                'hsv_lower': [0, 100, 100],
                'hsv_upper': [10, 255, 255],
                'min_contour_area': 500,
                'target_area_ratio': 0.05
            },
            'navigation': {
                'max_steering': 0.6,
                'steering_kp': 0.003,
                'base_throttle': 0.3,
                'steering_dead_zone': 0.1,
                'steering_quantization': 0.05,
                'ble': {
                    'device_name': 'BLE_Sensor_Hub',
                    'service_uuid': '12345678-1234-5678-1234-56789abcdef0',
                    'char_throttle_uuid': '12345678-1234-5678-1234-56789abcdef2',
                    'char_steering_uuid': '12345678-1234-5678-1234-56789abcdef3'
                }
            }
        }
    
    async def connect_ble(self):
        """Connect to BLE sensor hub."""
        print(f"\nScanning for BLE device '{self.ble_device_name}'...")
        devices = await BleakScanner.discover(timeout=10.0) 
        target_device = next((d for d in devices if d.name == self.ble_device_name), None)
        
        if not target_device:
            print(f"ERROR: BLE device '{self.ble_device_name}' not found!")
            print("Make sure the ESP32-C3 sensor hub is powered on.")
            return False
        
        print(f"Found device at {target_device.address}")
        print("Connecting...")
        
        self.ble_client = BleakClient(target_device.address)
        await self.ble_client.connect()
        
        if not self.ble_client.is_connected:
            print("ERROR: Failed to connect to BLE device")
            return False
        
        print("Connected successfully!\n")
        return True
    
    def init_camera(self):
        """Initialize camera connection."""
        print(f"Connecting to camera at {self.camera_url}...")
        self.cap = cv2.VideoCapture(self.camera_url)
        
        if not self.cap.isOpened():
            print(f"ERROR: Failed to connect to camera")
            return False
        
        # Set buffer size for lower latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config['camera']['buffer_size'])
        
        # Get frame dimensions
        ret, frame = self.cap.read()
        if ret:
            self.frame_height, self.frame_width = frame.shape[:2]
            print(f"Camera connected: {self.frame_width}x{self.frame_height}")
        
        print("Camera connected successfully")
        return True
    
    async def _ble_sender_task(self):
        """Dedicated background task for sending BLE commands at 4Hz (250ms)."""
        last_throttle_byte = None
        last_steering_byte = None
        
        while self.running:
            try:
                if self.ble_client and self.ble_client.is_connected:
                    throttle_byte = to_byte(self.current_throttle)
                    steering_byte = to_byte(self.current_steering)
                    
                    # Only send if values changed to avoid spamming ESP32
                    if throttle_byte != last_throttle_byte or steering_byte != last_steering_byte:
                        await self.ble_client.write_gatt_char(self.ble_throttle_uuid, bytearray([throttle_byte]))
                        await self.ble_client.write_gatt_char(self.ble_steering_uuid, bytearray([steering_byte]))
                        print(f"[BLE TX] Throttle: {self.current_throttle:+.2f} ({throttle_byte:3d}) | Steering: {self.current_steering:+.2f} ({steering_byte:3d})")
                        last_throttle_byte = throttle_byte
                        last_steering_byte = steering_byte
                
                # Send at 4Hz (250ms interval) - gentler on ESP32
                await asyncio.sleep(0.25)
            except Exception as e:
                print(f"[BLE sender error: {e}]")
                await asyncio.sleep(0.5)
    
    def send_motor_command(self, throttle, steering):
        """
        Update motor command values (non-blocking).
        Background task handles actual BLE transmission.
        """
        self.current_throttle = max(-1.0, min(1.0, throttle))
        self.current_steering = max(-1.0, min(1.0, steering))
    
    def calculate_steering(self, target_center_x):
        """
        Calculate steering based on target position with dead zone and quantization.
        """
        if self.frame_width is None:
            return 0.0
        
        frame_center = self.frame_width / 2.0
        error = target_center_x - frame_center
        
        # Proportional control
        steering = error * self.steering_kp
        
        # Apply dead zone
        if abs(steering) < self.steering_dead_zone:
            steering = 0.0
        
        # Clamp to max steering
        steering = max(-self.max_steering, min(self.max_steering, steering))
        
        # Quantize steering
        if steering != 0.0:
            steering = round(steering / self.steering_quantization) * self.steering_quantization
        
        return steering
    
    def detect_color_target(self, frame):
        """
        Detect colored object in frame using HSV color space.
        
        Returns:
            (center_x, center_y, area, mask) or (None, None, 0, mask)
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
        
        # Morphological operations to reduce noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, None, 0, mask
        
        # Find largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        if area < self.min_contour_area:
            return None, None, 0, mask
        
        # Get center
        M = cv2.moments(largest_contour)
        if M["m00"] == 0:
            return None, None, 0, mask
        
        center_x = int(M["m10"] / M["m00"])
        center_y = int(M["m01"] / M["m00"])
        
        return center_x, center_y, area, mask
    
    def process_frame_autonomous(self, frame):
        """
        Process frame in autonomous mode.
        
        Returns:
            (throttle, steering, frame_with_overlay)
        """
        # Detect color target
        center_x, center_y, area, mask = self.detect_color_target(frame)
        
        throttle = 0.0
        steering = 0.0
        
        if center_x is not None:
            # Calculate area ratio
            frame_area = self.frame_width * self.frame_height
            area_ratio = area / frame_area
            
            # Draw detection
            cv2.circle(frame, (center_x, center_y), 10, (0, 255, 0), -1)
            cv2.circle(frame, (center_x, center_y), 15, (255, 255, 255), 2)
            
            # Calculate steering to center the target
            steering = self.calculate_steering(center_x)
            
            # Calculate throttle based on size
            # If target is small (far), move forward
            # If target is large (close), slow down or stop
            size_error = self.target_area_ratio - area_ratio
            
            if size_error > 0.01:  # Too far
                throttle = self.base_throttle
            elif size_error < -0.01:  # Too close
                throttle = -self.base_throttle * 0.3
            else:  # Just right
                throttle = 0.0
            
            # Add status overlay
            throttle_byte = to_byte(throttle)
            steering_byte = to_byte(steering)
            
            status_text = [
                f"Target detected at ({center_x}, {center_y})",
                f"Area: {area:.0f}px | Ratio: {area_ratio:.3f} (Target: {self.target_area_ratio:.3f})",
                f"Size Error: {size_error:+.3f}",
                "",
                f"COMMANDS:",
                f"Throttle: {throttle:+.2f} (byte: {throttle_byte:3d})",
                f"Steering: {steering:+.2f} (byte: {steering_byte:3d})"
            ]
            
            y_offset = 30
            for i, text in enumerate(status_text):
                if text == "":
                    y_offset += 10
                    continue
                color = (0, 255, 255) if i >= 4 else (0, 255, 0)
                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 25
            
            # Draw center line
            cv2.line(frame, (int(self.frame_width/2), 0),
                    (int(self.frame_width/2), self.frame_height),
                    (255, 0, 0), 2)
        else:
            # No target detected - stop
            throttle = 0.0
            steering = 0.0
            
            cv2.putText(frame, "NO COLOR TARGET DETECTED - STOPPED",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Show mask in corner
        mask_small = cv2.resize(mask, (320, 240))
        mask_colored = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
        frame[10:250, frame.shape[1]-330:frame.shape[1]-10] = mask_colored
        
        return throttle, steering, frame
    
    def process_manual_input(self, key):
        """Process manual control input."""
        if key == ord('w'):
            self.manual_throttle = min(1.0, self.manual_throttle + 0.1)
        elif key == ord('s'):
            self.manual_throttle = max(-1.0, self.manual_throttle - 0.1)
        elif key == ord('a'):
            self.manual_steering = max(-1.0, self.manual_steering - 0.1)
        elif key == ord('d'):
            self.manual_steering = min(1.0, self.manual_steering + 0.1)
        elif key == ord(' '):
            self.manual_throttle = 0.0
            self.manual_steering = 0.0
    
    async def run_async(self):
        """Main control loop (async)."""
        # Initialize camera
        if not self.init_camera():
            return
        
        # Connect to BLE
        if not await self.connect_ble():
            print("\nRunning without BLE connection (simulation mode)")
            print("Commands will be calculated but not sent.\n")
        
        # Window setup
        window_name = "Color Navigation - Press 'h' for help"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        
        print("\n" + "="*60)
        print("COLOR NAVIGATION CONTROLLER")
        print("="*60)
        print("Controls:")
        print("  'p' - Pause/Resume autonomous mode")
        print("  'm' - Toggle manual override")
        print("  'c' - Recalibrate color (coming soon)")
        print("  'w'/'s' - Manual throttle (forward/backward)")
        print("  'a'/'d' - Manual steering (left/right)")
        print("  'space' - Stop (manual mode)")
        print("  'q' - Quit")
        print("="*60)
        print(f"\nTracking HSV range: {self.hsv_lower} to {self.hsv_upper}")
        print(f"Autonomous mode: {'ON' if self.autonomous_mode else 'OFF'}")
        print("\nStarting...\n")
        
        # Start background BLE sender task
        ble_task = asyncio.create_task(self._ble_sender_task())
        frame_count = 0
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    print("Failed to read frame")
                    break
                
                frame_count += 1
                
                # Determine control mode and process
                if self.manual_mode:
                    throttle = self.manual_throttle
                    steering = self.manual_steering
                    
                    cv2.putText(frame, "MANUAL MODE",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
                    cv2.putText(frame, f"Throttle: {throttle:+.2f} | Steering: {steering:+.2f}",
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                
                elif self.autonomous_mode:
                    throttle, steering, frame = self.process_frame_autonomous(frame)
                    
                    cv2.putText(frame, "AUTONOMOUS MODE",
                               (10, frame.shape[0] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    # Paused
                    throttle = 0.0
                    steering = 0.0
                    
                    cv2.putText(frame, "PAUSED",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
                
                # Update motor command (non-blocking)
                self.send_motor_command(throttle, steering)
                
                # Display frame
                cv2.imshow(window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('p'):
                    if not self.manual_mode:
                        self.autonomous_mode = not self.autonomous_mode
                        print(f"Autonomous mode: {'ON' if self.autonomous_mode else 'OFF'}")
                elif key == ord('m'):
                    self.manual_mode = not self.manual_mode
                    if self.manual_mode:
                        self.autonomous_mode = False
                    print(f"Manual mode: {'ON' if self.manual_mode else 'OFF'}")
                
                # Manual control input
                if self.manual_mode:
                    self.process_manual_input(key)
                
                # Fast camera loop
                await asyncio.sleep(0.001)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            # Stop BLE sender and send stop command
            print("\nStopping robot...")
            self.running = False
            self.send_motor_command(0.0, 0.0)
            await asyncio.sleep(0.2)
            ble_task.cancel()
            
            if self.cap:
                self.cap.release()
            if self.ble_client and self.ble_client.is_connected:
                await self.ble_client.disconnect()
            cv2.destroyAllWindows()
            
            print(f"Total frames processed: {frame_count}")
            print("Goodbye!")
    
    def run(self):
        """Main entry point - wraps async loop."""
        asyncio.run(self.run_async())


def main():
    controller = ColorNavigationController()
    controller.run()


if __name__ == "__main__":
    main()
