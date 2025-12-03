#!/usr/bin/env python3
"""
Quick test of simulation mode - no GUI, just verify BLE simulation works
"""

import asyncio
import sys
from pathlib import Path

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ble_client import CarBLEClient

async def test_simulation():
    """Test BLE client in simulation mode."""
    print("\n" + "="*60)
    print("Testing BLE Client - Simulation Mode")
    print("="*60 + "\n")
    
    # Create client
    print("Creating BLE client...")
    car = CarBLEClient()
    
    # Try to connect (will go to simulation if no device)
    print("Attempting connection...")
    await car.connect()
    
    print("\n" + "-"*60)
    print("Sending test commands...")
    print("-"*60 + "\n")
    
    # Test manual control
    print("Testing Manual Control:")
    await car.set_throttle(0.5)
    await car.set_steering(-0.3)
    await car.set_omega(0.2)
    await car.set_led(1)
    
    print("\nTesting Waypoint:")
    await car.set_waypoint(100.5, 75.3, 45.0)
    
    print("\nTesting Stop:")
    await car.set_throttle(0.0)
    await car.set_steering(0.0)
    await car.set_omega(0.0)
    
    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60 + "\n")
    
    # Disconnect
    await car.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(test_simulation())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
