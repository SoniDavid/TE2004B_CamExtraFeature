#!/usr/bin/env python3
"""
Base Navigation Controller
===========================

Abstract base class for navigation with different vision targets.
Handles common functionality: BLE, motor control, manual mode, etc.
"""

import cv2
import sys
import os
import yaml
import asyncio
from abc import ABC, abstractmethod
from bleak import BleakScanner, BleakClient

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def to_byte(val):
    """Convert value from -1.0 to +1.0 to byte (0-255)."""
    return int((val + 1) * 127.5)


class BaseNavigationController(ABC):
    """Base class for navigation controllers with different vision targets."""
    
    def __init__(self, config_path=None):
        """Initialize the base navigation controller."""
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(os.path.dirname(script_dir), 'config.yaml')
        
        self.config = self.load_config(config_path)
        
        # Extract configuration
        camera_cfg = self.config['camera']
        nav_cfg = self.config.get('navigation', {})
        
        # Camera setup
        self.camera_url = camera_cfg['url']
        self.cap = None
        self.frame_width = None
        self.frame_height = None
        
        # Navigation parameters
        self.max_steering = nav_cfg.get('max_steering', 0.6)
        self.steering_kp = nav_cfg.get('steering_kp', 0.003)
        self.base_throttle = nav_cfg.get('base_throttle', 0.3)
        self.backward_throttle_multiplier = nav_cfg.get('backward_throttle_multiplier', 0.5)
        
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
            'navigation': {
                'max_steering': 0.6,
                'steering_kp': 0.003,
                'base_throttle': 0.3,
                'backward_throttle_multiplier': 0.5,
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
            print(f"WARNING: BLE device '{self.ble_device_name}' not found!")
            print("Running in simulation mode (no commands sent)")
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
        
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config['camera']['buffer_size'])
        
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
                    
                    if throttle_byte != last_throttle_byte or steering_byte != last_steering_byte:
                        await self.ble_client.write_gatt_char(self.ble_throttle_uuid, bytearray([throttle_byte]))
                        await self.ble_client.write_gatt_char(self.ble_steering_uuid, bytearray([steering_byte]))
                        print(f"[BLE TX] Throttle: {self.current_throttle:+.2f} ({throttle_byte:3d}) | Steering: {self.current_steering:+.2f} ({steering_byte:3d})")
                        last_throttle_byte = throttle_byte
                        last_steering_byte = steering_byte
                
                await asyncio.sleep(0.25)
            except Exception as e:
                print(f"[BLE sender error: {e}]")
                await asyncio.sleep(0.5)
    
    def send_motor_command(self, throttle, steering):
        """Update motor command values (non-blocking)."""
        self.current_throttle = max(-1.0, min(1.0, throttle))
        self.current_steering = max(-1.0, min(1.0, steering))
    
    def calculate_steering(self, target_center_x):
        """Calculate steering based on target position with dead zone and quantization."""
        if self.frame_width is None:
            return 0.0
        
        frame_center = self.frame_width / 2.0
        error = target_center_x - frame_center
        
        steering = error * self.steering_kp
        
        if abs(steering) < self.steering_dead_zone:
            steering = 0.0
        
        steering = max(-self.max_steering, min(self.max_steering, steering))
        
        if steering != 0.0:
            steering = round(steering / self.steering_quantization) * self.steering_quantization
        
        return steering
    
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
    
    @abstractmethod
    def get_detector_name(self):
        """Return the name of this detector (e.g., 'ArUco', 'Color')."""
        pass
    
    @abstractmethod
    def process_frame_autonomous(self, frame):
        """
        Process frame in autonomous mode - MUST BE IMPLEMENTED BY SUBCLASS.
        
        Returns:
            (throttle, steering, frame_with_overlay)
        """
        pass
    
    async def run_async(self):
        """Main control loop."""
        if not self.init_camera():
            return
        
        await self.connect_ble()
        
        window_name = f"{self.get_detector_name()} Navigation"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        
        print("\n" + "="*60)
        print(f"{self.get_detector_name().upper()} NAVIGATION CONTROLLER")
        print("="*60)
        print("Controls:")
        print("  'p' - Pause/Resume autonomous mode")
        print("  'm' - Toggle manual override")
        print("  'w'/'s' - Manual throttle")
        print("  'a'/'d' - Manual steering")
        print("  'space' - Stop")
        print("  'q' - Quit")
        print("="*60)
        print(f"Autonomous mode: {'ON' if self.autonomous_mode else 'OFF'}\n")
        
        ble_task = asyncio.create_task(self._ble_sender_task())
        frame_count = 0
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    print("Failed to read frame")
                    break
                
                frame_count += 1
                
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
                    throttle = 0.0
                    steering = 0.0
                    
                    cv2.putText(frame, "PAUSED",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
                
                self.send_motor_command(throttle, steering)
                
                cv2.imshow(window_name, frame)
                
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
                
                if self.manual_mode:
                    self.process_manual_input(key)
                
                await asyncio.sleep(0.001)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
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
        """Main entry point."""
        asyncio.run(self.run_async())
