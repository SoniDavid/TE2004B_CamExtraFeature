#!/usr/bin/env python3
"""
HSV Color Calibration Tool
===========================

Interactive tool to calibrate HSV color ranges for color-based tracking.
Click on the desired color in the video feed to automatically generate
optimal HSV ranges.

Usage:
    python calibrate_color_mask.py [--camera CAMERA_URL]

Controls:
    - Click on object to sample color
    - Trackbars adjust HSV range
    - 's' - Save current HSV values to config
    - 'r' - Reset to default values
    - 'q' - Quit

The tool shows:
    - Original video feed
    - HSV mask (what the robot sees)
    - Current HSV values
"""

import cv2
import numpy as np
import yaml
import argparse
import os


class ColorCalibrator:
    """Interactive HSV color calibration tool."""
    
    def __init__(self, camera_url, config_path="../config.yaml"):
        self.camera_url = camera_url
        self.config_path = config_path
        
        # Default HSV values (red color range)
        self.h_min = 0
        self.h_max = 10
        self.s_min = 100
        self.s_max = 255
        self.v_min = 100
        self.v_max = 255
        
        # Load existing config if available
        self.load_existing_config()
        
        # Camera
        self.cap = None
        
        # Windows
        self.window_original = "Original - Click to sample color"
        self.window_mask = "HSV Mask"
        self.window_controls = "HSV Controls"
        
    def load_existing_config(self):
        """Load existing HSV values from config if available."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    color_cfg = config.get('color_tracking', {})
                    
                    hsv_lower = color_cfg.get('hsv_lower', [0, 100, 100])
                    hsv_upper = color_cfg.get('hsv_upper', [10, 255, 255])
                    
                    self.h_min, self.s_min, self.v_min = hsv_lower
                    self.h_max, self.s_max, self.v_max = hsv_upper
                    
                    print(f"Loaded existing HSV values from config")
            except Exception as e:
                print(f"Could not load existing config: {e}")
    
    def mouse_callback(self, event, x, y, flags, param):
        """Mouse callback to sample color from frame."""
        if event == cv2.EVENT_LBUTTONDOWN:
            frame_bgr, frame_hsv = param
            
            # Get clicked pixel's BGR value
            b, g, r = frame_bgr[y, x]
            
            # Get clicked pixel's HSV value
            h, s, v = frame_hsv[y, x]
            
            print(f"\nSampled color at ({x}, {y}):")
            print(f"  RGB: R={r}, G={g}, B={b}")
            print(f"  BGR: B={b}, G={g}, R={r}")
            print(f"  HSV: H={h}, S={s}, V={v}")
            
            # Set HSV range with tolerance
            h_tolerance = 10
            s_tolerance = 50
            v_tolerance = 50
            
            self.h_min = max(0, h - h_tolerance)
            self.h_max = min(179, h + h_tolerance)  # OpenCV uses 0-179 for H
            self.s_min = max(0, s - s_tolerance)
            self.s_max = min(255, s + s_tolerance)
            self.v_min = max(0, v - v_tolerance)
            self.v_max = min(255, v + v_tolerance)
            
            # Update trackbars
            cv2.setTrackbarPos('H Min', self.window_controls, self.h_min)
            cv2.setTrackbarPos('H Max', self.window_controls, self.h_max)
            cv2.setTrackbarPos('S Min', self.window_controls, self.s_min)
            cv2.setTrackbarPos('S Max', self.window_controls, self.s_max)
            cv2.setTrackbarPos('V Min', self.window_controls, self.v_min)
            cv2.setTrackbarPos('V Max', self.window_controls, self.v_max)
            
            print(f"  Generated HSV range: H=[{self.h_min}-{self.h_max}], S=[{self.s_min}-{self.s_max}], V=[{self.v_min}-{self.v_max}]")
            print("  Adjust trackbars to fine-tune, then press 's' to save")
    
    def nothing(self, x):
        """Dummy callback for trackbars."""
        pass
    
    def create_windows(self):
        """Create windows and trackbars."""
        cv2.namedWindow(self.window_original)
        cv2.namedWindow(self.window_mask)
        cv2.namedWindow(self.window_controls)
        
        # Create trackbars
        cv2.createTrackbar('H Min', self.window_controls, self.h_min, 179, self.nothing)
        cv2.createTrackbar('H Max', self.window_controls, self.h_max, 179, self.nothing)
        cv2.createTrackbar('S Min', self.window_controls, self.s_min, 255, self.nothing)
        cv2.createTrackbar('S Max', self.window_controls, self.s_max, 255, self.nothing)
        cv2.createTrackbar('V Min', self.window_controls, self.v_min, 255, self.nothing)
        cv2.createTrackbar('V Max', self.window_controls, self.v_max, 255, self.nothing)
    
    def save_to_config(self):
        """Save current HSV values to config file."""
        hsv_lower = [self.h_min, self.s_min, self.v_min]
        hsv_upper = [self.h_max, self.s_max, self.v_max]
        
        # Load existing config or create new
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            config = {}
        
        # Update color tracking section
        if 'color_tracking' not in config:
            config['color_tracking'] = {}
        
        config['color_tracking']['hsv_lower'] = hsv_lower
        config['color_tracking']['hsv_upper'] = hsv_upper
        
        # Save to file
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"\n{'='*60}")
        print(f"Saved HSV values to {self.config_path}")
        print(f"  hsv_lower: {hsv_lower}")
        print(f"  hsv_upper: {hsv_upper}")
        print(f"{'='*60}\n")
    
    def run(self):
        """Main calibration loop."""
        # Connect to camera
        print(f"Connecting to camera at {self.camera_url}...")
        self.cap = cv2.VideoCapture(self.camera_url)
        
        if not self.cap.isOpened():
            print(f"ERROR: Could not connect to camera")
            return
        
        print("Camera connected!")
        print("\nInstructions:")
        print("  1. Click on the colored object you want to track")
        print("     - Shows RGB and HSV values of clicked pixel")
        print("     - Automatically generates HSV range")
        print("  2. Adjust HSV trackbars to fine-tune the mask")
        print("  3. Press 's' to save values to config.yaml")
        print("  4. Press 'r' to reset to defaults")
        print("  5. Press 'q' to quit\n")
        
        # Create windows
        self.create_windows()
        
        try:
            while True:
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to read frame")
                    break
                
                # Convert to HSV
                frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Get current trackbar values
                self.h_min = cv2.getTrackbarPos('H Min', self.window_controls)
                self.h_max = cv2.getTrackbarPos('H Max', self.window_controls)
                self.s_min = cv2.getTrackbarPos('S Min', self.window_controls)
                self.s_max = cv2.getTrackbarPos('S Max', self.window_controls)
                self.v_min = cv2.getTrackbarPos('V Min', self.window_controls)
                self.v_max = cv2.getTrackbarPos('V Max', self.window_controls)
                
                # Create HSV mask
                lower = np.array([self.h_min, self.s_min, self.v_min])
                upper = np.array([self.h_max, self.s_max, self.v_max])
                mask = cv2.inRange(frame_hsv, lower, upper)
                
                # Apply morphological operations
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                # Find contours and draw largest
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    if cv2.contourArea(largest) > 500:
                        # Draw contour on original
                        cv2.drawContours(frame, [largest], -1, (0, 255, 0), 3)
                        
                        # Draw center
                        M = cv2.moments(largest)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
                
                # Add HSV values text to frame
                text_lines = [
                    f"HSV Lower: [{self.h_min}, {self.s_min}, {self.v_min}]",
                    f"HSV Upper: [{self.h_max}, {self.s_max}, {self.v_max}]",
                    "",
                    "Click on object to sample RGB/HSV color",
                    "Press 's' to save, 'r' to reset, 'q' to quit"
                ]
                
                y_offset = 30
                for line in text_lines:
                    cv2.putText(frame, line, (10, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    y_offset += 25
                
                # Set mouse callback with both BGR and HSV frames as parameters
                cv2.setMouseCallback(self.window_original, self.mouse_callback, (frame, frame_hsv))
                
                # Display
                cv2.imshow(self.window_original, frame)
                cv2.imshow(self.window_mask, mask)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('s'):
                    self.save_to_config()
                elif key == ord('r'):
                    print("\nReset to default values")
                    self.h_min, self.h_max = 0, 10
                    self.s_min, self.s_max = 100, 255
                    self.v_min, self.v_max = 100, 255
                    cv2.setTrackbarPos('H Min', self.window_controls, self.h_min)
                    cv2.setTrackbarPos('H Max', self.window_controls, self.h_max)
                    cv2.setTrackbarPos('S Min', self.window_controls, self.s_min)
                    cv2.setTrackbarPos('S Max', self.window_controls, self.s_max)
                    cv2.setTrackbarPos('V Min', self.window_controls, self.v_min)
                    cv2.setTrackbarPos('V Max', self.window_controls, self.v_max)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            print("Goodbye!")


def main():
    # Determine paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config = os.path.join(os.path.dirname(script_dir), 'config.yaml')
    
    parser = argparse.ArgumentParser(description="Calibrate HSV color range for tracking")
    parser.add_argument('--config', default=default_config,
                       help=f'Path to config.yaml (default: {default_config})')
    
    args = parser.parse_args()
    
    # Load camera URL from config
    if os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
            camera_url = config.get('camera', {}).get('url', 'http://10.22.227.47:4747/video')
    else:
        camera_url = 'http://10.22.227.47:4747/video'
    
    calibrator = ColorCalibrator(camera_url, args.config)
    calibrator.run()


if __name__ == "__main__":
    main()
