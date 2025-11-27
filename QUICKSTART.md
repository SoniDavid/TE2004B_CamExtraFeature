# Quick Reference - Camera Viewer with ArUco

## Run Commands

```bash
# Generate printable ArUco markers
python3 utils/generate_aruco_markers.py

# Run main viewer with ArUco detection
python3 viewer/aruco_viewer.py

# Run simple viewer (no ArUco)
python3 viewer/camera_viewer.py
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `a` | Toggle ArUco detection ON/OFF |
| `d` | Toggle distance display |
| `i` | Toggle marker ID display |
| `g` | Grayscale mode |
| `e` | Edge detection |
| `o` | Original (no processing) |
| `h` | Show help |
| `q` | Quit |

## Configuration

Edit `config.yaml`

```yaml
camera:
  url: "http://192.168.1.100:4747/video"  
  buffer_size: 1                          
  
aruco:
  marker_size_cm: 15.0      
  focal_length_px: 490.20   
  dictionary_type: "DICT_6X6_250"

display:
  window_width: 1280
  window_height: 720
```

**To calibrate focal length for accurate depth:**
```bash
python3 utils/calibrate_focal_length.py
```

## File Locations

```
config.yaml                     - Configuration file
viewer/aruco_viewer.py          - Main application with ArUco
viewer/camera_viewer.py         - Simple camera viewer
utils/generate_aruco_markers.py - Generate markers
utils/calibrate_focal_length.py - Calibrate depth measurement
aruco_markers/                  - Generated markers
camera_processing/              - Core modules
```

## Quick Start Steps

1. Edit `config.yaml` with your camera URL
2. Generate markers: `python3 utils/generate_aruco_markers.py`
3. Print `aruco_markers/printable_sheet.png`
4. Measure printed marker size in cm
5. Update `marker_size_cm` in `config.yaml`
6. Calibrate focal length: `python3 utils/calibrate_focal_length.py`
7. Run: `python3 viewer/aruco_viewer.py`
8. Point camera at printed marker
9. See distance in real-time

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect to camera | Check camera URL in config.yaml, ensure camera app is running |
| No markers detected | Check lighting, marker should be flat with white border |
| Inaccurate distance | Measure marker accurately, calibrate focal_length_px in config.yaml |
| Import error | Run from project root directory |
