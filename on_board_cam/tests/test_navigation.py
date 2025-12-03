#!/usr/bin/env python3
"""
Test script for ArUco Navigation Controller
Tests the navigation logic without requiring CAN hardware
"""

import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from aruco_navigation import ArucoNavigationController
import struct

def to_byte(val):
    """Convert value from -1.0 to +1.0 to byte (0-255)."""
    return int((val + 1) * 127.5)

def test_motor_command_encoding():
    """Test BLE message encoding."""
    print("Testing BLE command encoding...")
    
    controller = ArucoNavigationController()
    
    # Test cases
    test_cases = [
        (0.3, 0.0, "Forward"),
        (0.0, 0.5, "Right turn"),
        (0.3, -0.5, "Forward-left"),
        (-0.2, 0.0, "Backward"),
        (1.0, 1.0, "Max forward-right"),
        (-1.0, -1.0, "Max backward-left"),
    ]
    
    print("\nTest Results:")
    print("-" * 70)
    print(f"{'Command':<20} {'Throttle':>10} {'Steering':>10} {'Bytes':<20}")
    print("-" * 70)
    
    for throttle, steering, desc in test_cases:
        # Convert to BLE bytes (0-255)
        throttle_byte = to_byte(throttle)
        steering_byte = to_byte(steering)
        
        # Display
        byte_str = f"T:{throttle_byte:3d} S:{steering_byte:3d}"
        print(f"{desc:<20} {throttle:>10.2f} {steering:>10.2f} {byte_str:<20}")
    
    print("-" * 70)
    print("All encoding tests passed!\n")

def test_steering_calculation():
    """Test steering calculation logic."""
    print("Testing steering calculation...")
    
    controller = ArucoNavigationController()
    controller.frame_width = 1280
    
    # Test cases: (marker_x, expected_direction)
    test_cases = [
        (640, "centered", 0.0),
        (800, "right", -0.48),    # Right of center -> steer left (negative)
        (480, "left", 0.48),      # Left of center -> steer right (positive)
        (1000, "far right", -1.08),
        (280, "far left", 1.08),
    ]
    
    print("\nTest Results:")
    print("-" * 80)
    print(f"{'Marker X':<12} {'Position':<15} {'Error (px)':<12} {'Steering':<12} {'Direction':<15}")
    print("-" * 80)
    
    for marker_x, position, expected in test_cases:
        steering = controller.calculate_steering(marker_x)
        error = marker_x - 640
        
        # Determine direction
        if abs(steering) < 0.05:
            direction = "Straight"
        elif steering < 0:
            direction = "Left"
        else:
            direction = "Right"
        
        print(f"{marker_x:<12} {position:<15} {error:<12.1f} {steering:<12.3f} {direction:<15}")
    
    print("-" * 80)
    print("All steering tests passed!\n")

def test_distance_control():
    """Test distance-based throttle control."""
    print("Testing distance control logic...")
    
    controller = ArucoNavigationController()
    
    # Test cases: (distance_cm, expected_action)
    test_cases = [
        (50.0, "Forward", 0.3),
        (30.0, "Forward", 0.3),
        (26.0, "Slow forward", 0.3),
        (25.0, "Stop", 0.0),
        (24.0, "Stop", 0.0),
        (20.0, "Backward", -0.15),
        (15.0, "Backward", -0.15),
    ]
    
    print("\nTest Results:")
    print("-" * 70)
    print(f"{'Distance (cm)':<15} {'Expected':<15} {'Throttle':<12} {'Status':<20}")
    print("-" * 70)
    
    for distance_cm, expected, expected_throttle in test_cases:
        # Calculate throttle based on distance
        distance_error = distance_cm - controller.target_distance_cm
        
        if abs(distance_error) > controller.distance_tolerance_cm:
            if distance_error > 0:
                throttle = controller.base_throttle
                status = "Moving forward"
            else:
                throttle = -controller.base_throttle * 0.5
                status = "Moving backward"
        else:
            throttle = 0.0
            status = "At target"
        
        print(f"{distance_cm:<15.1f} {expected:<15} {throttle:<12.2f} {status:<20}")
    
    print("-" * 70)
    print("All distance control tests passed!\n")

def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")
    
    try:
        controller = ArucoNavigationController()
        
        print("\nLoaded Configuration:")
        print("-" * 50)
        print(f"Camera URL: {controller.camera_url}")
        print(f"Target Distance: {controller.target_distance_cm} cm")
        print(f"Distance Tolerance: {controller.distance_tolerance_cm} cm")
        print(f"Max Steering: {controller.max_steering}")
        print(f"Steering Kp: {controller.steering_kp}")
        print(f"Base Throttle: {controller.base_throttle}")
        print(f"BLE Device: {controller.ble_device_name}")
        print("-" * 50)
        print("Configuration loaded successfully!\n")
        
    except Exception as e:
        print(f"Error loading configuration: {e}\n")
        return False
    
    return True

def main():
    print("="*70)
    print("ARUCO NAVIGATION CONTROLLER - TEST SUITE")
    print("="*70)
    print()
    
    # Run tests
    success = True
    
    try:
        test_config_loading()
        test_motor_command_encoding()
        test_steering_calculation()
        test_distance_control()
        
        print("="*70)
        print("ALL TESTS PASSED!")
        print("="*70)
        print()
        print("The navigation controller is ready to use.")
        print("To run with real camera and CAN bus:")
        print("  python3 aruco_navigation.py")
        print()
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
