#!/usr/bin/env python3
"""
Unified Robot Control GUI - V2
===============================

Single GUI with clean mode switching (stops one mode, starts another):
1. Manual Control - Keyboard/gamepad control (WASD + QE)
2. Waypoint Mode - Click to send waypoint coordinates
3. ArUco Navigation - Follow ArUco markers (like aruco_navigation.py)
4. Color Navigation - Follow colored objects (like color_navigation.py)

Each mode runs independently and cleanly stops before another starts.
"""

import asyncio
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageTk
import yaml

# Try to import BLE
try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("⚠ BLE not available - simulation mode")

# Try to import manual control
try:
    import combined_input as inp
    MANUAL_CONTROL_AVAILABLE = True
except ImportError:
    MANUAL_CONTROL_AVAILABLE = False
    print("Manual control not available")

# Try to import OpenCV-based navigation
try:
    import os
    nav_path = Path(__file__).parent.parent / "on_board_cam"
    if str(nav_path) not in sys.path:
        sys.path.insert(0, str(nav_path))
    
    from camera_processing import ArucoDetector
    NAVIGATION_AVAILABLE = True
except ImportError as e:
    NAVIGATION_AVAILABLE = False
    print(f"Navigation not available: {e}")


def load_scales():
    """Load throttle/steering/omega scales from file."""
    try:
        config_path = Path(__file__).parent / "scales.txt"
        with open(config_path) as f:
            lines = f.read().strip().split('\n')
            return float(lines[0]), float(lines[1]), float(lines[2])
    except:
        return 1.0, 0.8, 0.8


def to_byte(val):
    """Convert value from -1.0 to +1.0 to byte (0-255)."""
    result = int(val * 128.0 + 128.0)
    return max(0, min(255, result))


class UnifiedControlGUI:
    """Unified control GUI with clean mode switching."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Unified Robot Control V2")
        self.root.configure(bg='#2b2b2b')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # BLE setup (direct like aruco_navigation.py)
        self.ble_device_name = "BLE_Sensor_Hub"
        self.ble_service_uuid = "12345678-1234-5678-1234-56789abcdef0"
        self.ble_throttle_uuid = "12345678-1234-5678-1234-56789abcdef2"
        self.ble_steering_uuid = "12345678-1234-5678-1234-56789abcdef3"
        self.ble_omega_uuid = "12345678-1234-5678-1234-56789abcdef4"
        self.ble_waypoint_uuid = "12345678-1234-5678-1234-56789abcdef5"
        
        self.ble_client = None
        self.ble_connected = False
        self.loop = None
        self.running = True
        
        # Current command values (like aruco_navigation.py)
        self.current_throttle = 0.0
        self.current_steering = 0.0
        self.current_omega = 0.0
        
        # Current mode state
        self.current_mode = None  # None, "manual", "waypoint", "aruco", "color"
        self.mode_task = None  # Current mode's asyncio task
        
        # Manual control state
        self.manual_scales = load_scales()
        
        # Waypoint dimensions
        self.max_x = 180.0
        self.max_y = 120.0
        
        # Camera and navigation state
        self.camera_cap = None
        self.frame_width = None
        self.frame_height = None
        self.aruco_detector = None
        
        # Filter state
        self.filter_type = "color"  # color or canny
        
        # Navigation config
        self.nav_config = self.load_nav_config()
        
        # Build UI
        self.build_ui()
        
        # Bind keyboard shortcuts
        self.root.bind('1', lambda e: self.request_mode_change('manual'))
        self.root.bind('2', lambda e: self.request_mode_change('waypoint'))
        self.root.bind('3', lambda e: self.request_mode_change('aruco'))
        self.root.bind('4', lambda e: self.request_mode_change('color'))
        self.root.bind('5', lambda e: self.request_mode_change('filter'))
        self.root.bind('<Escape>', lambda e: self.request_mode_change(None))
        
        # Start asyncio loop
        self.start_async_loop()
    
    def load_nav_config(self):
        """Load navigation configuration from config.yaml."""
        config_path = Path(__file__).parent.parent / "on_board_cam" / "config.yaml"
        if not config_path.exists():
            return self.default_nav_config()
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except:
            return self.default_nav_config()
    
    def default_nav_config(self):
        """Return default navigation configuration."""
        return {
            'camera': {'url': 0, 'buffer_size': 1},
            'aruco': {
                'dictionary_type': 'DICT_6X6_250',
                'marker_size_cm': 15.8,
                'focal_length_px': 490.20
            },
            'navigation': {
                'target_distance_cm': 50.0,
                'distance_tolerance_cm': 5.0,
                'max_steering': 0.6,
                'steering_kp': 0.003,
                'base_throttle': 0.3,
                'steering_dead_zone': 0.1,
                'steering_quantization': 0.05
            },
            'color_tracking': {
                'hsv_lower': [0, 120, 70],
                'hsv_upper': [10, 255, 255],
                'min_contour_area': 500,
                'target_area_ratio': 0.05
            }
        }
    
    def build_ui(self):
        """Build the main UI."""
        # Top frame - BLE status and mode buttons
        top_frame = tk.Frame(self.root, bg='#2b2b2b')
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        # BLE status
        self.ble_status_label = tk.Label(
            top_frame, 
            text="BLE: Disconnected", 
            font=("Arial", 12, "bold"),
            fg="#ff4444",
            bg='#2b2b2b'
        )
        self.ble_status_label.pack(side=tk.LEFT, padx=10)
        
        # Mode buttons
        tk.Label(
            top_frame, 
            text="Mode (1-4/ESC):", 
            font=("Arial", 12),
            fg="white",
            bg='#2b2b2b'
        ).pack(side=tk.LEFT, padx=(20, 5))
        
        button_frame = tk.Frame(top_frame, bg='#2b2b2b')
        button_frame.pack(side=tk.LEFT, padx=5)
        
        modes = [
            ("1: Manual", "manual", MANUAL_CONTROL_AVAILABLE),
            ("2: Waypoint", "waypoint", True),
            ("3: ArUco Nav", "aruco", NAVIGATION_AVAILABLE),
            ("4: Color Nav", "color", NAVIGATION_AVAILABLE),
            ("5: Filters", "filter", NAVIGATION_AVAILABLE),
            ("ESC: Stop", None, True)
        ]
        
        for text, mode, enabled in modes:
            color = "#4CAF50" if mode else "#f44336"
            btn = tk.Button(
                button_frame,
                text=text,
                command=lambda m=mode: self.request_mode_change(m),
                font=("Arial", 10, "bold"),
                fg="white",
                bg=color,
                activebackground=color,
                state=tk.NORMAL if enabled else tk.DISABLED,
                width=12
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Current mode label
        self.mode_label = tk.Label(
            top_frame,
            text="Mode: STOPPED",
            font=("Arial", 14, "bold"),
            fg="#ffaa00",
            bg='#2b2b2b'
        )
        self.mode_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content frame
        self.content_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create all panels
        self.create_manual_panel()
        self.create_waypoint_panel()
        self.create_navigation_panel()
        self.create_filter_panel()
        
        # Show stop message initially
        self.show_stop_panel()
    
    def create_manual_panel(self):
        """Create manual control panel."""
        self.manual_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        tk.Label(
            self.manual_panel,
            text="Manual Control Mode",
            font=("Arial", 18, "bold"),
            fg="#4CAF50",
            bg='#2b2b2b'
        ).pack(pady=20)
        
        instructions = [
            "Controls:",
            "  W/S - Throttle Forward/Backward",
            "  A/D - Steering Left/Right",
            "  Q/E - Omega Rotate Left/Right",
            "  X - Toggle LED",
            "  ESC - Emergency Stop"
        ]
        
        for text in instructions:
            tk.Label(
                self.manual_panel,
                text=text,
                font=("Arial", 12),
                fg="white",
                bg='#2b2b2b',
                anchor='w'
            ).pack(pady=2)
        
        # Status display
        status_frame = tk.Frame(self.manual_panel, bg='#2b2b2b')
        status_frame.pack(pady=20)
        
        self.throttle_label = tk.Label(
            status_frame, text="Throttle: 0.00",
            font=("Arial", 14), fg="cyan", bg='#2b2b2b'
        )
        self.throttle_label.pack(pady=5)
        
        self.steering_label = tk.Label(
            status_frame, text="Steering: 0.00",
            font=("Arial", 14), fg="cyan", bg='#2b2b2b'
        )
        self.steering_label.pack(pady=5)
        
        self.omega_label = tk.Label(
            status_frame, text="Omega: 0.00",
            font=("Arial", 14), fg="cyan", bg='#2b2b2b'
        )
        self.omega_label.pack(pady=5)
    
    def create_waypoint_panel(self):
        """Create waypoint panel."""
        self.waypoint_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        tk.Label(
            self.waypoint_panel,
            text="Waypoint Mode - Click to Set Target",
            font=("Arial", 18, "bold"),
            fg="#4CAF50",
            bg='#2b2b2b'
        ).pack(pady=10)
        
        # Canvas for waypoint visualization
        self.waypoint_canvas = tk.Canvas(
            self.waypoint_panel,
            width=600,
            height=400,
            bg='#1a1a1a',
            highlightthickness=0
        )
        self.waypoint_canvas.pack(pady=10)
        self.waypoint_canvas.bind('<Button-1>', self.on_waypoint_click)
        
        # Status label
        self.waypoint_status = tk.Label(
            self.waypoint_panel,
            text="Click on canvas to send waypoint",
            font=("Arial", 12),
            fg="cyan",
            bg='#2b2b2b'
        )
        self.waypoint_status.pack(pady=10)
    
    def create_navigation_panel(self):
        """Create navigation panel (shared by ArUco and Color modes)."""
        self.navigation_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        self.nav_title_label = tk.Label(
            self.navigation_panel,
            text="Navigation Mode",
            font=("Arial", 18, "bold"),
            fg="#4CAF50",
            bg='#2b2b2b'
        )
        self.nav_title_label.pack(pady=10)
        
        # Camera view canvas
        self.nav_canvas = tk.Canvas(
            self.navigation_panel,
            width=800,
            height=600,
            bg='#1a1a1a',
            highlightthickness=0
        )
        self.nav_canvas.pack(pady=10)
        
        # Status label
        self.nav_status = tk.Label(
            self.navigation_panel,
            text="Status: Initializing...",
            font=("Arial", 12),
            fg="cyan",
            bg='#2b2b2b'
        )
        self.nav_status.pack(pady=10)
    
    def create_filter_panel(self):
        """Create filter panel."""
        self.filter_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        self.filter_title_label = tk.Label(
            self.filter_panel,
            text="Filter View Mode",
            font=("Arial", 18, "bold"),
            fg="#4CAF50",
            bg='#2b2b2b'
        )
        self.filter_title_label.pack(pady=10)
        
        # Filter type selector
        filter_frame = tk.Frame(self.filter_panel, bg='#2b2b2b')
        filter_frame.pack(pady=5)
        
        tk.Label(
            filter_frame,
            text="Filter Type:",
            font=("Arial", 12),
            fg="white",
            bg='#2b2b2b'
        ).pack(side=tk.LEFT, padx=5)
        
        self.filter_type_var = tk.StringVar(value="color")
        
        tk.Radiobutton(
            filter_frame,
            text="Color Mask",
            variable=self.filter_type_var,
            value="color",
            command=self.on_filter_type_change,
            font=("Arial", 10),
            fg="white",
            bg='#2b2b2b',
            selectcolor='#404040',
            activebackground='#2b2b2b',
            activeforeground='white'
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            filter_frame,
            text="Canny Edge",
            variable=self.filter_type_var,
            value="canny",
            command=self.on_filter_type_change,
            font=("Arial", 10),
            fg="white",
            bg='#2b2b2b',
            selectcolor='#404040',
            activebackground='#2b2b2b',
            activeforeground='white'
        ).pack(side=tk.LEFT, padx=5)
        
        # Camera view canvas
        self.filter_canvas = tk.Canvas(
            self.filter_panel,
            width=800,
            height=600,
            bg='#1a1a1a',
            highlightthickness=0
        )
        self.filter_canvas.pack(pady=10)
        
        # Status label
        self.filter_status = tk.Label(
            self.filter_panel,
            text="Status: Ready",
            font=("Arial", 12),
            fg="cyan",
            bg='#2b2b2b'
        )
        self.filter_status.pack(pady=10)
    
    def on_filter_type_change(self):
        """Handle filter type change."""
        self.filter_type = self.filter_type_var.get()
        print(f"Filter type changed to: {self.filter_type}")
    
    def show_stop_panel(self):
        """Show the stop/idle panel."""
        # Hide all panels
        self.manual_panel.pack_forget()
        self.waypoint_panel.pack_forget()
        self.navigation_panel.pack_forget()
        
        # Create/show stop panel
        if not hasattr(self, 'stop_panel'):
            self.stop_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
            
            tk.Label(
                self.stop_panel,
                text="⏹ ALL MODES STOPPED",
                font=("Arial", 24, "bold"),
                fg="#f44336",
                bg='#2b2b2b'
            ).pack(pady=100)
            
            tk.Label(
                self.stop_panel,
                text="Select a mode to start:\n\n1 - Manual Control\n2 - Waypoint\n3 - ArUco Navigation\n4 - Color Navigation\n5 - Filter View",
                font=("Arial", 14),
                fg="white",
                bg='#2b2b2b',
                justify='center'
            ).pack(pady=20)
        
        self.stop_panel.pack(fill=tk.BOTH, expand=True)
    
    def request_mode_change(self, new_mode):
        """Request a mode change (async safe)."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.change_mode(new_mode),
                self.loop
            )
    
    async def change_mode(self, new_mode):
        """Change operational mode (stops old, starts new)."""
        if new_mode == self.current_mode:
            return  # Already in this mode
        
        print(f"\n{'='*60}")
        print(f"MODE CHANGE: {self.current_mode or 'STOPPED'} → {new_mode or 'STOPPED'}")
        print(f"{'='*60}\n")
        
        # Step 1: Stop current mode
        if self.mode_task:
            print(f"[Stopping {self.current_mode} mode...]")
            self.mode_task.cancel()
            try:
                await self.mode_task
            except asyncio.CancelledError:
                pass
            self.mode_task = None
        
        # Step 2: Send stop commands to robot
        print("[Sending stop commands...]")
        self.send_motor_command(0.0, 0.0, 0.0)
        await asyncio.sleep(0.2)  # Give BLE sender time to transmit
        
        # Step 3: Release camera ONLY if switching to non-camera mode
        # Keep camera open when switching between aruco/color/filter modes
        old_needs_camera = self.current_mode in ["aruco", "color", "filter"]
        new_needs_camera = new_mode in ["aruco", "color", "filter"]
        
        if old_needs_camera and not new_needs_camera:
            # Switching from camera mode to non-camera mode
            if self.camera_cap:
                print("[Releasing camera...]")
                self.camera_cap.release()
                self.camera_cap = None
                self.frame_width = None
                self.frame_height = None
        elif not old_needs_camera and new_needs_camera:
            # Switching from non-camera mode to camera mode
            print("[Camera will be initialized...]")
        else:
            # Both modes use camera or neither uses camera - keep current state
            if new_needs_camera and self.camera_cap:
                print("[Reusing existing camera connection]")
        
        self.current_mode = new_mode
        
        # Step 4: Update UI
        self.root.after(0, self.update_mode_ui)
        
        # Step 5: Start new mode
        if new_mode is None:
            print("[All modes stopped]\n")
        elif new_mode == "manual":
            print("[Starting Manual Control mode...]")
            self.mode_task = asyncio.create_task(self.manual_control_loop())
        elif new_mode == "waypoint":
            print("[Waypoint mode ready]")
            # Waypoint is event-driven, no continuous loop needed
        elif new_mode == "aruco":
            print("[Starting ArUco Navigation mode...]")
            # Init camera only if not already open
            if not self.camera_cap:
                if not await self.init_camera():
                    messagebox.showerror("Camera Error", "Failed to open camera for ArUco navigation")
                    await self.change_mode(None)
                    return
            # Init ArUco detector if needed
            self.init_aruco_detector()
            self.mode_task = asyncio.create_task(self.aruco_navigation_loop())
        elif new_mode == "color":
            print("[Starting Color Navigation mode...]")
            # Init camera only if not already open
            if not self.camera_cap:
                if not await self.init_camera():
                    messagebox.showerror("Camera Error", "Failed to open camera for Color navigation")
                    await self.change_mode(None)
                    return
            self.mode_task = asyncio.create_task(self.color_navigation_loop())
        elif new_mode == "filter":
            print("[Starting Filter View mode...]")
            # Init camera only if not already open
            if not self.camera_cap:
                if not await self.init_camera():
                    messagebox.showerror("Camera Error", "Failed to open camera for Filter view")
                    await self.change_mode(None)
                    return
            self.mode_task = asyncio.create_task(self.filter_view_loop())
    
    def update_mode_ui(self):
        """Update UI to reflect current mode."""
        # Hide all panels
        self.manual_panel.pack_forget()
        self.waypoint_panel.pack_forget()
        self.navigation_panel.pack_forget()
        self.filter_panel.pack_forget()
        if hasattr(self, 'stop_panel'):
            self.stop_panel.pack_forget()
        
        # Show appropriate panel
        if self.current_mode is None:
            self.mode_label.config(text="Mode: STOPPED", fg="#f44336")
            self.show_stop_panel()
        elif self.current_mode == "manual":
            self.mode_label.config(text="Mode: MANUAL CONTROL", fg="#4CAF50")
            self.manual_panel.pack(fill=tk.BOTH, expand=True)
        elif self.current_mode == "waypoint":
            self.mode_label.config(text="Mode: WAYPOINT", fg="#2196F3")
            self.waypoint_panel.pack(fill=tk.BOTH, expand=True)
            self.draw_waypoint_grid()
        elif self.current_mode == "aruco":
            self.mode_label.config(text="Mode: ARUCO NAVIGATION", fg="#FF9800")
            self.nav_title_label.config(text="ArUco Marker Navigation")
            self.navigation_panel.pack(fill=tk.BOTH, expand=True)
        elif self.current_mode == "color":
            self.mode_label.config(text="Mode: COLOR NAVIGATION", fg="#9C27B0")
            self.nav_title_label.config(text="Color Target Navigation")
            self.navigation_panel.pack(fill=tk.BOTH, expand=True)
        elif self.current_mode == "filter":
            self.mode_label.config(text="Mode: FILTER VIEW", fg="#E91E63")
            self.filter_panel.pack(fill=tk.BOTH, expand=True)
    
    async def init_camera(self):
        """Initialize camera (blocking). Returns True if camera is open."""
        if self.camera_cap is not None:
            print("✓ Camera already open")
            return True
        
        print("Opening camera...")
        camera_url = self.nav_config['camera'].get('url', 0)
        
        # Run camera init in thread executor to avoid blocking
        def open_camera():
            cap = cv2.VideoCapture(camera_url)
            if not cap.isOpened():
                return None
            # Test read
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return None
            return cap
        
        self.camera_cap = await asyncio.get_event_loop().run_in_executor(
            None, open_camera
        )
        
        if self.camera_cap is None:
            print("✗ Failed to open camera")
            return False
        
        # Get frame dimensions
        ret, frame = self.camera_cap.read()
        if ret:
            self.frame_height, self.frame_width = frame.shape[:2]
            print(f"✓ Camera opened: {self.frame_width}x{self.frame_height}")
        
        return True
    
    def init_aruco_detector(self):
        """Initialize ArUco detector."""
        if self.aruco_detector is None:
            aruco_cfg = self.nav_config['aruco']
            self.aruco_detector = ArucoDetector(
                aruco_dict_type=aruco_cfg['dictionary_type'],
                marker_size_cm=aruco_cfg['marker_size_cm'],
                focal_length_px=aruco_cfg['focal_length_px']
            )
            print("✓ ArUco detector initialized")
    
    def send_motor_command(self, throttle, steering, omega=0.0):
        """
        Update motor command values (non-blocking).
        Background BLE sender task will transmit them.
        
        Args:
            throttle: -1.0 to +1.0
            steering: -1.0 to +1.0
            omega: -1.0 to +1.0
        """
        self.current_throttle = max(-1.0, min(1.0, throttle))
        self.current_steering = max(-1.0, min(1.0, steering))
        self.current_omega = max(-1.0, min(1.0, omega))
    
    # ========== MODE LOOPS ==========
    
    async def manual_control_loop(self):
        """Manual control mode loop."""
        if not MANUAL_CONTROL_AVAILABLE:
            print("✗ Manual control not available")
            return
        
        throttle_scale, steering_scale, omega_scale = self.manual_scales
        
        print("✓ Manual control active")
        
        try:
            while self.current_mode == "manual":
                # Get inputs
                throttle = inp.get_bipolar_ctrl('w', 's') * throttle_scale
                steering = inp.get_bipolar_ctrl('d', 'a') * steering_scale
                omega = inp.get_bipolar_ctrl('e', 'q') * omega_scale
                
                # Update commands (background task will send)
                self.send_motor_command(throttle, steering, omega)
                
                # Update UI
                self.root.after(0, lambda t=throttle, s=steering, o=omega: 
                              self.update_manual_display(t, s, o))
                
                # Fast loop - minimal delay
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            print("✓ Manual control stopped")
            raise
    
    def update_manual_display(self, throttle, steering, omega):
        """Update manual control display."""
        self.throttle_label.config(text=f"Throttle: {throttle:+.2f}")
        self.steering_label.config(text=f"Steering: {steering:+.2f}")
        self.omega_label.config(text=f"Omega: {omega:+.2f}")
    
    async def aruco_navigation_loop(self):
        """ArUco navigation mode loop (matches aruco_navigation.py logic)."""
        print("✓ ArUco navigation active")
        
        nav_cfg = self.nav_config['navigation']
        target_distance = nav_cfg['target_distance_cm']
        tolerance = nav_cfg['distance_tolerance_cm']
        max_steering = nav_cfg['max_steering']
        steering_kp = nav_cfg['steering_kp']
        base_throttle = nav_cfg['base_throttle']
        dead_zone = nav_cfg['steering_dead_zone']
        
        try:
            while self.current_mode == "aruco":
                if not self.camera_cap:
                    await asyncio.sleep(0.1)
                    continue
                
                ret, frame = self.camera_cap.read()
                if not ret or frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Detect ArUco markers
                corners, ids, _ = self.aruco_detector.detect(frame)
                
                throttle = 0.0
                steering = 0.0
                
                if ids is not None and len(ids) > 0:
                    # Get first marker
                    marker_info = self.aruco_detector.get_marker_info(corners, ids)[0]
                    distance_cm = marker_info['distance_cm']
                    center_x = marker_info['center_x']
                    marker_id = marker_info['id']
                    
                    # Draw detections
                    frame = self.aruco_detector.draw_detections(
                        frame, corners, ids,
                        show_distance=True, show_id=True
                    )
                    
                    # Calculate steering
                    frame_center = self.frame_width / 2.0
                    error = center_x - frame_center
                    steering = error * steering_kp
                    
                    # Apply dead zone
                    if abs(steering) < dead_zone:
                        steering = 0.0
                    
                    # Clamp steering
                    steering = max(-max_steering, min(max_steering, steering))
                    
                    # Calculate throttle
                    distance_error = distance_cm - target_distance
                    if abs(distance_error) > tolerance:
                        throttle = base_throttle if distance_error > 0 else -base_throttle * 0.5
                        # Invert steering when backing up
                        if throttle < 0:
                            steering = -steering
                    
                    # Status overlay
                    status = [
                        f"ID: {marker_id} | Dist: {distance_cm:.1f}cm",
                        f"Target: {target_distance:.1f}cm | Error: {distance_error:+.1f}cm",
                        f"Throttle: {throttle:+.2f} | Steering: {steering:+.2f}"
                    ]
                    
                    y = 30
                    for text in status:
                        cv2.putText(frame, text, (10, y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        y += 25
                    
                    # Draw center line and marker
                    cv2.line(frame, (int(frame_center), 0),
                            (int(frame_center), self.frame_height), (255, 0, 0), 2)
                    cv2.circle(frame, (int(center_x), int(marker_info['center_y'])),
                              5, (0, 255, 255), -1)
                else:
                    # No marker - stop
                    cv2.putText(frame, "NO MARKER - STOPPED",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                # Send commands (non-blocking - background task handles BLE)
                self.send_motor_command(throttle, steering)
                
                # Display frame
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (800, 600))
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)
                self.root.after(0, lambda i=imgtk: self.update_nav_canvas(i))
                
                await asyncio.sleep(0.001)  # Fast loop for real-time camera
        
        except asyncio.CancelledError:
            print("✓ ArUco navigation stopped")
            raise
    
    async def color_navigation_loop(self):
        """Color navigation mode loop."""
        print("✓ Color navigation active")
        
        color_cfg = self.nav_config['color_tracking']
        hsv_lower = np.array(color_cfg['hsv_lower'])
        hsv_upper = np.array(color_cfg['hsv_upper'])
        min_area = color_cfg['min_contour_area']
        
        nav_cfg = self.nav_config['navigation']
        max_steering = nav_cfg['max_steering']
        steering_kp = nav_cfg['steering_kp']
        base_throttle = nav_cfg['base_throttle']
        dead_zone = nav_cfg['steering_dead_zone']
        
        try:
            while self.current_mode == "color":
                if not self.camera_cap:
                    await asyncio.sleep(0.1)
                    continue
                
                ret, frame = self.camera_cap.read()
                if not ret or frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Detect color
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                throttle = 0.0
                steering = 0.0
                
                if contours:
                    # Find largest contour
                    largest = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest)
                    
                    if area > min_area:
                        # Get centroid
                        M = cv2.moments(largest)
                        if M["m00"] > 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            
                            # Draw contour and center
                            cv2.drawContours(frame, [largest], -1, (0, 255, 0), 3)
                            cv2.circle(frame, (cx, cy), 10, (0, 255, 255), -1)
                            
                            # Calculate steering
                            frame_center = self.frame_width / 2.0
                            error = cx - frame_center
                            steering = error * steering_kp
                            
                            if abs(steering) < dead_zone:
                                steering = 0.0
                            
                            steering = max(-max_steering, min(max_steering, steering))
                            
                            # Simple throttle based on area
                            throttle = base_throttle
                            
                            # Status
                            cv2.putText(frame, f"Target Found | Area: {area:.0f}",
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                            cv2.putText(frame, f"Throttle: {throttle:+.2f} | Steering: {steering:+.2f}",
                                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            
                            # Draw center line
                            cv2.line(frame, (int(frame_center), 0),
                                    (int(frame_center), self.frame_height), (255, 0, 0), 2)
                
                if throttle == 0.0:
                    cv2.putText(frame, "NO TARGET - STOPPED",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                # Send commands (non-blocking)
                self.send_motor_command(throttle, steering)
                
                # Display frame
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (800, 600))
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)
                self.root.after(0, lambda i=imgtk: self.update_nav_canvas(i))
                
                await asyncio.sleep(0.001)  # Fast loop for real-time camera
        
        except asyncio.CancelledError:
            print("✓ Color navigation stopped")
            raise
    
    async def filter_view_loop(self):
        """Filter view mode loop (visualization only, no control)."""
        print("✓ Filter view active")
        
        color_cfg = self.nav_config['color_tracking']
        hsv_lower = np.array(color_cfg['hsv_lower'])
        hsv_upper = np.array(color_cfg['hsv_upper'])
        
        try:
            while self.current_mode == "filter":
                if not self.camera_cap:
                    await asyncio.sleep(0.1)
                    continue
                
                ret, frame = self.camera_cap.read()
                if not ret or frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Apply selected filter
                if self.filter_type == "color":
                    # HSV color mask
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
                    
                    # Apply mask to original frame
                    result = cv2.bitwise_and(frame, frame, mask=mask)
                    
                    # Add text overlay
                    cv2.putText(result, "Color Mask Filter (HSV)",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(result, f"Lower: {hsv_lower.tolist()}",
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(result, f"Upper: {hsv_upper.tolist()}",
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                elif self.filter_type == "canny":
                    # Canny edge detection
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray, 50, 150)
                    result = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                    
                    # Add text overlay
                    cv2.putText(result, "Canny Edge Detection",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(result, "Threshold: (50, 150)",
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Display frame
                frame_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (800, 600))
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)
                self.root.after(0, lambda i=imgtk: self.update_filter_canvas(i))
                
                await asyncio.sleep(0.001)  # Fast loop
        
        except asyncio.CancelledError:
            print("✓ Filter view stopped")
            raise
    
    def update_nav_canvas(self, imgtk):
        """Update navigation canvas."""
        self.nav_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.nav_canvas.image = imgtk
    
    def update_filter_canvas(self, imgtk):
        """Update filter canvas."""
        self.filter_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.filter_canvas.image = imgtk
    
    # ========== WAYPOINT MODE ==========
    
    def draw_waypoint_grid(self):
        """Draw the waypoint workspace grid."""
        canvas = self.waypoint_canvas
        canvas.delete("all")
        
        w = canvas.winfo_reqwidth()
        h = canvas.winfo_reqheight()
        
        # Draw grid
        for i in range(0, w, 50):
            canvas.create_line(i, 0, i, h, fill='#333333')
        for i in range(0, h, 50):
            canvas.create_line(0, i, w, i, fill='#333333')
        
        # Draw axes
        canvas.create_line(0, h, w, h, fill='#00ff00', width=2)
        canvas.create_line(0, 0, 0, h, fill='#00ff00', width=2)
        
        # Labels
        canvas.create_text(w-10, h-10, text=f"{self.max_x}cm", fill='white', anchor='se')
        canvas.create_text(10, 10, text=f"{self.max_y}cm", fill='white', anchor='nw')
    
    def on_waypoint_click(self, event):
        """Handle waypoint canvas click."""
        if self.current_mode != "waypoint":
            return
        
        canvas = self.waypoint_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        
        # Convert click to cm coordinates
        x_cm = (event.x / w) * self.max_x
        y_cm = ((h - event.y) / h) * self.max_y  # Flip Y axis
        
        # Clear previous waypoint markers and redraw grid
        self.draw_waypoint_grid()
        
        # Draw new marker
        canvas.create_oval(event.x-5, event.y-5, event.x+5, event.y+5,
                          fill='red', outline='yellow', width=2)
        canvas.create_text(event.x, event.y-15, text=f"({x_cm:.1f}, {y_cm:.1f})",
                          fill='yellow', font=("Arial", 10, "bold"))
        
        # Send waypoint
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.send_waypoint(x_cm, y_cm),
                self.loop
            )
    
    async def send_waypoint(self, x, y):
        """Send waypoint to robot."""
        omega = 0.0
        
        if not self.ble_client or not self.ble_client.is_connected:
            if BLEAK_AVAILABLE:
                msg = f"⚠ BLE not connected - waypoint not sent: ({x:.1f}, {y:.1f}, {omega:.1f})"
                print(msg, flush=True)
                self.waypoint_status.config(text="⚠ BLE not connected", fg="red")
            else:
                msg = f"[SIM] Waypoint sent: x={x:.1f}cm, y={y:.1f}cm, omega={omega:.1f}"
                print(msg, flush=True)
                self.waypoint_status.config(text=f"[SIM] Waypoint: ({x:.1f}, {y:.1f})", fg="orange")
            return
        
        try:
            # Encode waypoint (6 bytes: x, y, omega as int16 with ×10 scaling)
            # Matches TE2004B/ble_controller/ble_client.py set_waypoint()
            x_mm = int(x * 10)  # cm to mm (×10 scaling)
            y_mm = int(y * 10)  # cm to mm (×10 scaling)
            omega_dec = int(omega * 10)  # degrees with ×10 scaling
            
            data = bytearray([
                x_mm & 0xFF, (x_mm >> 8) & 0xFF,
                y_mm & 0xFF, (y_mm >> 8) & 0xFF,
                omega_dec & 0xFF, (omega_dec >> 8) & 0xFF
            ])
            
            await self.ble_client.write_gatt_char(self.ble_waypoint_uuid, data)
            
            msg = f"[BLE TX] Waypoint sent: x={x:.1f}cm, y={y:.1f}cm, omega={omega:.1f} (bytes: {list(data)})"
            print(msg, flush=True)
            self.waypoint_status.config(text=f"✓ Waypoint: ({x:.1f}, {y:.1f}) cm", fg="green")
        except Exception as e:
            msg = f"✗ Waypoint error: {e}"
            print(msg, flush=True)
            self.waypoint_status.config(text=f"✗ Error: {e}", fg="red")
    
    # ========== ASYNC SETUP ==========
    
    def start_async_loop(self):
        """Start asyncio event loop in background thread."""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.async_main())
        
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
    
    async def async_main(self):
        """Main async loop - handles BLE connection and background sending."""
        # Try to connect to BLE
        if BLEAK_AVAILABLE:
            try:
                print(f"Scanning for {self.ble_device_name}...")
                devices = await BleakScanner.discover(timeout=3.0)
                device = next((d for d in devices if d.name == self.ble_device_name), None)
                
                if device:
                    print(f"Found at {device.address}, connecting...")
                    self.ble_client = BleakClient(device.address)
                    await self.ble_client.connect()
                    
                    if self.ble_client.is_connected:
                        self.ble_connected = True
                        self.root.after(0, lambda: self.ble_status_label.config(
                            text="BLE: Connected", fg="#00ff00"
                        ))
                        print("✓ BLE connected")
                    else:
                        print("⚠ Connection failed - simulation mode")
                        self.ble_client = None
                else:
                    print("⚠ Device not found - simulation mode")
                    self.root.after(0, lambda: self.ble_status_label.config(
                        text="BLE: Simulation", fg="#ffaa00"
                    ))
            except Exception as e:
                print(f"⚠ BLE error: {e} - simulation mode")
                self.ble_client = None
        else:
            print("⚠ BLE not available - simulation mode")
            self.root.after(0, lambda: self.ble_status_label.config(
                text="BLE: Simulation", fg="#ffaa00"
            ))
        
        # Start background BLE sender task (like aruco_navigation.py)
        sender_task = asyncio.create_task(self._ble_sender_task())
        
        # Keep alive
        try:
            while self.running:
                await asyncio.sleep(0.1)
        finally:
            sender_task.cancel()
            if self.ble_client and self.ble_client.is_connected:
                await self.ble_client.disconnect()
    
    async def _ble_sender_task(self):
        """Background task for sending BLE commands at 4Hz (matches aruco_navigation.py)."""
        last_throttle_byte = None
        last_steering_byte = None
        last_omega_byte = None
        
        print("✓ BLE sender task started")
        
        while self.running:
            try:
                if self.ble_client and self.ble_client.is_connected:
                    throttle_byte = to_byte(self.current_throttle)
                    steering_byte = to_byte(self.current_steering)
                    omega_byte = to_byte(self.current_omega)
                    
                    # Only send if values changed
                    if (throttle_byte != last_throttle_byte or 
                        steering_byte != last_steering_byte or
                        omega_byte != last_omega_byte):
                        
                        await self.ble_client.write_gatt_char(self.ble_throttle_uuid, bytearray([throttle_byte]))
                        await self.ble_client.write_gatt_char(self.ble_steering_uuid, bytearray([steering_byte]))
                        await self.ble_client.write_gatt_char(self.ble_omega_uuid, bytearray([omega_byte]))
                        
                        print(f"[BLE TX] Throttle: {self.current_throttle:+.2f} ({throttle_byte:3d}) | "
                              f"Steering: {self.current_steering:+.2f} ({steering_byte:3d}) | "
                              f"Omega: {self.current_omega:+.2f} ({omega_byte:3d})", flush=True)
                        
                        last_throttle_byte = throttle_byte
                        last_steering_byte = steering_byte
                        last_omega_byte = omega_byte
                elif not BLEAK_AVAILABLE or (self.ble_client is None):
                    # Simulation mode - print commands if they changed
                    throttle_byte = to_byte(self.current_throttle)
                    steering_byte = to_byte(self.current_steering)
                    omega_byte = to_byte(self.current_omega)
                    
                    if (throttle_byte != last_throttle_byte or 
                        steering_byte != last_steering_byte or
                        omega_byte != last_omega_byte):
                        
                        print(f"[SIM] Throttle: {self.current_throttle:+.2f} ({throttle_byte:3d}) | "
                              f"Steering: {self.current_steering:+.2f} ({steering_byte:3d}) | "
                              f"Omega: {self.current_omega:+.2f} ({omega_byte:3d})", flush=True)
                        
                        last_throttle_byte = throttle_byte
                        last_steering_byte = steering_byte
                        last_omega_byte = omega_byte
                
                # Send at 4Hz (250ms interval) - matches aruco_navigation.py
                await asyncio.sleep(0.25)
            except Exception as e:
                print(f"[BLE sender error: {e}]", flush=True)
                await asyncio.sleep(0.5)
        
        print(" BLE sender task stopped", flush=True)
    
    def on_close(self):
        """Handle window close."""
        print("\nShutting down...")
        self.running = False
        
        # Stop current mode and send stop commands
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.change_mode(None), self.loop)
            import time
            time.sleep(0.3)  # Give time for cleanup
        
        # Close window
        self.root.quit()
        self.root.destroy()


def main():
    """Main entry point."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    root = tk.Tk()
    app = UnifiedControlGUI(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
