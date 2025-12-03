#!/usr/bin/env python3
"""
Unified Navigation Viewer
==========================

Single viewer that can switch between different vision targets:
- ArUco markers
- Color-based tracking
- (Future: Line following, Face detection, etc.)

Controls:
  't' - Switch target detector type
  'p' - Pause/Resume autonomous mode
  'm' - Toggle manual override
  'w'/'s' - Manual throttle
  'a'/'d' - Manual steering
  'space' - Stop
  'q' - Quit
"""

import cv2
import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from navigation.base_navigation import BaseNavigationController, to_byte
from navigation.target_detectors import ArucoTargetDetector, ColorTargetDetector


class UnifiedNavigationController(BaseNavigationController):
    """Navigation controller that can switch between different target detectors."""
    
    def __init__(self, config_path=None, initial_detector='aruco'):
        """
        Initialize unified navigation controller.
        
        Args:
            config_path: Path to config file
            initial_detector: Initial detector type ('aruco' or 'color')
        """
        super().__init__(config_path)
        
        # Available detectors
        self.detector_types = ['aruco', 'color']
        self.current_detector_index = self.detector_types.index(initial_detector)
        
        # Initialize all detectors
        self.detectors = {
            'aruco': ArucoTargetDetector(self.config),
            'color': ColorTargetDetector(self.config)
        }
        
        # ArUco-specific navigation params
        aruco_nav_cfg = self.config.get('navigation', {})
        self.target_distance_cm = aruco_nav_cfg.get('target_distance_cm', 50.0)
        self.distance_tolerance_cm = aruco_nav_cfg.get('distance_tolerance_cm', 3.0)
        
        print(f"Initialized with detector: {self.get_current_detector_name()}")
    
    def get_current_detector_name(self):
        """Get name of currently active detector."""
        return self.detector_types[self.current_detector_index].upper()
    
    def get_detector_name(self):
        """Return detector name for base class."""
        return self.get_current_detector_name()
    
    def switch_detector(self):
        """Switch to next detector type."""
        self.current_detector_index = (self.current_detector_index + 1) % len(self.detector_types)
        print(f"\nSwitched to {self.get_current_detector_name()} detector")
    
    def get_current_detector(self):
        """Get currently active detector."""
        detector_type = self.detector_types[self.current_detector_index]
        return self.detectors[detector_type]
    
    def process_frame_autonomous(self, frame):
        """
        Process frame using current detector.
        
        Returns:
            (throttle, steering, frame_with_overlay)
        """
        detector = self.get_current_detector()
        detection = detector.detect(frame)
        
        throttle = 0.0
        steering = 0.0
        frame = detection['frame']
        
        if detection['detected']:
            center_x = detection['center_x']
            center_y = detection['center_y']
            
            # Calculate steering to center the target
            steering = self.calculate_steering(center_x)
            
            # Calculate throttle based on detector type
            detector_type = self.detector_types[self.current_detector_index]
            
            if detector_type == 'aruco':
                # ArUco: use actual distance
                distance_cm = detection['distance_metric']
                distance_error = distance_cm - self.target_distance_cm
                
                if abs(distance_error) > self.distance_tolerance_cm:
                    if distance_error > 0:
                        throttle = self.base_throttle
                    else:
                        throttle = -self.base_throttle * self.backward_throttle_multiplier
                        steering = -steering  # Invert steering when backward
                else:
                    throttle = 0.0
                
                # Add overlay
                info = detection['info']
                throttle_byte = to_byte(throttle)
                steering_byte = to_byte(steering)
                
                status_text = [
                    f"Target: ArUco ID {info['id']} | Dist: {distance_cm:.1f}cm",
                    f"Target: {self.target_distance_cm:.1f}cm | Error: {distance_error:+.1f}cm",
                    "",
                    f"COMMANDS:",
                    f"Throttle: {throttle:+.2f} ({throttle_byte:3d})",
                    f"Steering: {steering:+.2f} ({steering_byte:3d})"
                ]
                
            elif detector_type == 'color':
                # Color: use area as distance proxy
                area = detection['distance_metric']
                info = detection['info']
                area_ratio = info['area_ratio']
                target_area_ratio = info['target_area_ratio']
                size_error = target_area_ratio - area_ratio
                
                if size_error > 0.01:
                    throttle = self.base_throttle
                elif size_error < -0.01:
                    throttle = -self.base_throttle * self.backward_throttle_multiplier * 0.5
                    steering = -steering  # Invert when backward
                else:
                    throttle = 0.0
                
                # Add overlay
                throttle_byte = to_byte(throttle)
                steering_byte = to_byte(steering)
                
                status_text = [
                    f"Target: Color @ ({center_x:.0f}, {center_y:.0f})",
                    f"Area: {area:.0f}px | Ratio: {area_ratio:.3f} (Target: {target_area_ratio:.3f})",
                    "",
                    f"COMMANDS:",
                    f"Throttle: {throttle:+.2f} ({throttle_byte:3d})",
                    f"Steering: {steering:+.2f} ({steering_byte:3d})"
                ]
            
            # Draw status overlay
            y_offset = 30
            for i, text in enumerate(status_text):
                if text == "":
                    y_offset += 10
                    continue
                color = (0, 255, 255) if i >= 3 else (0, 255, 0)
                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 25
            
            # Draw center line and target position
            if self.frame_width:
                cv2.line(frame, (int(self.frame_width/2), 0),
                        (int(self.frame_width/2), self.frame_height),
                        (255, 0, 0), 2)
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 255, 255), -1)
            
        else:
            # No target detected
            throttle = 0.0
            steering = 0.0
            
            cv2.putText(frame, f"NO {self.get_current_detector_name()} TARGET DETECTED - STOPPED",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        return throttle, steering, frame
    
    async def run_async(self):
        """Main control loop with target switching."""
        if not self.init_camera():
            return
        
        await self.connect_ble()
        
        window_name = "Unified Navigation - Multi-Target"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        
        print("\n" + "="*60)
        print("UNIFIED NAVIGATION CONTROLLER")
        print("="*60)
        print("Controls:")
        print("  't' - Switch target type (ArUco <-> Color)")
        print("  'p' - Pause/Resume autonomous mode")
        print("  'm' - Toggle manual override")
        print("  'w'/'s' - Manual throttle")
        print("  'a'/'d' - Manual steering")
        print("  'space' - Stop")
        print("  'q' - Quit")
        print("="*60)
        print(f"Current detector: {self.get_current_detector_name()}")
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
                    
                    cv2.putText(frame, f"MANUAL MODE - {self.get_current_detector_name()}",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
                    cv2.putText(frame, f"Throttle: {throttle:+.2f} | Steering: {steering:+.2f}",
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                
                elif self.autonomous_mode:
                    throttle, steering, frame = self.process_frame_autonomous(frame)
                    
                    cv2.putText(frame, f"AUTO - {self.get_current_detector_name()}",
                               (10, frame.shape[0] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    throttle = 0.0
                    steering = 0.0
                    
                    cv2.putText(frame, f"PAUSED - {self.get_current_detector_name()}",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
                
                self.send_motor_command(throttle, steering)
                
                cv2.imshow(window_name, frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('t'):
                    self.switch_detector()
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


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Unified navigation with switchable targets")
    parser.add_argument('--detector', choices=['aruco', 'color'], default='aruco',
                       help='Initial detector type (default: aruco)')
    args = parser.parse_args()
    
    controller = UnifiedNavigationController(
        initial_detector=args.detector
    )
    controller.run()


if __name__ == "__main__":
    main()
