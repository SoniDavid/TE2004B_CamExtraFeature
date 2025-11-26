"""
Camera Processing Module for ESP32-CAM
========================================

This package provides modules for retrieving and processing camera frames
from ESP32-CAM devices.

Modules:
    - esp_camera_client: HTTP client for ESP32-CAM communication
    - frame_processor: Image processing pipeline and filters

Example usage:
    from camera_processing import ESPCameraClient, FrameProcessor, ProcessingMode

    # Connect to ESP32-CAM
    client = ESPCameraClient("192.168.1.100")
    client.connect()

    # Create processor
    processor = FrameProcessor()
    processor.add_processing_step(convert_to_grayscale)

    # Get and process frame
    frame = client.get_frame()
    processed = processor.process(frame)
"""

from .frame_processor import (
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
    # Frame processing
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
