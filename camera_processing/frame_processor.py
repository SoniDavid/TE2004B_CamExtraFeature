import cv2
import numpy as np
from typing import Callable, List, Optional, Dict, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Available image processing modes."""
    ORIGINAL = "original"
    GRAYSCALE = "grayscale"
    EDGE_DETECTION = "edge_detection"
    BLUR = "blur"
    SHARPEN = "sharpen"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    THRESHOLD = "threshold"


class FrameProcessor:
    """
    Frame processing pipeline for ESP32-CAM images.
    Supports multiple processing operations and custom filters.
    """

    def __init__(self):
        """Initialize frame processor."""
        self.processing_pipeline: List[Callable] = []
        self.enabled = True

    def add_processing_step(self, func: Callable[[np.ndarray], np.ndarray]):
        """
        Add a custom processing function to the pipeline.

        Args:
            func: Function that takes a frame (numpy array) and returns processed frame
        """
        self.processing_pipeline.append(func)
        logger.info(f"Added processing step: {func.__name__}")

    def clear_pipeline(self):
        """Clear all processing steps."""
        self.processing_pipeline.clear()
        logger.info("Processing pipeline cleared")

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Process frame through the entire pipeline.

        Args:
            frame: Input frame as numpy array (BGR format)

        Returns:
            Processed frame
        """
        if not self.enabled or frame is None:
            return frame

        processed_frame = frame.copy()

        for step in self.processing_pipeline:
            try:
                processed_frame = step(processed_frame)
            except Exception as e:
                logger.error(f"Error in processing step {step.__name__}: {e}")
                continue

        return processed_frame

    def enable(self):
        """Enable frame processing."""
        self.enabled = True

    def disable(self):
        """Disable frame processing (passthrough mode)."""
        self.enabled = False


# Predefined processing functions

def resize_frame(width: int, height: int) -> Callable:
    """
    Create a resize processing function.

    Args:
        width: Target width
        height: Target height

    Returns:
        Processing function
    """
    def _resize(frame: np.ndarray) -> np.ndarray:
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
    return _resize


def convert_to_grayscale(frame: np.ndarray) -> np.ndarray:
    """Convert frame to grayscale."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)  # Convert back to BGR for consistency


def apply_edge_detection(frame: np.ndarray, threshold1: int = 100, threshold2: int = 200) -> np.ndarray:
    """
    Apply Canny edge detection.

    Args:
        frame: Input frame
        threshold1: First threshold for the hysteresis procedure
        threshold2: Second threshold for the hysteresis procedure

    Returns:
        Edge-detected frame
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold1, threshold2)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def apply_gaussian_blur(ksize: int = 5) -> Callable:
    """
    Create a Gaussian blur processing function.

    Args:
        ksize: Kernel size (must be odd)

    Returns:
        Processing function
    """
    def _blur(frame: np.ndarray) -> np.ndarray:
        return cv2.GaussianBlur(frame, (ksize, ksize), 0)
    return _blur


def apply_sharpen(frame: np.ndarray) -> np.ndarray:
    """Apply sharpening filter."""
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    return cv2.filter2D(frame, -1, kernel)


def adjust_brightness(value: int = 30) -> Callable:
    """
    Create a brightness adjustment function.

    Args:
        value: Brightness adjustment value (-100 to 100)

    Returns:
        Processing function
    """
    def _brightness(frame: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v = cv2.add(v, value)
        v = np.clip(v, 0, 255)
        final_hsv = cv2.merge((h, s, v))
        return cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return _brightness


def adjust_contrast(alpha: float = 1.5) -> Callable:
    """
    Create a contrast adjustment function.

    Args:
        alpha: Contrast control (1.0-3.0, 1.0 is no change)

    Returns:
        Processing function
    """
    def _contrast(frame: np.ndarray) -> np.ndarray:
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
    return _contrast


def apply_threshold(thresh_value: int = 127) -> Callable:
    """
    Create a binary threshold processing function.

    Args:
        thresh_value: Threshold value (0-255)

    Returns:
        Processing function
    """
    def _threshold(frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, thresh_value, 255, cv2.THRESH_BINARY)
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    return _threshold


def add_timestamp(frame: np.ndarray) -> np.ndarray:
    """Add timestamp overlay to frame."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2, cv2.LINE_AA)
    return frame


def add_text_overlay(text: str, position: tuple = (10, 30),
                     color: tuple = (0, 255, 0), thickness: int = 2) -> Callable:
    """
    Create a text overlay processing function.

    Args:
        text: Text to display
        position: (x, y) position for text
        color: BGR color tuple
        thickness: Text thickness

    Returns:
        Processing function
    """
    def _overlay(frame: np.ndarray) -> np.ndarray:
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, color, thickness, cv2.LINE_AA)
        return frame
    return _overlay


# Factory function to create processor with preset modes

def create_processor(mode: ProcessingMode = ProcessingMode.ORIGINAL,
                     **kwargs) -> FrameProcessor:
    """
    Create a frame processor with a preset processing mode.

    Args:
        mode: Processing mode to apply
        **kwargs: Additional parameters for specific modes

    Returns:
        Configured FrameProcessor instance
    """
    processor = FrameProcessor()

    if mode == ProcessingMode.ORIGINAL:
        pass  # No processing

    elif mode == ProcessingMode.GRAYSCALE:
        processor.add_processing_step(convert_to_grayscale)

    elif mode == ProcessingMode.EDGE_DETECTION:
        threshold1 = kwargs.get('threshold1', 100)
        threshold2 = kwargs.get('threshold2', 200)
        processor.add_processing_step(
            lambda frame: apply_edge_detection(frame, threshold1, threshold2)
        )

    elif mode == ProcessingMode.BLUR:
        ksize = kwargs.get('ksize', 5)
        processor.add_processing_step(apply_gaussian_blur(ksize))

    elif mode == ProcessingMode.SHARPEN:
        processor.add_processing_step(apply_sharpen)

    elif mode == ProcessingMode.BRIGHTNESS:
        value = kwargs.get('value', 30)
        processor.add_processing_step(adjust_brightness(value))

    elif mode == ProcessingMode.CONTRAST:
        alpha = kwargs.get('alpha', 1.5)
        processor.add_processing_step(adjust_contrast(alpha))

    elif mode == ProcessingMode.THRESHOLD:
        thresh_value = kwargs.get('thresh_value', 127)
        processor.add_processing_step(apply_threshold(thresh_value))

    return processor


if __name__ == "__main__":
    # Example usage
    print("Frame Processor Module")
    print("Available processing modes:")
    for mode in ProcessingMode:
        print(f"  - {mode.value}")
