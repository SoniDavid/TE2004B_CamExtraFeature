import asyncio
import sys
import argparse
import tkinter as tk
from pathlib import Path
from ble_client import CarBLEClient

# Global variables
last_waypoint = None


async def main_async():
    """Main asynchronous function that handles BLE and GUI."""

    # Recommended for Windows when using asyncio with BLE
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Workspace dimensions in centimeters
    # These should match your physical workspace size
    max_x = 180.0  # Width in cm
    max_y = 120.0  # Height in cm

    # Create BLE client and attempt connection
    car = CarBLEClient()
    print("Connecting via BLE...")
    try:
        await car.connect()
        if car.client is not None:
            print("Connected to robot via BLE")
        else:
            print("Running in simulation mode (BLE not available)")
    except Exception as e:
        print(f"Could not connect to BLE device: {e}")
        print("Running in simulation mode")

    # Window size in pixels
    WIDTH = 800
    HEIGHT = 600

    # Create main window
    root = tk.Tk()
    root.title(f"Waypoint Control - Workspace: {max_x}cm × {max_y}cm")
    root.configure(bg='#f0f0f0')

    # Status frame at the top
    status_frame = tk.Frame(root, bg='#f0f0f0')
    status_frame.pack(pady=10)

    # Label to display the selected coordinate
    coord_var = tk.StringVar()
    coord_var.set("Click on the workspace to set a waypoint")
    label = tk.Label(status_frame, textvariable=coord_var, font=("Arial", 12, "bold"), bg='#f0f0f0')
    label.pack()

    # Info label
    info_label = tk.Label(status_frame, 
                          text="Click anywhere to send waypoint coordinates to robot", 
                          font=("Arial", 9), 
                          fg="gray", 
                          bg='#f0f0f0')
    info_label.pack(pady=(0, 5))

    # Canvas frame
    canvas_frame = tk.Frame(root, bg='white', relief=tk.SUNKEN, borderwidth=2)
    canvas_frame.pack(padx=20, pady=(0, 20))

    # Canvas that represents the coordinate plane
    canvas = tk.Canvas(canvas_frame, width=WIDTH, height=HEIGHT, bg="white", highlightthickness=0)
    canvas.pack()

    # Draw border and reference axes
    canvas.create_rectangle(2, 2, WIDTH - 2, HEIGHT - 2, outline="black", width=2)
    canvas.create_line(0, HEIGHT / 2, WIDTH, HEIGHT / 2, fill="lightgray", dash=(5, 5))
    canvas.create_line(WIDTH / 2, 0, WIDTH / 2, HEIGHT, fill="lightgray", dash=(5, 5))
    
    # Add coordinate labels at corners
    canvas.create_text(10, HEIGHT - 10, text="(0, 0)", anchor='sw', fill='gray', font=("Arial", 9))
    canvas.create_text(WIDTH - 10, HEIGHT - 10, text=f"({max_x:.0f}, 0)", anchor='se', fill='gray', font=("Arial", 9))
    canvas.create_text(10, 10, text=f"(0, {max_y:.0f})", anchor='nw', fill='gray', font=("Arial", 9))
    canvas.create_text(WIDTH - 10, 10, text=f"({max_x:.0f}, {max_y:.0f})", anchor='ne', fill='gray', font=("Arial", 9))

    loop = asyncio.get_running_loop()
    running = True

    def on_click(event):
        """When you click on the canvas, calculate the coordinate and send it via BLE."""
        global last_waypoint

        # Click coordinates in pixels
        px = event.x
        py = event.y

        # Convert to physical coordinates (cm)
        coord_x = px * max_x / WIDTH
        coord_y = (HEIGHT - py) * max_y / HEIGHT

        coord_x_round = round(coord_x, 1)
        coord_y_round = round(coord_y, 1)

        last_waypoint = (coord_x_round, coord_y_round)
        print(f"→ Waypoint set: ({coord_x_round}, {coord_y_round}) cm")

        # Update GUI text
        coord_var.set(f"Waypoint: ({coord_x_round}, {coord_y_round}) cm | Status: Sending...")

        # Draw a marker where the click occurred
        canvas.delete("marker")
        r = 8
        canvas.create_oval(
            px - r, py - r, px + r, py + r,
            fill="#ff4444",
            outline="#cc0000",
            width=2,
            tags="marker"
        )
        # Add crosshair
        canvas.create_line(px - r - 5, py, px - r, py, fill="#cc0000", width=2, tags="marker")
        canvas.create_line(px + r, py, px + r + 5, py, fill="#cc0000", width=2, tags="marker")
        canvas.create_line(px, py - r - 5, px, py - r, fill="#cc0000", width=2, tags="marker")
        canvas.create_line(px, py + r, px, py + r + 5, fill="#cc0000", width=2, tags="marker")
        
        # Add coordinate label
        canvas.create_text(
            px, py - r - 15,
            text=f"({coord_x_round}, {coord_y_round})",
            fill="#cc0000",
            font=("Arial", 10, "bold"),
            tags="marker"
        )

        # Send waypoint via BLE without blocking the GUI
        async def send_wp():
            try:
                # Use CarBLEClient.set_waypoint(x, y, omega) method
                await car.set_waypoint(coord_x_round, coord_y_round)
                coord_var.set(f"Waypoint: ({coord_x_round}, {coord_y_round}) cm | Status: ✓ Sent")
            except Exception as e:
                print(f"  ✗ Error sending waypoint: {e}")
                coord_var.set(f"Waypoint: ({coord_x_round}, {coord_y_round}) cm | Status: ✗ Error")

        loop.create_task(send_wp())

    def on_close():
        nonlocal running
        running = False
        root.destroy()

    canvas.bind("<Button-1>", on_click)
    root.protocol("WM_DELETE_WINDOW", on_close)

    # Main loop integrating Tkinter with asyncio
    print("\nGUI ready. Click anywhere to set waypoints.\n")
    try:
        while running:
            root.update()
            await asyncio.sleep(0.01)
    finally:
        print("\nClosing connection...")
        try:
            await car.disconnect()
        except Exception as e:
            print(f"Error disconnecting: {e}")
        print("Program terminated.")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
