#!/usr/bin/env python3
"""
ArUco-Based Autonomous Navigation for TE2004B Robot Car
==========================================================

This script integrates ArUco marker detection with the TE2004B robot car
to enable autonomous navigation and alignment via BLE.

Features:
- Detects ArUco markers and measures distance
- Moves forward when distance > target distance
- Stops when distance <= target distance  
- Auto-steers to center the marker in camera frame
- Sends commands via BLE to ESP32-C3 sensor hub

Controls:
- 'q' - Quit
- 'p' - Pause/Resume autonomous mode
- 'm' - Toggle manual override
- WASD - Manual control (when in manual mode)
"""

import cv2
import sys
import os
import yaml
import time
import asyncio
from bleak import BleakScanner, BleakClient

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from camera_processing import ArucoDetector

# BLE Configuration (matches TE2004B sensor_hub)
TARGET_DEVICE_NAME = "BLE_Sensor_Hub"
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID_THROTTLE = "12345678-1234-5678-1234-56789abcdef2"
CHAR_UUID_STEERING = "12345678-1234-5678-1234-56789abcdef3"


def to_byte(val):
    """Convert value from -1.0 to +1.0 to byte (0-255)."""
    return int((val + 1) * 127.5)


class ArucoNavigationController:
    """Controller for ArUco-based autonomous navigation via BLE."""
    
    def __init__(self, config_path="config.yaml"):
        """Initialize the navigation controller."""
        self.config = self.load_config(config_path)
        
        # Extract configuration
        camera_cfg = self.config['camera']
        aruco_cfg = self.config['aruco']
        nav_cfg = self.config.get('navigation', {})
        
        # Camera setup
        self.camera_url = camera_cfg['url']
        self.cap = None
        
        # ArUco detector
        self.detector = ArucoDetector(
            aruco_dict_type=aruco_cfg['dictionary_type'],
            marker_size_cm=aruco_cfg['marker_size_cm'],
            focal_length_px=aruco_cfg['focal_length_px']
        )
        
        # Navigation parameters
        self.target_distance_cm = nav_cfg.get('target_distance_cm', 25.0)
        self.distance_tolerance_cm = nav_cfg.get('distance_tolerance_cm', 3.0)
        self.max_steering = nav_cfg.get('max_steering', 0.6)
        self.steering_kp = nav_cfg.get('steering_kp', 0.003)
        self.base_throttle = nav_cfg.get('base_throttle', 0.3)
        
        # BLE setup
        ble_cfg = nav_cfg.get('ble', {})
        self.ble_device_name = ble_cfg.get('device_name', TARGET_DEVICE_NAME)
        
        # State
        self.autonomous_mode = True
        self.manual_mode = False
        self.running = True
        self.frame_width = None
        self.frame_height = None
        
        # BLE client
        self.ble_client = None
        self.pending_ble_task = None
        
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
            'aruco': {'dictionary_type': 'DICT_6X6_250', 'marker_size_cm': 15.0, 'focal_length_px': 490.20},
            'navigation': {
                'target_distance_cm': 25.0,
                'distance_tolerance_cm': 3.0,
                'max_steering': 0.6,
                'steering_kp': 0.003,
                'base_throttle': 0.3,
                'ble': {'device_name': 'BLE_Sensor_Hub'}
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
        """Dedicated background task for sending BLE commands."""
        while self.running:
            try:
                if self.ble_client and self.ble_client.is_connected:
                    throttle_byte = to_byte(self.current_throttle)
                    steering_byte = to_byte(self.current_steering)
                    
                    # Fast, non-blocking writes
                    await self.ble_client.write_gatt_char(CHAR_UUID_THROTTLE, bytearray([throttle_byte]))
                    await self.ble_client.write_gatt_char(CHAR_UUID_STEERING, bytearray([steering_byte]))
                
                # Send at 20Hz (50ms interval)
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"[BLE sender error: {e}]")
                await asyncio.sleep(0.1)
    
    def send_motor_command(self, throttle, steering):
        """
        Update motor command values (non-blocking).
        Background task handles actual BLE transmission.
        
        Args:
            throttle: -1.0 to +1.0
            steering: -1.0 to +1.0
        """
        # Clamp and store values - background task will send them
        self.current_throttle = max(-1.0, min(1.0, throttle))
        self.current_steering = max(-1.0, min(1.0, steering))
        
        self.current_throttle = throttle
        self.current_steering = steering
    
    def calculate_steering(self, marker_center_x):
        """
        Calculate steering based on marker position in frame.
        
        Args:
            marker_center_x: X coordinate of marker center in pixels
        
        Returns:
            steering: Steering value from -1.0 (left) to +1.0 (right)
        """
        if self.frame_width is None:
            return 0.0
        
        frame_center = self.frame_width / 2.0
        error = marker_center_x - frame_center
        
        # Proportional control
        # Marker on right (error > 0) → Turn right (positive steering)
        # Marker on left (error < 0) → Turn left (negative steering)
        steering = error * self.steering_kp
        
        # Clamp to max steering
        steering = max(-self.max_steering, min(self.max_steering, steering))
        
        return steering
    
    def process_frame_autonomous(self, frame):
        """
        Process frame in autonomous mode.
        
        Returns:
            (throttle, steering, frame_with_overlay)
        """
        # Detect ArUco markers
        corners, ids, rejected = self.detector.detect(frame)
        
        throttle = 0.0
        steering = 0.0
        
        if ids is not None and len(ids) > 0:
            # Get first marker info
            marker_info = self.detector.get_marker_info(corners, ids)[0]
            distance_cm = marker_info['distance_cm']
            center_x = marker_info['center_x']
            center_y = marker_info['center_y']
            marker_id = marker_info['id']
            
            # Draw detection
            frame = self.detector.draw_detections(
                frame, corners, ids,
                show_distance=True,
                show_id=True
            )
            
            # Calculate steering to center the marker
            steering = self.calculate_steering(center_x)
            
            # Calculate throttle based on distance
            distance_error = distance_cm - self.target_distance_cm
            
            if abs(distance_error) > self.distance_tolerance_cm:
                if distance_error > 0:
                    # Too far, move forward
                    throttle = self.base_throttle
                else:
                    # Too close, move backward slowly
                    throttle = -self.base_throttle * 0.5
            else:
                # Within tolerance, stop
                throttle = 0.0
            
            # Add status overlay
            throttle_byte = to_byte(throttle)
            steering_byte = to_byte(steering)
            
            status_text = [
                f"ID: {marker_id} | Dist: {distance_cm:.1f}cm",
                f"Target: {self.target_distance_cm:.1f}cm",
                f"Error: {distance_cm - self.target_distance_cm:+.1f}cm | Center Err: {center_x - self.frame_width/2:+.0f}px",
                "",
                f"COMMANDS TO SEND:",
                f"Throttle: {throttle:+.2f} (byte: {throttle_byte:3d})",
                f"Steering: {steering:+.2f} (byte: {steering_byte:3d})"
            ]
            
            y_offset = 30
            for i, text in enumerate(status_text):
                if text == "":
                    y_offset += 10
                    continue
                color = (0, 255, 255) if i >= 4 else (0, 255, 0)  # Yellow for commands
                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 25
            
            # Draw center line and marker position
            cv2.line(frame, (int(self.frame_width/2), 0),
                    (int(self.frame_width/2), self.frame_height),
                    (255, 0, 0), 2)
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 255, 255), -1)
            
        else:
            # No marker detected - stop
            throttle = 0.0
            steering = 0.0
            
            cv2.putText(frame, "NO MARKER DETECTED - STOPPED",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        return throttle, steering, frame
    
    def process_manual_input(self, key):
        """Process manual control input."""
        # WASD controls
        if key == ord('w'):
            self.manual_throttle = min(1.0, self.manual_throttle + 0.1)
        elif key == ord('s'):
            self.manual_throttle = max(-1.0, self.manual_throttle - 0.1)
        elif key == ord('a'):
            self.manual_steering = max(-1.0, self.manual_steering - 0.1)
        elif key == ord('d'):
            self.manual_steering = min(1.0, self.manual_steering + 0.1)
        elif key == ord(' '):  # Space to stop
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
        window_name = "ArUco Navigation - Press 'h' for help"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        
        print("\n" + "="*60)
        print("ARUCO NAVIGATION CONTROLLER")
        print("="*60)
        print("Controls:")
        print("  'p' - Pause/Resume autonomous mode")
        print("  'm' - Toggle manual override")
        print("  'w'/'s' - Manual throttle (forward/backward)")
        print("  'a'/'d' - Manual steering (left/right)")
        print("  'space' - Stop (manual mode)")
        print("  'q' - Quit")
        print("="*60)
        print(f"\nTarget distance: {self.target_distance_cm}cm")
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
                
                # Fast camera loop - minimal delay for responsiveness
                await asyncio.sleep(0.001)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            # Stop BLE sender and send stop command
            print("\nStopping robot...")
            self.running = False
            self.send_motor_command(0.0, 0.0)
            await asyncio.sleep(0.2)  # Give BLE task time to send final command
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
    controller = ArucoNavigationController()
    controller.run()


if __name__ == "__main__":
    main()
