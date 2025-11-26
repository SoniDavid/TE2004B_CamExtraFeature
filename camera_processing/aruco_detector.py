"""
ArUco Marker Detection for Depth Estimation
============================================

This module provides ArUco marker detection and depth estimation based on marker size.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArucoDetector:
    """
    Detect ArUco markers and estimate depth/distance based on known marker size.
    
    Supported ArUco dictionaries:
    - DICT_4X4_50, DICT_4X4_100, DICT_4X4_250, DICT_4X4_1000
    - DICT_5X5_50, DICT_5X5_100, DICT_5X5_250, DICT_5X5_1000
    - DICT_6X6_50, DICT_6X6_100, DICT_6X6_250, DICT_6X6_1000
    - DICT_7X7_50, DICT_7X7_100, DICT_7X7_250, DICT_7X7_1000
    """
    
    # ArUco dictionary types
    ARUCO_DICT = {
        "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
        "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
        "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
        "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
        "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
        "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
        "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
        "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
        "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
        "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
        "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
        "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
        "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
        "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
        "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
        "DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
    }
    
    def __init__(
        self,
        aruco_dict_type: str = "DICT_6X6_250",
        marker_size_cm: float = 10.0,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None,
        focal_length_px: float = 1000.0
    ):
        """
        Initialize ArUco detector with optimized parameters.
        
        Args:
            aruco_dict_type: Type of ArUco dictionary to use
            marker_size_cm: Real-world size of the marker in centimeters
            camera_matrix: Camera calibration matrix (3x3)
            dist_coeffs: Camera distortion coefficients
            focal_length_px: Focal length in pixels (if camera_matrix not provided)
        """
        if aruco_dict_type not in self.ARUCO_DICT:
            raise ValueError(f"Invalid ArUco dictionary type: {aruco_dict_type}")
        
        self.aruco_dict_type = aruco_dict_type
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(self.ARUCO_DICT[aruco_dict_type])
        
        # Configure detection parameters for better detection
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_params.adaptiveThreshWinSizeMin = 3
        self.aruco_params.adaptiveThreshWinSizeMax = 23
        self.aruco_params.adaptiveThreshWinSizeStep = 10
        self.aruco_params.minMarkerPerimeterRate = 0.03
        self.aruco_params.maxMarkerPerimeterRate = 4.0
        self.aruco_params.polygonalApproxAccuracyRate = 0.05
        self.aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.aruco_params.cornerRefinementWinSize = 5
        
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        self.marker_size_cm = marker_size_cm
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.focal_length_px = focal_length_px
        
        logger.info(f"ArUco detector initialized with {aruco_dict_type}")
        logger.info(f"Marker size: {marker_size_cm} cm")
    
    def detect(self, frame: np.ndarray) -> Tuple[List, List, List]:
        """
        Detect ArUco markers in the frame.
        
        Args:
            frame: Input image (BGR or grayscale)
        
        Returns:
            Tuple of (corners, ids, rejected_points)
            - corners: List of detected marker corners
            - ids: List of marker IDs
            - rejected_points: List of rejected candidate corners
        """
        corners, ids, rejected = self.detector.detectMarkers(frame)
        return corners, ids, rejected
    
    def estimate_distance(self, corners: np.ndarray) -> float:
        """
        Estimate distance to marker based on its perceived size.
        
        Uses the formula: Distance = (Real_Size × Focal_Length) / Perceived_Size
        
        Args:
            corners: Corners of detected marker (4 points)
        
        Returns:
            Estimated distance in centimeters
        """
        # Calculate marker width in pixels (average of top and bottom edge)
        top_edge = np.linalg.norm(corners[0][0] - corners[0][1])
        bottom_edge = np.linalg.norm(corners[0][2] - corners[0][3])
        perceived_width_px = (top_edge + bottom_edge) / 2.0
        
        # Distance = (Real_Size × Focal_Length) / Perceived_Size
        distance_cm = (self.marker_size_cm * self.focal_length_px) / perceived_width_px
        
        return distance_cm
    
    def estimate_pose(
        self,
        corners: np.ndarray,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Estimate marker pose (rotation and translation vectors).
        Requires camera calibration.
        
        Args:
            corners: Corners of detected marker
            camera_matrix: Camera calibration matrix (uses instance default if None)
            dist_coeffs: Distortion coefficients (uses instance default if None)
        
        Returns:
            Tuple of (rvec, tvec) - rotation and translation vectors
            Returns (None, None) if camera calibration not available
        """
        cam_matrix = camera_matrix if camera_matrix is not None else self.camera_matrix
        dist_coeff = dist_coeffs if dist_coeffs is not None else self.dist_coeffs
        
        if cam_matrix is None:
            logger.warning("Camera calibration not available. Cannot estimate pose.")
            return None, None
        
        if dist_coeff is None:
            dist_coeff = np.zeros((5, 1))
        
        # Object points for the marker (square with marker_size_cm dimensions)
        marker_points = np.array([
            [-self.marker_size_cm/2, self.marker_size_cm/2, 0],
            [self.marker_size_cm/2, self.marker_size_cm/2, 0],
            [self.marker_size_cm/2, -self.marker_size_cm/2, 0],
            [-self.marker_size_cm/2, -self.marker_size_cm/2, 0]
        ], dtype=np.float32)
        
        # Solve PnP to get pose
        success, rvec, tvec = cv2.solvePnP(
            marker_points,
            corners,
            cam_matrix,
            dist_coeff,
            flags=cv2.SOLVEPNP_IPPE_SQUARE
        )
        
        if success:
            return rvec, tvec
        return None, None
    
    def draw_detections(
        self,
        frame: np.ndarray,
        corners: List,
        ids: List,
        show_distance: bool = True,
        show_id: bool = True
    ) -> np.ndarray:
        """
        Draw detected markers on the frame.
        
        Args:
            frame: Input frame
            corners: Detected marker corners
            ids: Detected marker IDs
            show_distance: Whether to show estimated distance
            show_id: Whether to show marker ID
        
        Returns:
            Frame with drawn markers
        """
        if ids is None or len(ids) == 0:
            return frame
        
        # Draw marker boundaries
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        
        # Draw additional info for each marker
        for i, corner in enumerate(corners):
            # Get marker center
            center = corner[0].mean(axis=0).astype(int)
            
            # Estimate distance
            distance = self.estimate_distance(corner)
            
            # Prepare text
            text_lines = []
            if show_id:
                text_lines.append(f"ID: {ids[i][0]}")
            if show_distance:
                text_lines.append(f"Dist: {distance:.1f}cm")
            
            # Draw text
            y_offset = -10
            for text in text_lines:
                cv2.putText(
                    frame,
                    text,
                    (center[0], center[1] + y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )
                y_offset += 25
        
        return frame
    
    def get_marker_info(
        self,
        corners: List,
        ids: List
    ) -> List[Dict]:
        """
        Get detailed information about detected markers.
        
        Args:
            corners: Detected marker corners
            ids: Detected marker IDs
        
        Returns:
            List of dictionaries with marker information
        """
        if ids is None or len(ids) == 0:
            return []
        
        markers_info = []
        
        for i, corner in enumerate(corners):
            marker_id = ids[i][0]
            distance = self.estimate_distance(corner)
            center = corner[0].mean(axis=0)
            
            # Calculate marker area (for quality assessment)
            area = cv2.contourArea(corner[0])
            
            info = {
                'id': marker_id,
                'distance_cm': distance,
                'center_x': float(center[0]),
                'center_y': float(center[1]),
                'corners': corner[0].tolist(),
                'area_px': float(area)
            }
            
            markers_info.append(info)
        
        return markers_info


def generate_aruco_marker(marker_id: int, marker_size: int = 200, aruco_dict_type: str = "DICT_6X6_250", border_bits: int = 1) -> np.ndarray:
    """
    Generate an ArUco marker image with white border.
    
    Args:
        marker_id: ID of the marker to generate
        marker_size: Size of the marker in pixels (including border)
        aruco_dict_type: Type of ArUco dictionary
        border_bits: Number of white border bits (default=1, recommended for detection)
    
    Returns:
        Generated marker image with white border
    """
    if aruco_dict_type not in ArucoDetector.ARUCO_DICT:
        raise ValueError(f"Invalid ArUco dictionary type: {aruco_dict_type}")
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(ArucoDetector.ARUCO_DICT[aruco_dict_type])
    
    # Generate marker without border first
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size, borderBits=border_bits)
    
    # Add extra white padding for better detection
    padding = max(20, marker_size // 10)
    marker_with_padding = cv2.copyMakeBorder(
        marker_image,
        padding, padding, padding, padding,
        cv2.BORDER_CONSTANT,
        value=255
    )
    
    return marker_with_padding


def save_aruco_marker(marker_id: int, filename: str, marker_size: int = 200, aruco_dict_type: str = "DICT_6X6_250", border_bits: int = 1):
    """
    Generate and save an ArUco marker to a file with proper borders.
    
    Args:
        marker_id: ID of the marker to generate
        filename: Output filename (e.g., "marker_0.png")
        marker_size: Size of the marker in pixels (core marker, padding added automatically)
        aruco_dict_type: Type of ArUco dictionary
        border_bits: Number of white border bits (default=1)
    """
    marker = generate_aruco_marker(marker_id, marker_size, aruco_dict_type, border_bits)
    cv2.imwrite(filename, marker)
    logger.info(f"Saved ArUco marker ID {marker_id} to {filename}")


if __name__ == "__main__":
    # Example usage: Generate some markers
    import os
    
    output_dir = "aruco_markers"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating ArUco markers...")
    for i in range(5):
        filename = os.path.join(output_dir, f"marker_{i}.png")
        save_aruco_marker(i, filename, marker_size=400, aruco_dict_type="DICT_6X6_250")
        print(f"✓ Generated marker {i}")
    
    print(f"\nMarkers saved in '{output_dir}/' directory")
    print("Print these markers and use them for depth estimation!")
