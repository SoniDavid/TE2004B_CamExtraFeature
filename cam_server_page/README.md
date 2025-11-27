# Camera Stream Web Application

A Streamlit-based web application that captures your camera feed and displays it in real-time on a web interface.

## Features

- Real-time camera feed streaming
- Web-based interface accessible from any browser
- Stop/Start camera controls
- Responsive layout

## Requirements

- Python 3.10+
- Webcam/Camera device
- All dependencies listed in `requirements.txt`

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the Streamlit application:**
   ```bash
   streamlit run app.py
   ```

2. **Access the web interface:**
   - The application will automatically open in your default browser
   - Or manually navigate to: `http://localhost:8501`

3. **Using the camera:**
   - The camera will start automatically when the page loads
   - Grant camera permissions when prompted by your browser/system
   - Click the "Stop Camera" button to stop the stream
   - Refresh the page to restart the camera

## How It Works

1. **Camera Capture:** Uses OpenCV to capture frames from your default camera (device 0)
2. **Frame Processing:** Converts frames from BGR (OpenCV format) to RGB (display format)
3. **Web Display:** Streams the processed frames to the Streamlit web interface in real-time

## Troubleshooting

### Camera not detected
- Ensure your camera is properly connected
- Check camera permissions for your terminal/Python
- Try a different camera index (change `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` in `app.py`)

### Port already in use
- Stop any running Streamlit instances
- Or specify a different port: `streamlit run app.py --server.port 8502`

### Performance issues
- Lower the camera resolution
- Reduce the frame rate
- Close other applications using the camera

## Project Structure

```
cam_server_page/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Technologies Used

- **Streamlit**: Web framework for Python
- **OpenCV**: Computer vision and camera capture
- **NumPy**: Array operations
- **Pillow**: Image processing

## License

This project is open source and available for personal and educational use.
