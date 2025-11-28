"""
Target Detectors for Navigation
================================

Different target detection strategies that can be used with navigation.
Each detector implements the detection logic and returns target information.
"""

import cv2
import numpy as np
import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import ArucoDetector


class TargetDetector:
    """Base class for target detectors."""
    
    def __init__(self, config):
        self.config = config
    
    def detect(self, frame):
        """
        Detect target in frame.
        
        Returns:
            dict with keys:
                - detected: bool
                - center_x: float (pixel x coordinate)
                - center_y: float (pixel y coordinate)
                - distance_metric: float (distance proxy or actual distance)
                - frame: annotated frame
                - info: dict with additional info
        """
        raise NotImplementedError


class ArucoTargetDetector(TargetDetector):
    """Detect ArUco markers as targets."""
    
    def __init__(self, config):
        super().__init__(config)
        aruco_cfg = config['aruco']
        nav_cfg = config.get('navigation', {})
        
        self.detector = ArucoDetector(
            aruco_dict_type=aruco_cfg['dictionary_type'],
            marker_size_cm=aruco_cfg['marker_size_cm'],
            focal_length_px=aruco_cfg['focal_length_px']
        )
        
        self.target_distance_cm = nav_cfg.get('target_distance_cm', 50.0)
        self.distance_tolerance_cm = nav_cfg.get('distance_tolerance_cm', 3.0)
    
    def detect(self, frame):
        """Detect ArUco marker."""
        corners, ids, rejected = self.detector.detect(frame)
        
        if ids is not None and len(ids) > 0:
            marker_info = self.detector.get_marker_info(corners, ids)[0]
            distance_cm = marker_info['distance_cm']
            center_x = marker_info['center_x']
            center_y = marker_info['center_y']
            marker_id = marker_info['id']
            
            frame = self.detector.draw_detections(
                frame, corners, ids,
                show_distance=True,
                show_id=True
            )
            
            return {
                'detected': True,
                'center_x': center_x,
                'center_y': center_y,
                'distance_metric': distance_cm,
                'frame': frame,
                'info': {
                    'id': marker_id,
                    'distance_cm': distance_cm,
                    'target_distance_cm': self.target_distance_cm,
                    'tolerance_cm': self.distance_tolerance_cm
                }
            }
        else:
            return {
                'detected': False,
                'center_x': None,
                'center_y': None,
                'distance_metric': None,
                'frame': frame,
                'info': {}
            }


class ColorTargetDetector(TargetDetector):
    """Detect colored objects as targets."""
    
    def __init__(self, config):
        super().__init__(config)
        color_cfg = config.get('color_tracking', {})
        
        self.hsv_lower = np.array(color_cfg.get('hsv_lower', [0, 100, 100]))
        self.hsv_upper = np.array(color_cfg.get('hsv_upper', [10, 255, 255]))
        self.min_contour_area = color_cfg.get('min_contour_area', 500)
        self.target_area_ratio = color_cfg.get('target_area_ratio', 0.05)
    
    def detect(self, frame):
        """Detect colored target."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            if area >= self.min_contour_area:
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    
                    # Draw detection
                    cv2.drawContours(frame, [largest_contour], -1, (0, 255, 0), 3)
                    cv2.circle(frame, (center_x, center_y), 10, (0, 255, 0), -1)
                    cv2.circle(frame, (center_x, center_y), 15, (255, 255, 255), 2)
                    
                    # Show mask in corner
                    mask_small = cv2.resize(mask, (320, 240))
                    mask_colored = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
                    frame[10:250, frame.shape[1]-330:frame.shape[1]-10] = mask_colored
                    
                    return {
                        'detected': True,
                        'center_x': center_x,
                        'center_y': center_y,
                        'distance_metric': area,  # Use area as distance proxy
                        'frame': frame,
                        'info': {
                            'area': area,
                            'area_ratio': area / (frame.shape[0] * frame.shape[1]),
                            'target_area_ratio': self.target_area_ratio
                        }
                    }
        
        return {
            'detected': False,
            'center_x': None,
            'center_y': None,
            'distance_metric': None,
            'frame': frame,
            'info': {}
        }
