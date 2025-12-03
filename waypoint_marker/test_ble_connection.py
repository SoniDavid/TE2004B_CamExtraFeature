"""
BLE Connection Test - Simple LED blink test to verify BLE connectivity
Tests the connection to ESP32-C3 BLE_Sensor_Hub by toggling LED on/off
"""

import asyncio
import time
from ble_client import CarBLEClient

async def test_ble_connection():
    """Test BLE connection by blinking LED on robot"""
    print("BLE Connection Test")
    print("=" * 40)
    print("This will blink the LED on/off every 0.5s")
    print("Press Ctrl+C to stop\n")
    
    # Create client instance
    car = CarBLEClient()
    
    # Connect to the device
    await car.connect()
    
    try:
        print("✓ Connected! Blinking LED...\n")
        while True:
            await car.set_led(0)  # LED OFF
            print("LED: OFF")
            time.sleep(0.5)
            await car.set_led(1)  # LED ON
            print("LED: ON")
            time.sleep(0.5)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        await car.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(test_ble_connection())
    except KeyboardInterrupt:
        print("\n\n✓ Test completed successfully")
    except Exception as e:
        print(f"\n✗ Error: {e}")