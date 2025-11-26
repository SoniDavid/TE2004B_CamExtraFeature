"""
Camera Processing Module
=========================

This package provides modules for processing camera frames and ArUco marker detection
for DroidCam or other camera sources.

Modules:
    - image_filters: Image processing pipeline and filters
    - aruco_detector: ArUco marker detection and depth estimation

Example usage:
    import cv2
    from camera_processing import FrameProcessor, ProcessingMode, ArucoDetector

    # Open camera stream
    cap = cv2.VideoCapture("http://10.22.209.148:4747/video")
    
    # Create processor and ArUco detector
    processor = FrameProcessor()
    aruco = ArucoDetector()
    
    # Get and process frame
    ret, frame = cap.read()
    processed = processor.process(frame, ProcessingMode.EDGE_DETECTION)
    markers = aruco.detect(frame)
"""

from .image_filters import (
    FrameProcessor,
    ProcessingMode,
    create_processor,
    # Processing functions
    resize_frame,
    convert_to_grayscale,
    apply_edge_detection,
    apply_gaussian_blur,
    apply_sharpen,
    adjust_brightness,
    adjust_contrast,
    apply_threshold,
    add_timestamp,
    add_text_overlay,
)

from .aruco_detector import (
    ArucoDetector,
    generate_aruco_marker,
    save_aruco_marker,
)

__version__ = "2.0.0"
__all__ = [
    # Image filters
    "FrameProcessor",
    "ProcessingMode",
    "create_processor",
    "resize_frame",
    "convert_to_grayscale",
    "apply_edge_detection",
    "apply_gaussian_blur",
    "apply_sharpen",
    "adjust_brightness",
    "adjust_contrast",
    "apply_threshold",
    "add_timestamp",
    "add_text_overlay",
    # ArUco detection
    "ArucoDetector",
    "generate_aruco_marker",
    "save_aruco_marker",
]
