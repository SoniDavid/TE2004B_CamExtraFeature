# Quick Reference - Camera Viewer with ArUco

## 🚀 Run Commands

```bash
# Generate printable ArUco markers
python3 utils/generate_aruco_markers.py

# Run main viewer with ArUco detection
python3 viewer/aruco_viewer.py

# Run simple viewer (no ArUco)
python3 viewer/camera_viewer.py
```

## ⌨️ Keyboard Controls

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

## 📝 Configuration

Edit `viewer/aruco_viewer.py`:

```python
CAMERA_URL = "http://10.22.209.148:4747/video"  # Your DroidCam IP
MARKER_SIZE_CM = 10.0   # Measured marker size in cm
FOCAL_LENGTH_PX = 1000.0  # Adjust for accuracy
```

## 📁 File Locations

```
viewer/aruco_viewer.py          ← Main application with ArUco
viewer/camera_viewer.py         ← Simple camera viewer
utils/generate_aruco_markers.py ← Generate markers
aruco_markers/                  ← Generated markers
camera_processing/              ← Core modules
```

## 🎯 Quick Start

1. Generate markers: `python3 utils/generate_aruco_markers.py`
2. Print `aruco_markers/marker_sheet_0.png`
3. Measure printed marker size in cm
4. Update `MARKER_SIZE_CM` in `viewer/aruco_viewer.py`
5. Run: `python3 viewer/aruco_viewer.py`
6. Point camera at printed marker
7. See distance in real-time!

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect to camera | Check camera URL, ensure camera app is running |
| No markers detected | Check lighting, marker should be flat and visible |
| Inaccurate distance | Measure marker accurately, adjust FOCAL_LENGTH_PX |
| Import error | Run from project root: `cd espCamFeature` |

## 💡 Tips

- Use white paper for printing
- Keep markers flat and perpendicular
- Good lighting is essential
- Larger markers = farther detection
- Each marker needs unique ID
