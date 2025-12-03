#!/usr/bin/env python3
"""
Unified Robot Control GUI
==========================

Single GUI to control the robot with multiple modes:
1. Manual Control - Keyboard/gamepad control (WASD + QE for omega)
2. Waypoint Mode - Click to send waypoint coordinates
3. Navigation Modes - ArUco or Color following (view only, sends throttle/steering)
4. Filter View - Color/Canny filters visualization

All modes share a single BLE connection to the ESP32.
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

# Import BLE client
from ble_client import CarBLEClient

# Try to import manual control
try:
    import combined_input as inp
    MANUAL_CONTROL_AVAILABLE = True
except ImportError:
    MANUAL_CONTROL_AVAILABLE = False
    print("⚠ Manual control (combined_input) not available")

# Try to import OpenCV-based navigation
try:
    # Add navigation path
    import os
    nav_path = Path(__file__).parent.parent / "on_board_cam"
    if str(nav_path) not in sys.path:
        sys.path.insert(0, str(nav_path))
    
    from navigation.target_detectors import ArucoTargetDetector, ColorTargetDetector
    NAVIGATION_AVAILABLE = True
except ImportError as e:
    NAVIGATION_AVAILABLE = False
    print(f"⚠ Navigation modules not available: {e}")


def load_scales():
    """Load throttle/steering/omega scales from file."""
    try:
        config_path = Path(__file__).parent / "scales.txt"
        with open(config_path) as f:
            lines = f.read().strip().split('\n')
            return float(lines[0]), float(lines[1]), float(lines[2])
    except:
        return 1.0, 0.8, 0.8


class UnifiedControlGUI:
    """Unified control GUI with multiple modes."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Unified Robot Control")
        self.root.configure(bg='#2b2b2b')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # BLE setup
        self.car = None
        self.ble_connected = False
        self.loop = None
        self.running = True
        
        # Mode state
        self.current_mode = "manual"  # manual, waypoint, navigation, filter
        
        # Manual control state
        self.manual_throttle = 0.0
        self.manual_steering = 0.0
        self.manual_omega = 0.0
        
        # Waypoint workspace dimensions (cm)
        self.max_x = 180.0
        self.max_y = 120.0
        
        # Navigation state
        self.nav_detector = None
        self.nav_type = "aruco"  # aruco or color
        self.camera_cap = None
        self.nav_throttle = 0.0
        self.nav_steering = 0.0
        
        # Filter state
        self.filter_type = "color"  # color or canny
        
        # Build UI
        self.build_ui()
        
        # Bind keyboard shortcuts for mode switching
        self.root.bind('1', lambda e: self.switch_mode_key('manual'))
        self.root.bind('2', lambda e: self.switch_mode_key('waypoint'))
        self.root.bind('3', lambda e: self.switch_mode_key('navigation'))
        self.root.bind('4', lambda e: self.switch_mode_key('filter'))
        self.root.bind('<Tab>', lambda e: self.cycle_mode())
        
        # Start asyncio loop in background thread
        self.start_async_loop()
    
    def build_ui(self):
        """Build the main UI."""
        # Top frame - BLE status and mode selector
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
        
        # Mode selector
        tk.Label(
            top_frame, 
            text="Mode (1-4/Tab):", 
            font=("Arial", 12),
            fg="white",
            bg='#2b2b2b'
        ).pack(side=tk.LEFT, padx=(20, 5))
        
        self.mode_var = tk.StringVar(value="manual")
        modes = [
            ("Manual Control", "manual"),
            ("Waypoint", "waypoint"),
            ("Navigation", "navigation"),
            ("Filters", "filter")
        ]
        
        for text, mode in modes:
            enabled = True
            if mode == "manual" and not MANUAL_CONTROL_AVAILABLE:
                enabled = False
            if mode in ["navigation", "filter"] and not NAVIGATION_AVAILABLE:
                enabled = False
            
            rb = tk.Radiobutton(
                top_frame,
                text=text,
                variable=self.mode_var,
                value=mode,
                command=self.on_mode_change,
                font=("Arial", 10),
                fg="white",
                bg='#2b2b2b',
                selectcolor='#404040',
                activebackground='#2b2b2b',
                activeforeground='white',
                state=tk.NORMAL if enabled else tk.DISABLED
            )
            rb.pack(side=tk.LEFT, padx=5)
        
        # Main content frame (will switch based on mode)
        self.content_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create all mode panels (initially hidden)
        self.create_manual_panel()
        self.create_waypoint_panel()
        self.create_navigation_panel()
        self.create_filter_panel()
        
        # Show initial mode
        self.on_mode_change()
    
    def create_manual_panel(self):
        """Create manual control panel."""
        self.manual_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        # Title
        tk.Label(
            self.manual_panel,
            text="Manual Control Mode",
            font=("Arial", 16, "bold"),
            fg="white",
            bg='#2b2b2b'
        ).pack(pady=10)
        
        # Instructions
        instructions = [
            "Controls:",
            "  W/S - Forward/Backward (Throttle)",
            "  A/D - Left/Right (Steering)",
            "  Q/E - Rotate Left/Right (Omega)",
            "  X - LED Toggle",
            "  ESC - Emergency Stop",
            "",
            "Mode Switching:",
            "  1 - Manual | 2 - Waypoint | 3 - Navigation | 4 - Filters",
            "  Tab - Cycle through modes",
            "",
            "Gamepad also supported (LY=throttle, RX=steering, D-pad=omega)"
        ]
        
        inst_text = "\n".join(instructions)
        tk.Label(
            self.manual_panel,
            text=inst_text,
            font=("Arial", 11),
            fg="#aaaaaa",
            bg='#2b2b2b',
            justify=tk.LEFT
        ).pack(pady=20)
        
        # Status display
        self.manual_status_frame = tk.Frame(self.manual_panel, bg='#3b3b3b', relief=tk.SUNKEN, bd=2)
        self.manual_status_frame.pack(pady=20, padx=50, fill=tk.X)
        
        self.throttle_label = tk.Label(
            self.manual_status_frame,
            text="Throttle: 0.00",
            font=("Arial", 12),
            fg="#00ff00",
            bg='#3b3b3b'
        )
        self.throttle_label.pack(pady=5)
        
        self.steering_label = tk.Label(
            self.manual_status_frame,
            text="Steering: 0.00",
            font=("Arial", 12),
            fg="#00ff00",
            bg='#3b3b3b'
        )
        self.steering_label.pack(pady=5)
        
        self.omega_label = tk.Label(
            self.manual_status_frame,
            text="Omega: 0.00",
            font=("Arial", 12),
            fg="#00ff00",
            bg='#3b3b3b'
        )
        self.omega_label.pack(pady=5)
        
        if not MANUAL_CONTROL_AVAILABLE:
            tk.Label(
                self.manual_panel,
                text="⚠ Manual control not available (combined_input module missing)",
                font=("Arial", 10),
                fg="#ff4444",
                bg='#2b2b2b'
            ).pack(pady=10)
    
    def create_waypoint_panel(self):
        """Create waypoint selection panel."""
        self.waypoint_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        # Title and info
        title_frame = tk.Frame(self.waypoint_panel, bg='#2b2b2b')
        title_frame.pack(pady=10)
        
        tk.Label(
            title_frame,
            text=f"Waypoint Mode - Workspace: {self.max_x}cm × {self.max_y}cm",
            font=("Arial", 16, "bold"),
            fg="white",
            bg='#2b2b2b'
        ).pack()
        
        self.waypoint_status_label = tk.Label(
            title_frame,
            text="Click on the workspace to send a waypoint",
            font=("Arial", 10),
            fg="#aaaaaa",
            bg='#2b2b2b'
        )
        self.waypoint_status_label.pack(pady=5)
        
        # Canvas frame
        canvas_frame = tk.Frame(self.waypoint_panel, bg='white', relief=tk.SUNKEN, borderwidth=2)
        canvas_frame.pack(padx=20, pady=10)
        
        # Canvas for waypoint selection
        self.waypoint_canvas_width = 800
        self.waypoint_canvas_height = 600
        
        self.waypoint_canvas = tk.Canvas(
            canvas_frame,
            width=self.waypoint_canvas_width,
            height=self.waypoint_canvas_height,
            bg="white",
            highlightthickness=0
        )
        self.waypoint_canvas.pack()
        self.waypoint_canvas.bind("<Button-1>", self.on_waypoint_click)
        
        # Draw grid and labels
        self.draw_waypoint_grid()
    
    def draw_waypoint_grid(self):
        """Draw grid and labels on waypoint canvas."""
        w = self.waypoint_canvas_width
        h = self.waypoint_canvas_height
        
        # Border
        self.waypoint_canvas.create_rectangle(2, 2, w-2, h-2, outline="black", width=2)
        
        # Center lines
        self.waypoint_canvas.create_line(0, h/2, w, h/2, fill="lightgray", dash=(5, 5))
        self.waypoint_canvas.create_line(w/2, 0, w/2, h, fill="lightgray", dash=(5, 5))
        
        # Corner labels
        self.waypoint_canvas.create_text(10, h-10, text="(0, 0)", anchor='sw', fill='gray', font=("Arial", 9))
        self.waypoint_canvas.create_text(w-10, h-10, text=f"({self.max_x:.0f}, 0)", anchor='se', fill='gray', font=("Arial", 9))
        self.waypoint_canvas.create_text(10, 10, text=f"(0, {self.max_y:.0f})", anchor='nw', fill='gray', font=("Arial", 9))
        self.waypoint_canvas.create_text(w-10, 10, text=f"({self.max_x:.0f}, {self.max_y:.0f})", anchor='ne', fill='gray', font=("Arial", 9))
    
    def create_navigation_panel(self):
        """Create navigation mode panel (ArUco/Color following)."""
        self.navigation_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        # Title and controls
        title_frame = tk.Frame(self.navigation_panel, bg='#2b2b2b')
        title_frame.pack(pady=10)
        
        tk.Label(
            title_frame,
            text="Navigation Mode",
            font=("Arial", 16, "bold"),
            fg="white",
            bg='#2b2b2b'
        ).pack()
        
        # Navigation type selector
        nav_control_frame = tk.Frame(self.navigation_panel, bg='#2b2b2b')
        nav_control_frame.pack(pady=10)
        
        tk.Label(
            nav_control_frame,
            text="Target:",
            font=("Arial", 12),
            fg="white",
            bg='#2b2b2b'
        ).pack(side=tk.LEFT, padx=10)
        
        self.nav_type_var = tk.StringVar(value="aruco")
        
        tk.Radiobutton(
            nav_control_frame,
            text="ArUco Marker",
            variable=self.nav_type_var,
            value="aruco",
            command=self.on_nav_type_change,
            font=("Arial", 10),
            fg="white",
            bg='#2b2b2b',
            selectcolor='#404040',
            activebackground='#2b2b2b',
            activeforeground='white'
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            nav_control_frame,
            text="Color Target",
            variable=self.nav_type_var,
            value="color",
            command=self.on_nav_type_change,
            font=("Arial", 10),
            fg="white",
            bg='#2b2b2b',
            selectcolor='#404040',
            activebackground='#2b2b2b',
            activeforeground='white'
        ).pack(side=tk.LEFT, padx=5)
        
        # Camera view
        self.nav_canvas = tk.Canvas(
            self.navigation_panel,
            width=640,
            height=480,
            bg="black",
            highlightthickness=0
        )
        self.nav_canvas.pack(pady=10)
        
        # Status
        self.nav_status_label = tk.Label(
            self.navigation_panel,
            text="Throttle: 0.00 | Steering: 0.00",
            font=("Arial", 12),
            fg="#00ff00",
            bg='#2b2b2b'
        )
        self.nav_status_label.pack(pady=10)
        
        if not NAVIGATION_AVAILABLE:
            tk.Label(
                self.navigation_panel,
                text="⚠ Navigation not available (camera modules missing)",
                font=("Arial", 10),
                fg="#ff4444",
                bg='#2b2b2b'
            ).pack(pady=10)
    
    def create_filter_panel(self):
        """Create filter visualization panel."""
        self.filter_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        # Title and controls
        title_frame = tk.Frame(self.filter_panel, bg='#2b2b2b')
        title_frame.pack(pady=10)
        
        tk.Label(
            title_frame,
            text="Filter View",
            font=("Arial", 16, "bold"),
            fg="white",
            bg='#2b2b2b'
        ).pack()
        
        # Filter type selector
        filter_control_frame = tk.Frame(self.filter_panel, bg='#2b2b2b')
        filter_control_frame.pack(pady=10)
        
        tk.Label(
            filter_control_frame,
            text="Filter:",
            font=("Arial", 12),
            fg="white",
            bg='#2b2b2b'
        ).pack(side=tk.LEFT, padx=10)
        
        self.filter_type_var = tk.StringVar(value="color")
        
        tk.Radiobutton(
            filter_control_frame,
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
            filter_control_frame,
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
        
        # Filter view
        self.filter_canvas = tk.Canvas(
            self.filter_panel,
            width=640,
            height=480,
            bg="black",
            highlightthickness=0
        )
        self.filter_canvas.pack(pady=10)
        
        if not NAVIGATION_AVAILABLE:
            tk.Label(
                self.filter_panel,
                text="⚠ Filters not available (camera modules missing)",
                font=("Arial", 10),
                fg="#ff4444",
                bg='#2b2b2b'
            ).pack(pady=10)
    
    def switch_mode_key(self, mode):
        """Switch mode via keyboard shortcut."""
        self.mode_var.set(mode)
        self.on_mode_change()
        print(f"\n[Mode switched to: {mode.upper()}]")
    
    def cycle_mode(self):
        """Cycle through modes with Tab key."""
        modes = ["manual", "waypoint", "navigation", "filter"]
        current_idx = modes.index(self.current_mode)
        next_idx = (current_idx + 1) % len(modes)
        
        # Skip unavailable modes
        while True:
            next_mode = modes[next_idx]
            # Check if mode is available
            if next_mode == "manual" and not MANUAL_CONTROL_AVAILABLE:
                next_idx = (next_idx + 1) % len(modes)
                continue
            if next_mode in ["navigation", "filter"] and not NAVIGATION_AVAILABLE:
                next_idx = (next_idx + 1) % len(modes)
                continue
            break
        
        self.switch_mode_key(modes[next_idx])
    
    def on_mode_change(self):
        """Handle mode change."""
        # Hide all panels
        self.manual_panel.pack_forget()
        self.waypoint_panel.pack_forget()
        self.navigation_panel.pack_forget()
        self.filter_panel.pack_forget()
        
        # Show selected panel
        self.current_mode = self.mode_var.get()
        
        if self.current_mode == "manual":
            self.manual_panel.pack(fill=tk.BOTH, expand=True)
        elif self.current_mode == "waypoint":
            self.waypoint_panel.pack(fill=tk.BOTH, expand=True)
        elif self.current_mode == "navigation":
            self.navigation_panel.pack(fill=tk.BOTH, expand=True)
            # Force camera initialization and wait for it
            print(f"\n[Entering Navigation Mode - initializing camera...]")
            self.force_init_camera()
        elif self.current_mode == "filter":
            self.filter_panel.pack(fill=tk.BOTH, expand=True)
            # Force camera initialization and wait for it
            print(f"\n[Entering Filter Mode - initializing camera...]")
            self.force_init_camera()
    
    def on_nav_type_change(self):
        """Handle navigation type change."""
        self.nav_type = self.nav_type_var.get()
        print(f"Switched to {self.nav_type.upper()} navigation")
    
    def on_filter_type_change(self):
        """Handle filter type change."""
        self.filter_type = self.filter_type_var.get()
        print(f"Switched to {self.filter_type.upper()} filter")
    
    def on_waypoint_click(self, event):
        """Handle click on waypoint canvas."""
        if not self.car:
            messagebox.showwarning("BLE Not Ready", "BLE client not initialized yet")
            return
        
        # Convert pixel coordinates to physical coordinates (cm)
        px = event.x
        py = event.y
        
        coord_x = px * self.max_x / self.waypoint_canvas_width
        coord_y = (self.waypoint_canvas_height - py) * self.max_y / self.waypoint_canvas_height
        
        coord_x_round = round(coord_x, 1)
        coord_y_round = round(coord_y, 1)
        
        print(f"→ Waypoint set: ({coord_x_round}, {coord_y_round}) cm")
        
        # Update status
        self.waypoint_status_label.config(
            text=f"Waypoint: ({coord_x_round}, {coord_y_round}) cm | Sending..."
        )
        
        # Draw marker
        self.waypoint_canvas.delete("marker")
        r = 8
        self.waypoint_canvas.create_oval(
            px - r, py - r, px + r, py + r,
            fill="#ff4444",
            outline="#cc0000",
            width=2,
            tags="marker"
        )
        # Crosshair
        self.waypoint_canvas.create_line(px - r - 5, py, px - r, py, fill="#cc0000", width=2, tags="marker")
        self.waypoint_canvas.create_line(px + r, py, px + r + 5, py, fill="#cc0000", width=2, tags="marker")
        self.waypoint_canvas.create_line(px, py - r - 5, px, py - r, fill="#cc0000", width=2, tags="marker")
        self.waypoint_canvas.create_line(px, py + r, px, py + r + 5, fill="#cc0000", width=2, tags="marker")
        
        # Label
        self.waypoint_canvas.create_text(
            px, py - r - 15,
            text=f"({coord_x_round}, {coord_y_round})",
            fill="#cc0000",
            font=("Arial", 10, "bold"),
            tags="marker"
        )
        
        # Send waypoint via BLE
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.send_waypoint(coord_x_round, coord_y_round),
                self.loop
            )
    
    async def send_waypoint(self, x, y):
        """Send waypoint via BLE."""
        try:
            if self.car:
                await self.car.set_waypoint(x, y)
                self.root.after(0, lambda: self.waypoint_status_label.config(
                    text=f"Waypoint: ({x}, {y}) cm | ✓ Sent"
                ))
        except Exception as e:
            print(f"Error sending waypoint: {e}")
            self.root.after(0, lambda: self.waypoint_status_label.config(
                text=f"Waypoint: ({x}, {y}) cm | ✗ Error"
            ))
    
    def force_init_camera(self):
        """Force camera initialization and WAIT for it to complete (blocking)."""
        if not NAVIGATION_AVAILABLE:
            print("✗ Navigation modules not available")
            return False
        
        if self.camera_cap is not None:
            print("✓ Camera already initialized")
            return True
        
        print("Opening camera...")
        try:
            # Try to get camera URL from config if available
            import yaml
            import os
            config_path = Path(__file__).parent.parent / "on_board_cam" / "config.yaml"
            camera_url = 0  # Default to device 0
            
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        camera_url = config.get('camera', {}).get('url', 0)
                        print(f"  Using camera URL from config: {camera_url}")
                except:
                    pass
            
            # Open camera (BLOCKING - will wait)
            cap = cv2.VideoCapture(camera_url)
            
            # Wait and retry if needed
            max_retries = 3
            retry_count = 0
            while not cap.isOpened() and retry_count < max_retries:
                print(f"  Camera not ready, retry {retry_count + 1}/{max_retries}...")
                cap.release()
                import time
                time.sleep(1)
                cap = cv2.VideoCapture(camera_url)
                retry_count += 1
            
            if not cap.isOpened():
                print("✗ Failed to open camera after retries")
                messagebox.showerror("Camera Error", 
                    f"Could not open camera!\nURL: {camera_url}\n\nCheck:\n" +
                    "1. Camera is connected\n" +
                    "2. Camera URL in config.yaml is correct\n" +
                    "3. Camera not in use by another app")
                return False
            
            # Test read
            ret, frame = cap.read()
            if not ret or frame is None:
                print("✗ Camera opened but cannot read frames")
                cap.release()
                messagebox.showerror("Camera Error", "Camera opened but cannot read frames")
                return False
            
            self.camera_cap = cap
            print(f"✓ Camera initialized: {frame.shape[1]}x{frame.shape[0]}")
            return True
            
        except Exception as e:
            print(f"✗ Camera error: {e}")
            messagebox.showerror("Camera Error", f"Camera initialization failed:\n{e}")
            self.camera_cap = None
            return False
    
    def init_camera(self):
        """Legacy non-blocking camera init (called by async loop)."""
        if self.camera_cap is None and NAVIGATION_AVAILABLE:
            def init_in_thread():
                try:
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        print("⚠ Could not open camera")
                        self.camera_cap = None
                    else:
                        self.camera_cap = cap
                        print("✓ Camera initialized")
                except Exception as e:
                    print(f"⚠ Camera error: {e}")
                    self.camera_cap = None
            
            import threading
            thread = threading.Thread(target=init_in_thread, daemon=True)
            thread.start()
    
    def start_async_loop(self):
        """Start asyncio event loop in background thread."""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.async_main())
        
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
    
    async def async_main(self):
        """Main async function."""
        # Connect to BLE
        await self.connect_ble()
        
        # Start control loops
        await asyncio.gather(
            self.manual_control_loop(),
            self.navigation_loop(),
            return_exceptions=True
        )
    
    async def connect_ble(self):
        """Connect to BLE device."""
        # Update status to connecting
        self.root.after(0, lambda: self.ble_status_label.config(
            text="BLE: Connecting...",
            fg="#ffaa00"
        ))
        print("\n" + "="*60)
        print("BLE Connection Attempt")
        print("="*60)
        
        try:
            self.car = CarBLEClient()
            await self.car.connect()
            
            if self.car.client is not None:
                self.ble_connected = True
                self.root.after(0, lambda: self.ble_status_label.config(
                    text="BLE: Connected ✓",
                    fg="#00ff00"
                ))
                print("✓ Connected to BLE device")
                print("="*60 + "\n")
            else:
                # Simulation mode
                self.ble_connected = False  # Mark as not connected for waypoint check
                self.root.after(0, lambda: self.ble_status_label.config(
                    text="BLE: Simulation Mode 🔧",
                    fg="#ffaa00"
                ))
                print("⚠ Running in SIMULATION MODE")
                print("  All commands will be printed to terminal")
                print("="*60 + "\n")
        except Exception as e:
            print(f"✗ BLE connection error: {e}")
            print("="*60 + "\n")
            self.root.after(0, lambda: self.ble_status_label.config(
                text="BLE: Error ✗",
                fg="#ff4444"
            ))
    
    async def manual_control_loop(self):
        """Manual control loop (WASD + QE for omega)."""
        if not MANUAL_CONTROL_AVAILABLE:
            return
        
        last_throttle = 0.0
        last_steering = 0.0
        last_omega = 0.0
        
        while self.running:
            try:
                if self.current_mode == "manual" and self.car:
                    THROTTLE_SCALE, STEERING_SCALE, OMEGA_SCALE = load_scales()
                    
                    throttle = inp.get_bipolar_ctrl('w', 's', 'LY') * THROTTLE_SCALE
                    steering = inp.get_bipolar_ctrl('d', 'a', 'RX') * STEERING_SCALE
                    omega = inp.get_bipolar_ctrl('e', 'q', 'DPAD_RIGHT', 'DPAD_LEFT') * OMEGA_SCALE
                    
                    self.manual_throttle = throttle
                    self.manual_steering = steering
                    self.manual_omega = omega
                    
                    # Only send if values changed (reduce spam in simulation)
                    if throttle != last_throttle:
                        await self.car.set_throttle(throttle)
                        last_throttle = throttle
                    if steering != last_steering:
                        await self.car.set_steering(steering)
                        last_steering = steering
                    if omega != last_omega:
                        await self.car.set_omega(omega)
                        last_omega = omega
                    
                    # Update UI
                    self.root.after(0, self.update_manual_display)
                    
                    # LED control
                    led = 0 if (inp.is_pressed('x') or inp.is_pressed('A')) else 1
                    await self.car.set_led(led)
                    
                    # Emergency stop
                    if inp.is_pressed('Key.esc'):
                        print("\n[EMERGENCY STOP]")
                        await self.car.set_throttle(0.0)
                        await self.car.set_steering(0.0)
                        await self.car.set_omega(0.0)
                        last_throttle = 0.0
                        last_steering = 0.0
                        last_omega = 0.0
                
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Manual control error: {e}")
                await asyncio.sleep(0.1)
    
    def update_manual_display(self):
        """Update manual control display."""
        self.throttle_label.config(text=f"Throttle: {self.manual_throttle:+.2f}")
        self.steering_label.config(text=f"Steering: {self.manual_steering:+.2f}")
        self.omega_label.config(text=f"Omega: {self.manual_omega:+.2f}")
    
    async def navigation_loop(self):
        """Navigation and filter processing loop."""
        if not NAVIGATION_AVAILABLE:
            return
        
        while self.running:
            try:
                # Only process if in navigation/filter mode AND camera is open
                if self.current_mode in ["navigation", "filter"] and self.camera_cap:
                    ret, frame = self.camera_cap.read()
                    
                    if ret and frame is not None:
                        if self.current_mode == "navigation":
                            await self.process_navigation_frame(frame)
                        elif self.current_mode == "filter":
                            await self.process_filter_frame(frame)
                    else:
                        # Camera read failed
                        print("⚠ Camera read failed")
                        await asyncio.sleep(0.5)
                else:
                    # Not in camera mode or camera not ready
                    await asyncio.sleep(0.1)
                
                await asyncio.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"Navigation loop error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(0.5)
    
    async def process_navigation_frame(self, frame):
        """Process frame for navigation mode."""
        # This is a simplified version - you can expand with full navigation logic
        # For now, just display the frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (640, 480))
        
        # Add text overlay
        cv2.putText(frame_resized, f"Navigation: {self.nav_type.upper()}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Convert to PIL Image and display
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
        self.root.after(0, lambda: self.update_nav_canvas(imgtk))
    
    def update_nav_canvas(self, imgtk):
        """Update navigation canvas."""
        self.nav_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.nav_canvas.image = imgtk  # Keep reference
    
    async def process_filter_frame(self, frame):
        """Process frame for filter view."""
        if self.filter_type == "color":
            # Simple color mask (red)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower = np.array([0, 120, 70])
            upper = np.array([10, 255, 255])
            mask = cv2.inRange(hsv, lower, upper)
            result = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        elif self.filter_type == "canny":
            # Canny edge detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            result = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        
        frame_resized = cv2.resize(result, (640, 480))
        
        # Convert to PIL Image and display
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
        self.root.after(0, lambda: self.update_filter_canvas(imgtk))
    
    def update_filter_canvas(self, imgtk):
        """Update filter canvas."""
        self.filter_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.filter_canvas.image = imgtk  # Keep reference
    
    def on_close(self):
        """Handle window close."""
        self.running = False
        
        # Stop motors
        if self.car and self.loop:
            async def stop():
                await self.car.set_throttle(0.0)
                await self.car.set_steering(0.0)
                await self.car.set_omega(0.0)
                if self.car.client:
                    await self.car.disconnect()
            
            asyncio.run_coroutine_threadsafe(stop(), self.loop)
        
        # Release camera
        if self.camera_cap:
            self.camera_cap.release()
        
        # Close window
        self.root.quit()
        self.root.destroy()


def main():
    """Main entry point."""
    # Recommended for Windows
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
