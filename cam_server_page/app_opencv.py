import streamlit as st
import cv2
import time

# Configure Streamlit page
st.set_page_config(
    page_title="Camera Stream",
    page_icon="📷",
    layout="wide"
)

st.title("📷 Live Camera Feed")
st.write("Fast camera viewer - ESP32-CAM, DroidCam, IP Webcam compatible")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Camera URL configuration
    camera_url = st.text_input(
        "Camera Stream URL",
        value="http://10.22.209.148:4747/video",
        help="Enter the URL of your camera stream"
    )
    
    st.caption("Common formats:")
    st.caption("• ESP32-CAM: http://192.168.1.100/stream")
    st.caption("• DroidCam: http://10.22.209.148:4747/video")
    st.caption("• IP Webcam: http://192.168.1.100:8080/video")

# Initialize session state
if 'cap' not in st.session_state:
    st.session_state.cap = None
    st.session_state.connected = False

if 'frame_count' not in st.session_state:
    st.session_state.frame_count = 0

# Connection management
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🔌 Connect to Camera", type="primary"):
        if st.session_state.cap is not None:
            st.session_state.cap.release()
        
        st.session_state.cap = cv2.VideoCapture(camera_url)
        
        if st.session_state.cap.isOpened():
            st.session_state.connected = True
            st.success("✓ Connected successfully!")
        else:
            st.session_state.connected = False
            st.error("✗ Failed to connect to camera")

with col2:
    if st.button("🔌 Disconnect"):
        if st.session_state.cap is not None:
            st.session_state.cap.release()
            st.session_state.cap = None
        st.session_state.connected = False
        st.info("Disconnected from camera")

# Main display area
if st.session_state.connected and st.session_state.cap is not None:
    # Create placeholder for video
    video_placeholder = st.empty()
    stats_placeholder = st.empty()
    
    # Stream loop
    while st.session_state.connected:
        ret, frame = st.session_state.cap.read()
        
        if not ret or frame is None:
            st.error("Failed to read frame from camera. Stream may have ended.")
            st.session_state.connected = False
            break
        
        # Convert BGR to RGB for display (no processing)
        display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Display
        video_placeholder.image(
            display_frame,
            channels="RGB",
            width="stretch",
            caption=f"Frame: {st.session_state.frame_count}"
        )
        
        # Update stats
        st.session_state.frame_count += 1
        stats_placeholder.metric("Frames Displayed", st.session_state.frame_count)
        
        # Small delay to prevent overwhelming the browser
        time.sleep(0.033)  # ~30 FPS max
        
else:
    st.info("👆 Click 'Connect to Camera' to start streaming")
    
    # Show helpful information
    with st.expander("📖 Camera URL Examples"):
        st.markdown("""
        **ESP32-CAM:**
        ```
        http://192.168.1.100/stream
        ```
        
        **DroidCam:**
        ```
        http://10.22.209.148:4747/video
        ```
        
        **IP Webcam:**
        ```
        http://192.168.1.100:8080/video
        ```
        
        **Troubleshooting:**
        - Ensure camera/app is running
        - Check you're on the same WiFi network
        - Try opening the URL in a browser first
        """)

# Cleanup on app close
if not st.session_state.get('connected', False):
    if st.session_state.get('cap') is not None:
        st.session_state.cap.release()
