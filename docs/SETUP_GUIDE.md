# ESP32-CAM Integration Guide

This guide explains how to set up and use the ESP32-CAM with Python processing and Streamlit visualization.

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   ESP32-CAM     │ HTTP │  camera_processing│      │  cam_server_page│
│  (Arduino .ino) │─────>│   (Python)        │─────>│   (Streamlit)   │
│                 │      │                   │      │                 │
│ • Captures video│      │ • Fetches frames  │      │ • Web interface │
│ • WiFi server   │      │ • Processes images│      │ • Live display  │
│ • /stream       │      │ • Applies filters │      │ • Controls      │
│ • /capture      │      │                   │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

## Setup Steps

### 1. Prepare ESP32-CAM Hardware

1. **Upload Arduino Code:**
   - Open Arduino IDE
   - Install ESP32 board support (if not already installed)
   - Open `CameraWebServer/CameraWebServer.ino`
   
2. **Configure WiFi:**
   Edit these lines in the .ino file with your WiFi credentials:
   ```cpp
   const char *ssid = "YOUR_WIFI_NAME";
   const char *password = "YOUR_WIFI_PASSWORD";
   ```

3. **Upload to ESP32-CAM:**
   - Select the correct board (e.g., AI Thinker ESP32-CAM)
   - Select the correct port
   - Upload the code

4. **Get ESP32-CAM IP Address:**
   - Open Serial Monitor (115200 baud)
   - Wait for "WiFi connected"
   - Note the IP address printed, e.g.:
     ```
     Camera Ready! Use 'http://192.168.1.100' to connect
     ```
   - **This is NOT localhost** - it's the ESP's IP on your local network

### 2. Test ESP32-CAM Connection

Run the test script to verify everything is working:

```bash
python test_esp_connection.py
```

This will:
- Check Python imports
- Test connection to your ESP32-CAM
- Capture a test frame
- Verify processing works

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- streamlit - Web interface
- opencv-python - Image processing
- numpy - Array operations
- Pillow - Image handling
- requests - HTTP client for ESP32-CAM

### 4. Try the Simple Example

Test frame capture and processing:

```bash
python simple_capture_example.py
```

This will:
- Connect to ESP32-CAM
- Capture one frame
- Process it with edge detection
- Save original and processed images to `output/` folder

### 5. Run Streamlit App

Start the web interface:

```bash
cd cam_server_page
streamlit run app.py
```

Then:
1. Open the URL shown (typically http://localhost:8501)
2. Enter your ESP32-CAM IP address in the sidebar
3. Select processing mode
4. Adjust parameters
5. View the live processed stream!

## Project Structure

```
espCamFeature/
├── CameraWebServer/          # Arduino ESP32-CAM code
│   ├── CameraWebServer.ino   # Main Arduino sketch
│   ├── app_httpd.cpp         # HTTP server implementation
│   ├── camera_index.h        # Web interface HTML
│   └── ...
│
├── camera_processing/        # Python processing module
│   ├── __init__.py           # Module exports
│   ├── esp_camera_client.py # ESP32-CAM HTTP client
│   └── frame_processor.py    # Image processing pipeline
│
├── cam_server_page/          # Streamlit web app
│   ├── app.py                # Main Streamlit application
│   └── README.md             # App documentation
│
├── test_esp_connection.py    # Connection test script
├── simple_capture_example.py # Simple usage example
└── requirements.txt          # Python dependencies
```

## How It Works

### 1. ESP32-CAM (Hardware)

The ESP32-CAM runs Arduino code that:
- Initializes the camera
- Connects to your WiFi network
- Starts an HTTP server on port 80
- Provides endpoints:
  - `/stream` - MJPEG video stream
  - `/capture` - Single JPEG frame

### 2. camera_processing (Python Module)

**ESPCameraClient**: Connects to ESP32-CAM via HTTP
```python
from camera_processing import ESPCameraClient

client = ESPCameraClient("192.168.1.100")
client.connect()
frame = client.get_frame()  # Returns numpy array (BGR)
```

**FrameProcessor**: Processes images with various filters
```python
from camera_processing import FrameProcessor, ProcessingMode, create_processor

# Method 1: Use predefined processor
processor = create_processor(ProcessingMode.EDGE_DETECTION, threshold1=100, threshold2=200)
processed = processor.process(frame)

# Method 2: Build custom pipeline
processor = FrameProcessor()
processor.add_processing_step(convert_to_grayscale)
processor.add_processing_step(apply_blur)
processed = processor.process(frame)
```

### 3. cam_server_page (Streamlit App)

The Streamlit app provides:
- Web interface for live streaming
- Real-time processing controls
- Multiple processing modes:
  - Original
  - Grayscale
  - Edge Detection
  - Blur
  - Sharpen
  - Brightness adjustment
  - Contrast adjustment
  - Threshold

## Troubleshooting

### "Failed to connect to ESP32-CAM"

**Check:**
1. ESP32-CAM is powered on and running
2. You're on the same WiFi network as the ESP32-CAM
3. IP address is correct (check Serial Monitor)
4. Try accessing `http://YOUR_ESP_IP` in a web browser
5. Firewall isn't blocking the connection

### "Import error" in Python

**Fix:**
```bash
# Make sure you're in the project root directory
cd /home/soni/reto_embebidos/espCamFeature

# Install dependencies
pip install -r requirements.txt

# Test imports
python test_esp_connection.py
```

### "Camera init failed" on ESP32-CAM

**Check:**
1. Camera module is properly connected
2. Correct board configuration in `board_config.h`
3. Sufficient power supply (camera needs good power)
4. Try pressing the reset button

### Slow frame rate

**Optimize:**
1. Reduce frame size in .ino file:
   ```cpp
   s->set_framesize(s, FRAMESIZE_QVGA);  // Smaller = faster
   ```
2. Increase JPEG quality (lower number):
   ```cpp
   config.jpeg_quality = 10;  // 0-63, lower = better quality
   ```
3. Use simpler processing modes (Original or Grayscale)

## Understanding IP Addresses

**Important:** The ESP32-CAM does NOT create "localhost"!

- **localhost** (`127.0.0.1`) = Your computer
- **ESP32-CAM IP** (e.g., `192.168.1.100`) = The ESP device on your WiFi network

When you upload the .ino code:
1. ESP32-CAM connects to your WiFi
2. Your router assigns it an IP address
3. This IP is printed in the Serial Monitor
4. You use this IP to connect from Python

## Advanced Usage

### Custom Processing Pipeline

```python
from camera_processing import FrameProcessor
import cv2

processor = FrameProcessor()

# Add custom function
def my_custom_filter(frame):
    # Your processing code
    return cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

processor.add_processing_step(my_custom_filter)
processed = processor.process(frame)
```

### Continuous Stream Processing

```python
client = ESPCameraClient("192.168.1.100")
client.connect()

try:
    while True:
        frame = client.get_frame()
        if frame is not None:
            processed = processor.process(frame)
            cv2.imshow("Processed", processed)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
finally:
    client.disconnect()
    cv2.destroyAllWindows()
```

## Next Steps

1. ✅ Upload .ino code to ESP32-CAM
2. ✅ Get ESP IP from Serial Monitor
3. ✅ Run `python test_esp_connection.py`
4. ✅ Try `python simple_capture_example.py`
5. ✅ Launch Streamlit app: `cd cam_server_page && streamlit run app.py`
6. 🎉 Enjoy your ESP32-CAM system!

## Support

If you encounter issues:
1. Check Serial Monitor output from ESP32-CAM
2. Verify network connectivity
3. Test ESP IP in web browser first
4. Run test_esp_connection.py for diagnostics
