import streamlit as st
import cv2
import numpy as np
from PIL import Image
import sys
import os
import time

# Add parent directory to path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import CameraStreamClient, FrameProcessor, ProcessingMode, create_processor

# Configure Streamlit page
st.set_page_config(
    page_title="Camera Stream Processor",
    page_icon="📷",
    layout="wide"
)

st.title("📷 Live Camera Stream with Processing")
st.write("Stream from HTTP camera with real-time image processing")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Camera stream URL configuration
    stream_url = st.text_input(
        "Camera Stream URL",
        value="http://10.22.209.148:4747/video",
        help="Enter the full URL to your camera stream (MJPEG format)"
    )

    # Processing mode selection
    st.header("🎨 Processing Mode")
    processing_mode = st.selectbox(
        "Select processing mode",
        options=[mode.value for mode in ProcessingMode],
        index=0
    )

    # Mode-specific parameters
    if processing_mode == ProcessingMode.EDGE_DETECTION.value:
        st.subheader("Edge Detection Parameters")
        threshold1 = st.slider("Threshold 1", 0, 255, 100)
        threshold2 = st.slider("Threshold 2", 0, 255, 200)
        mode_kwargs = {'threshold1': threshold1, 'threshold2': threshold2}

    elif processing_mode == ProcessingMode.BLUR.value:
        st.subheader("Blur Parameters")
        ksize = st.slider("Kernel Size", 1, 15, 5, step=2)
        mode_kwargs = {'ksize': ksize}

    elif processing_mode == ProcessingMode.BRIGHTNESS.value:
        st.subheader("Brightness Parameters")
        brightness = st.slider("Brightness", -100, 100, 30)
        mode_kwargs = {'value': brightness}

    elif processing_mode == ProcessingMode.CONTRAST.value:
        st.subheader("Contrast Parameters")
        contrast = st.slider("Contrast", 0.5, 3.0, 1.5, step=0.1)
        mode_kwargs = {'alpha': contrast}

    elif processing_mode == ProcessingMode.THRESHOLD.value:
        st.subheader("Threshold Parameters")
        thresh_value = st.slider("Threshold Value", 0, 255, 127)
        mode_kwargs = {'thresh_value': thresh_value}

    else:
        mode_kwargs = {}

    # Enable/disable processing
    enable_processing = st.checkbox("Enable Processing", value=True)

    # Refresh rate control
    st.header("⚡ Performance")
    refresh_rate = st.slider("Refresh Rate (FPS)", 1, 30, 10, help="Lower FPS = more stable display")

# Initialize session state
if 'camera_client' not in st.session_state:
    st.session_state.camera_client = CameraStreamClient(stream_url)
    st.session_state.camera_client.connect()

if 'frame_count' not in st.session_state:
    st.session_state.frame_count = 0

if 'processor' not in st.session_state:
    st.session_state.processor = create_processor(ProcessingMode.ORIGINAL)

if 'streaming' not in st.session_state:
    st.session_state.streaming = True

# Update processor based on selected mode
mode_enum = ProcessingMode(processing_mode)
st.session_state.processor = create_processor(mode_enum, **mode_kwargs)

if not enable_processing:
    st.session_state.processor.disable()
else:
    st.session_state.processor.enable()

# Control buttons
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("⏹️ Stop Stream" if st.session_state.streaming else "▶️ Start Stream"):
        st.session_state.streaming = not st.session_state.streaming
        st.rerun()

with col2:
    if st.button("🔄 Reconnect"):
        st.session_state.camera_client.disconnect()
        st.session_state.camera_client = CameraStreamClient(stream_url)
        st.session_state.camera_client.connect()
        st.session_state.frame_count = 0
        st.rerun()

# Show current configuration
with st.sidebar:
    st.info(f"""
    **Current Settings:**
    - URL: {stream_url}
    - Mode: {processing_mode}
    - Processing: {'Enabled' if enable_processing else 'Disabled'}
    - FPS: {refresh_rate}
    """)

# Streaming fragment with controlled refresh rate
@st.fragment(run_every=1.0/refresh_rate)
def display_stream():
    if st.session_state.streaming:
        frame = st.session_state.camera_client.get_frame()

        if frame is not None:
            # Process the frame
            processed_frame = st.session_state.processor.process(frame)

            # Convert BGR to RGB for display
            frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)

            # Display the frame
            st.image(frame_rgb, channels="RGB", width="stretch")

            # Update stats
            st.session_state.frame_count += 1

            # Stats in columns
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Frames Processed", st.session_state.frame_count)
            with col2:
                st.success(f"✅ Streaming at {refresh_rate} FPS")
        else:
            st.error("❌ Failed to grab frame from camera stream")
            if st.button("🔄 Retry Connection"):
                st.session_state.camera_client.disconnect()
                st.session_state.camera_client = CameraStreamClient(stream_url)
                st.session_state.camera_client.connect()
                st.rerun()
    else:
        st.info("Stream paused. Click 'Start Stream' to resume.")

# Run the streaming display
display_stream()

# Footer with instructions
st.markdown("---")
st.markdown("""
### 📝 Instructions:
1. **Start IP Webcam** on your phone (or other camera source)
2. Enter the full stream URL in the sidebar (e.g., `http://10.22.209.148:4747/video`)
3. Adjust the **Refresh Rate** slider to control streaming speed (lower = more stable)
4. Select a processing mode and adjust parameters in real-time
5. Use **Stop Stream** to pause, or **Reconnect** to reconnect to the camera

### 🎥 Supported Stream Sources:
- **IP Webcam** (Android app): `http://<phone-ip>:4747/video`
- **DroidCam**: `http://<phone-ip>:4747/mjpegfeed`
- **ESP32-CAM**: `http://<esp-ip>/stream`
- **Any MJPEG stream**: HTTP URLs that provide MJPEG format

### 🔧 Processing Modes:
- **Original**: No processing, raw camera feed
- **Grayscale**: Convert to black and white
- **Edge Detection**: Detect edges using Canny algorithm
- **Blur**: Apply Gaussian blur filter
- **Sharpen**: Enhance image sharpness
- **Brightness**: Adjust image brightness
- **Contrast**: Adjust image contrast
- **Threshold**: Binary threshold (black/white)

### 💡 Tips:
- If you see flickering, reduce the Refresh Rate (FPS)
- The stream automatically connects when the app loads
- Adjust processing parameters in real-time without reconnecting
""")
