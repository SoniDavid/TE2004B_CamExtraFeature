#!/usr/bin/env python3
"""
Simple Control GUI - Manual + Waypoint Only (No Camera Dependencies)
Fast and lightweight version for basic control
"""

import asyncio
import sys
import tkinter as tk
import threading
from pathlib import Path

from ble_client import CarBLEClient

try:
    import combined_input as inp
    MANUAL_CONTROL_AVAILABLE = True
except ImportError:
    MANUAL_CONTROL_AVAILABLE = False
    print("⚠ Manual control not available")


def load_scales():
    try:
        config_path = Path(__file__).parent / "scales.txt"
        with open(config_path) as f:
            lines = f.read().strip().split('\n')
            return float(lines[0]), float(lines[1]), float(lines[2])
    except:
        return 1.0, 0.8, 0.8


class SimpleControlGUI:
    """Simple GUI with Manual + Waypoint modes only."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Robot Control (Manual + Waypoint)")
        self.root.configure(bg='#2b2b2b')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.car = None
        self.loop = None
        self.running = True
        self.current_mode = "manual"
        
        self.manual_throttle = 0.0
        self.manual_steering = 0.0
        self.manual_omega = 0.0
        
        self.max_x = 180.0
        self.max_y = 120.0
        
        self.build_ui()
        
        # Keyboard shortcuts
        self.root.bind('1', lambda e: self.switch_mode('manual'))
        self.root.bind('2', lambda e: self.switch_mode('waypoint'))
        self.root.bind('<Tab>', lambda e: self.toggle_mode())
        
        self.start_async_loop()
    
    def build_ui(self):
        # Top frame
        top_frame = tk.Frame(self.root, bg='#2b2b2b')
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.ble_status_label = tk.Label(
            top_frame, text="BLE: Disconnected", font=("Arial", 12, "bold"),
            fg="#ff4444", bg='#2b2b2b'
        )
        self.ble_status_label.pack(side=tk.LEFT, padx=10)
        
        tk.Label(top_frame, text="Mode (1/2/Tab):", font=("Arial", 12),
                fg="white", bg='#2b2b2b').pack(side=tk.LEFT, padx=(20, 5))
        
        self.mode_var = tk.StringVar(value="manual")
        
        tk.Radiobutton(top_frame, text="Manual", variable=self.mode_var, value="manual",
                      command=self.on_mode_change, font=("Arial", 10), fg="white",
                      bg='#2b2b2b', selectcolor='#404040', activebackground='#2b2b2b',
                      state=tk.NORMAL if MANUAL_CONTROL_AVAILABLE else tk.DISABLED
                      ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(top_frame, text="Waypoint", variable=self.mode_var, value="waypoint",
                      command=self.on_mode_change, font=("Arial", 10), fg="white",
                      bg='#2b2b2b', selectcolor='#404040', activebackground='#2b2b2b'
                      ).pack(side=tk.LEFT, padx=5)
        
        # Content frame
        self.content_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_manual_panel()
        self.create_waypoint_panel()
        self.on_mode_change()
    
    def create_manual_panel(self):
        self.manual_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        tk.Label(self.manual_panel, text="Manual Control Mode",
                font=("Arial", 16, "bold"), fg="white", bg='#2b2b2b').pack(pady=10)
        
        instructions = [
            "WASD - Throttle/Steering | QE - Omega (Rotate) | X - LED | ESC - Stop",
            "1 - Manual Mode | 2 - Waypoint Mode | Tab - Toggle Modes"
        ]
        
        tk.Label(self.manual_panel, text="\n".join(instructions), font=("Arial", 11),
                fg="#aaaaaa", bg='#2b2b2b', justify=tk.LEFT).pack(pady=20)
        
        status_frame = tk.Frame(self.manual_panel, bg='#3b3b3b', relief=tk.SUNKEN, bd=2)
        status_frame.pack(pady=20, padx=50, fill=tk.X)
        
        self.throttle_label = tk.Label(status_frame, text="Throttle: 0.00",
                                      font=("Arial", 12), fg="#00ff00", bg='#3b3b3b')
        self.throttle_label.pack(pady=5)
        
        self.steering_label = tk.Label(status_frame, text="Steering: 0.00",
                                      font=("Arial", 12), fg="#00ff00", bg='#3b3b3b')
        self.steering_label.pack(pady=5)
        
        self.omega_label = tk.Label(status_frame, text="Omega: 0.00",
                                    font=("Arial", 12), fg="#00ff00", bg='#3b3b3b')
        self.omega_label.pack(pady=5)
    
    def create_waypoint_panel(self):
        self.waypoint_panel = tk.Frame(self.content_frame, bg='#2b2b2b')
        
        tk.Label(self.waypoint_panel, text=f"Waypoint Mode - {self.max_x}cm × {self.max_y}cm",
                font=("Arial", 16, "bold"), fg="white", bg='#2b2b2b').pack(pady=10)
        
        self.waypoint_status_label = tk.Label(self.waypoint_panel,
                text="Click on workspace to send waypoint | Tab/1/2 - Switch modes",
                font=("Arial", 10), fg="#aaaaaa", bg='#2b2b2b')
        self.waypoint_status_label.pack(pady=5)
        
        canvas_frame = tk.Frame(self.waypoint_panel, bg='white', relief=tk.SUNKEN, borderwidth=2)
        canvas_frame.pack(padx=20, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, width=800, height=600, bg="white", highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_waypoint_click)
        
        self.draw_grid()
    
    def draw_grid(self):
        w, h = 800, 600
        self.canvas.create_rectangle(2, 2, w-2, h-2, outline="black", width=2)
        self.canvas.create_line(0, h/2, w, h/2, fill="lightgray", dash=(5, 5))
        self.canvas.create_line(w/2, 0, w/2, h, fill="lightgray", dash=(5, 5))
        
        self.canvas.create_text(10, h-10, text="(0, 0)", anchor='sw', fill='gray')
        self.canvas.create_text(w-10, h-10, text=f"({self.max_x:.0f}, 0)", anchor='se', fill='gray')
        self.canvas.create_text(10, 10, text=f"(0, {self.max_y:.0f})", anchor='nw', fill='gray')
        self.canvas.create_text(w-10, 10, text=f"({self.max_x:.0f}, {self.max_y:.0f})", anchor='ne', fill='gray')
    
    def switch_mode(self, mode):
        self.mode_var.set(mode)
        self.on_mode_change()
        print(f"\n[Mode: {mode.upper()}]")
    
    def toggle_mode(self):
        self.switch_mode("waypoint" if self.current_mode == "manual" else "manual")
    
    def on_mode_change(self):
        self.manual_panel.pack_forget()
        self.waypoint_panel.pack_forget()
        
        self.current_mode = self.mode_var.get()
        
        if self.current_mode == "manual":
            self.manual_panel.pack(fill=tk.BOTH, expand=True)
        else:
            self.waypoint_panel.pack(fill=tk.BOTH, expand=True)
    
    def on_waypoint_click(self, event):
        if not self.car:
            return
        
        px, py = event.x, event.y
        x = round(px * self.max_x / 800, 1)
        y = round((600 - py) * self.max_y / 600, 1)
        
        print(f"→ Waypoint: ({x}, {y}) cm")
        
        self.waypoint_status_label.config(text=f"Waypoint: ({x}, {y}) cm | Sending...")
        
        self.canvas.delete("marker")
        r = 8
        self.canvas.create_oval(px-r, py-r, px+r, py+r, fill="#ff4444", outline="#cc0000", width=2, tags="marker")
        self.canvas.create_text(px, py-r-15, text=f"({x}, {y})", fill="#cc0000", font=("Arial", 10, "bold"), tags="marker")
        
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.send_waypoint(x, y), self.loop)
    
    async def send_waypoint(self, x, y):
        try:
            if self.car:
                await self.car.set_waypoint(x, y)
                self.root.after(0, lambda: self.waypoint_status_label.config(text=f"Waypoint: ({x}, {y}) cm | ✓ Sent"))
        except Exception as e:
            print(f"Error: {e}")
    
    def start_async_loop(self):
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.async_main())
        
        threading.Thread(target=run_loop, daemon=True).start()
    
    async def async_main(self):
        await self.connect_ble()
        await self.manual_control_loop()
    
    async def connect_ble(self):
        self.root.after(0, lambda: self.ble_status_label.config(text="BLE: Connecting...", fg="#ffaa00"))
        
        try:
            self.car = CarBLEClient()
            await self.car.connect()
            
            if self.car.client:
                self.root.after(0, lambda: self.ble_status_label.config(text="BLE: Connected ✓", fg="#00ff00"))
                print("✓ BLE Connected")
            else:
                self.root.after(0, lambda: self.ble_status_label.config(text="BLE: Simulation 🔧", fg="#ffaa00"))
                print("⚠ Simulation Mode")
        except Exception as e:
            print(f"BLE Error: {e}")
            self.root.after(0, lambda: self.ble_status_label.config(text="BLE: Error ✗", fg="#ff4444"))
    
    async def manual_control_loop(self):
        if not MANUAL_CONTROL_AVAILABLE:
            return
        
        last_t, last_s, last_o = 0.0, 0.0, 0.0
        
        while self.running:
            try:
                if self.current_mode == "manual" and self.car:
                    T_SCALE, S_SCALE, O_SCALE = load_scales()
                    
                    t = inp.get_bipolar_ctrl('w', 's', 'LY') * T_SCALE
                    s = inp.get_bipolar_ctrl('d', 'a', 'RX') * S_SCALE
                    o = inp.get_bipolar_ctrl('e', 'q', 'DPAD_RIGHT', 'DPAD_LEFT') * O_SCALE
                    
                    self.manual_throttle, self.manual_steering, self.manual_omega = t, s, o
                    
                    if t != last_t:
                        await self.car.set_throttle(t)
                        last_t = t
                    if s != last_s:
                        await self.car.set_steering(s)
                        last_s = s
                    if o != last_o:
                        await self.car.set_omega(o)
                        last_o = o
                    
                    self.root.after(0, self.update_manual_display)
                    
                    led = 0 if (inp.is_pressed('x') or inp.is_pressed('A')) else 1
                    await self.car.set_led(led)
                    
                    if inp.is_pressed('Key.esc'):
                        print("\n[STOP]")
                        await self.car.set_throttle(0.0)
                        await self.car.set_steering(0.0)
                        await self.car.set_omega(0.0)
                        last_t = last_s = last_o = 0.0
                
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(0.1)
    
    def update_manual_display(self):
        self.throttle_label.config(text=f"Throttle: {self.manual_throttle:+.2f}")
        self.steering_label.config(text=f"Steering: {self.manual_steering:+.2f}")
        self.omega_label.config(text=f"Omega: {self.manual_omega:+.2f}")
    
    def on_close(self):
        self.running = False
        if self.car and self.loop:
            async def stop():
                await self.car.set_throttle(0.0)
                await self.car.set_steering(0.0)
                await self.car.set_omega(0.0)
                if self.car.client:
                    await self.car.disconnect()
            asyncio.run_coroutine_threadsafe(stop(), self.loop)
        self.root.quit()
        self.root.destroy()


def main():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    root = tk.Tk()
    app = SimpleControlGUI(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
