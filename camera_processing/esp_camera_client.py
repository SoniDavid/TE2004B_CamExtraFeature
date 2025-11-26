import cv2
import numpy as np
import requests
from typing import Optional, Tuple
import logging
import threading
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraStreamClient:
    """Client to retrieve frames from HTTP video stream (IP Webcam, ESP32-CAM, etc.)."""

    def __init__(self, stream_url: str):
        """
        Initialize camera stream client.

        Args:
            stream_url: Full URL to video stream (e.g., "http://10.22.209.148:4747/video")
        """
        self.stream_url = stream_url
        self.stream = None
        self._is_connected = False
        self._buffer = b''
        self._lock = threading.Lock()
        self._latest_frame = None
        self._boundary = None
        self._stream_iterator = None

    def connect(self, timeout: int = 5) -> bool:
        """
        Connect to video stream.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Test connection with a simple request
            response = requests.head(self.stream_url, timeout=timeout)
            if response.status_code == 200 or response.status_code == 405:
                # 405 is OK - some servers don't support HEAD requests
                logger.info(f"Connected to stream at {self.stream_url}")
                self._is_connected = True
                return True
            else:
                # Try GET request as fallback
                response = requests.get(self.stream_url, stream=True, timeout=timeout)
                if response.status_code == 200:
                    response.close()
                    logger.info(f"Connected to stream at {self.stream_url}")
                    self._is_connected = True
                    return True
                else:
                    logger.error(f"Failed to connect: HTTP {response.status_code}")
                    return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error: {e}")
            self._is_connected = False
            return False

    def start_stream(self) -> bool:
        """
        Start MJPEG stream.

        Returns:
            True if stream started successfully
        """
        try:
            if self.stream is not None:
                try:
                    self.stream.close()
                except:
                    pass

            logger.info(f"Starting stream: {self.stream_url}")
            self.stream = requests.get(self.stream_url, stream=True, timeout=None)

            if self.stream.status_code == 200:
                # Extract boundary from Content-Type header
                content_type = self.stream.headers.get('Content-Type', '')
                logger.info(f"Content-Type: {content_type}")

                # Look for boundary in header (multiple patterns)
                # Example formats:
                #   "multipart/x-mixed-replace;boundary=--dcmjpeg"
                #   "multipart/x-mixed-replace; boundary=myboundary"
                #   "multipart/x-mixed-replace;boundary=123456789000000000000987654321"
                match = re.search(r'boundary=([^\s;]+)', content_type)
                if match:
                    boundary_str = match.group(1).strip()
                    # Remove leading dashes if present in the header
                    boundary_str = boundary_str.lstrip('-')
                    self._boundary = boundary_str.encode()
                    logger.info(f"Found boundary: {self._boundary}")

                # Create persistent iterator with smaller chunks for better responsiveness
                self._stream_iterator = self.stream.iter_content(chunk_size=1024)

                logger.info("Stream started successfully")
                self._is_connected = True
                self._buffer = b''
                return True
            else:
                logger.error(f"Failed to start stream: HTTP {self.stream.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return False

    def _extract_frame_from_buffer(self) -> Optional[np.ndarray]:
        """
        Extract a single JPEG frame from the buffer.

        Returns:
            Decoded frame or None
        """
        # First, try to find boundary markers if they exist
        if self._boundary:
            # Look for boundary in buffer
            boundary_start = self._buffer.find(b'--' + self._boundary)
            if boundary_start != -1:
                # Find next boundary
                next_boundary = self._buffer.find(b'--' + self._boundary, boundary_start + len(self._boundary))
                if next_boundary != -1:
                    # Extract chunk between boundaries
                    chunk = self._buffer[boundary_start:next_boundary]
                    
                    # Find JPEG in this chunk
                    jpg_start = chunk.find(b'\xff\xd8')
                    jpg_end = chunk.find(b'\xff\xd9')
                    
                    if jpg_start != -1 and jpg_end != -1:
                        jpg = chunk[jpg_start:jpg_end+2]
                        
                        # Remove processed data
                        self._buffer = self._buffer[next_boundary:]
                        
                        # Decode
                        try:
                            frame = cv2.imdecode(
                                np.frombuffer(jpg, dtype=np.uint8),
                                cv2.IMREAD_COLOR
                            )
                            if frame is not None:
                                return frame
                        except Exception as e:
                            logger.error(f"Error decoding JPEG: {e}")
        
        # Fallback: Find JPEG start and end markers directly
        start = self._buffer.find(b'\xff\xd8')  # JPEG start (SOI)
        end = self._buffer.find(b'\xff\xd9')    # JPEG end (EOI)

        if start != -1 and end != -1 and end > start:
            # Extract JPEG data
            jpg = self._buffer[start:end+2]

            # Remove processed data from buffer
            self._buffer = self._buffer[end+2:]

            # Decode JPEG to frame
            try:
                frame = cv2.imdecode(
                    np.frombuffer(jpg, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )
                if frame is not None:
                    return frame
            except Exception as e:
                logger.error(f"Error decoding JPEG: {e}")

        return None

    def get_frame(self, timeout: float = 10.0) -> Optional[np.ndarray]:
        """
        Get next frame from stream.

        Args:
            timeout: Maximum time to wait for a frame in seconds

        Returns:
            Frame as numpy array (BGR format) or None if failed
        """
        if self.stream is None or self._stream_iterator is None:
            logger.info("Stream not started, attempting to start...")
            if not self.start_stream():
                logger.error("Failed to start stream")
                return None

        try:
            # Keep reading from the persistent stream until we get a complete frame
            while True:
                # First check if we already have a frame in the buffer
                frame = self._extract_frame_from_buffer()
                if frame is not None:
                    with self._lock:
                        self._latest_frame = frame
                    return frame

                # Read next chunk from stream
                try:
                    chunk = next(self._stream_iterator)
                    if chunk:
                        self._buffer += chunk

                        # Prevent buffer from growing too large
                        if len(self._buffer) > 500000:
                            # Find the last JPEG start marker and keep from there
                            last_jpeg_start = self._buffer.rfind(b'\xff\xd8')
                            if last_jpeg_start > 0:
                                self._buffer = self._buffer[last_jpeg_start:]
                            else:
                                # Keep only the last 100KB
                                self._buffer = self._buffer[-100000:]

                except StopIteration:
                    logger.warning("Stream ended")
                    self.stop_stream()
                    return None
                except Exception as e:
                    logger.error(f"Error reading chunk: {e}")
                    self.stop_stream()
                    return None

        except Exception as e:
            logger.error(f"Error getting frame: {e}")
            self.stop_stream()
            return None

    def read_stream(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read next frame from stream (OpenCV-compatible interface).

        Returns:
            Tuple of (success, frame) where frame is numpy array or None
        """
        frame = self.get_frame()
        if frame is not None:
            return True, frame
        return False, None

    def stop_stream(self):
        """Stop the video stream."""
        if self.stream is not None:
            try:
                self.stream.close()
            except:
                pass
            self.stream = None
            self._stream_iterator = None
            self._buffer = b''
            logger.info("Stream stopped")

    def is_connected(self) -> bool:
        """Check if connected to stream."""
        return self._is_connected and self.stream is not None

    def disconnect(self):
        """Disconnect from stream."""
        self.stop_stream()
        self._is_connected = False
        logger.info("Disconnected from stream")


# Backward compatibility alias
ESPCameraClient = CameraStreamClient


def test_camera_connection(stream_url: str) -> bool:
    """
    Test connection to video stream.

    Args:
        stream_url: Full URL to video stream

    Returns:
        True if connection successful
    """
    client = CameraStreamClient(stream_url)
    return client.connect()


if __name__ == "__main__":
    # Example usage
    STREAM_URL = "http://10.22.209.148:4747/video"

    client = CameraStreamClient(STREAM_URL)

    if client.connect():
        print("Connection test successful!")
        print("Starting stream and getting frames...")

        if client.start_stream():
            for i in range(10):
                print(f"Getting frame {i+1}...")
                frame = client.get_frame()
                if frame is not None:
                    print(f"✓ Frame {i+1} shape: {frame.shape}")
                    if i < 3:  # Save only first 3 frames
                        cv2.imwrite(f"test_frame_{i+1}.jpg", frame)
                else:
                    print(f"✗ Failed to get frame {i+1}")
                    break

            client.disconnect()
            print("\n✓ Test completed successfully!")
        else:
            print("✗ Failed to start stream")
    else:
        print("✗ Failed to connect to stream")
