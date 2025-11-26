#!/usr/bin/env python3
"""
ArUco Marker Generator
======================

Generate ArUco markers for printing and depth estimation.
"""

import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from camera_processing import save_aruco_marker, generate_aruco_marker
import cv2


def main():
    print("="*60)
    print("ARUCO MARKER GENERATOR")
    print("="*60)
    
    # Configuration
    print("\nAvailable ArUco dictionaries:")
    print("  1. DICT_4X4_50   (Recommended for small markers)")
    print("  2. DICT_6X6_250  (Recommended - good balance)")
    print("  3. DICT_7X7_1000 (More unique IDs)")
    
    dict_choice = input("\nChoose dictionary (default 2): ").strip() or "2"
    
    dict_map = {
        "1": "DICT_4X4_50",
        "2": "DICT_6X6_250",
        "3": "DICT_7X7_1000"
    }
    
    aruco_dict_type = dict_map.get(dict_choice, "DICT_6X6_250")
    print(f"Using: {aruco_dict_type}")
    
    # Number of markers
    num_markers = input("\nHow many markers to generate? (default 10): ").strip() or "10"
    num_markers = int(num_markers)
    
    # Marker size
    marker_size = input("\nMarker size in pixels (default 400): ").strip() or "400"
    marker_size = int(marker_size)
    
    # Output directory
    output_dir = input("\nOutput directory (default 'aruco_markers'): ").strip() or "aruco_markers"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Generating {num_markers} markers...")
    print(f"{'='*60}\n")
    
    for i in range(num_markers):
        filename = os.path.join(output_dir, f"marker_{i}.png")
        save_aruco_marker(i, filename, marker_size=marker_size, aruco_dict_type=aruco_dict_type)
        print(f"✓ Generated marker ID {i} → {filename}")
    
    # Create a sheet with multiple markers
    print(f"\n{'='*60}")
    print("Creating marker sheet...")
    print(f"{'='*60}\n")
    
    # Create a grid of markers (2x3 = 6 markers per sheet)
    markers_per_row = 3
    markers_per_col = 2
    markers_per_sheet = markers_per_row * markers_per_col
    
    num_sheets = (num_markers + markers_per_sheet - 1) // markers_per_sheet
    
    for sheet_num in range(num_sheets):
        # Create white canvas (A4-ish proportions)
        sheet_height = 1400
        sheet_width = 1000
        sheet = 255 * np.ones((sheet_height, sheet_width), dtype=np.uint8)
        
        # Calculate marker placement
        margin = 50
        spacing_x = (sheet_width - 2 * margin) // markers_per_row
        spacing_y = (sheet_height - 2 * margin) // markers_per_col
        
        marker_display_size = min(spacing_x, spacing_y) - 40
        
        for row in range(markers_per_col):
            for col in range(markers_per_row):
                marker_idx = sheet_num * markers_per_sheet + row * markers_per_row + col
                
                if marker_idx >= num_markers:
                    break
                
                # Generate marker
                marker = generate_aruco_marker(marker_idx, marker_display_size, aruco_dict_type)
                
                # Calculate position
                x = margin + col * spacing_x + (spacing_x - marker_display_size) // 2
                y = margin + row * spacing_y + (spacing_y - marker_display_size) // 2
                
                # Place marker on sheet
                sheet[y:y+marker_display_size, x:x+marker_display_size] = marker
                
                # Add label
                label = f"ID: {marker_idx}"
                cv2.putText(sheet, label, (x, y + marker_display_size + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
        
        sheet_filename = os.path.join(output_dir, f"marker_sheet_{sheet_num}.png")
        cv2.imwrite(sheet_filename, sheet)
        print(f"✓ Created marker sheet → {sheet_filename}")
    
    print(f"\n{'='*60}")
    print("DONE!")
    print(f"{'='*60}")
    print(f"\nMarkers saved in: {output_dir}/")
    print("\nNext steps:")
    print("  1. Print the marker sheets (use marker_sheet_*.png)")
    print("  2. Measure the printed marker size in cm")
    print("  3. Update MARKER_SIZE_CM in camera_viewer_aruco.py")
    print("  4. Run: python3 viewer/camera_viewer_aruco.py")
    print("\nTips:")
    print("  - Print on white paper for best detection")
    print("  - Keep markers flat and well-lit")
    print("  - Avoid glare and shadows")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import numpy as np
    main()
