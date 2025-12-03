#!/usr/bin/env python3
"""
ROS2-Style Launch System for TE2004B Robot
===========================================

Launches multiple processes with proper lifecycle management,
similar to ROS2 launch files but simpler.

Features:
- Launch multiple processes simultaneously
- Graceful shutdown of all processes
- Auto-restart on failure (optional)
- Environment variable management
- Output logging
"""

import subprocess
import signal
import sys
import time
import os
from pathlib import Path
from typing import List, Dict, Optional
import argparse


class ProcessNode:
    """Represents a single process/node to launch."""
    
    def __init__(self, name: str, cmd: List[str], cwd: Optional[str] = None, 
                 env: Optional[Dict[str, str]] = None, restart: bool = False):
        """
        Initialize a process node.
        
        Args:
            name: Human-readable name for the process
            cmd: Command and arguments as list
            cwd: Working directory (None = current dir)
            env: Environment variables to add/override
            restart: Whether to restart on failure
        """
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.env = env
        self.restart = restart
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.max_restarts = 3
    
    def start(self):
        """Start the process."""
        # Prepare environment
        process_env = os.environ.copy()
        if self.env:
            process_env.update(self.env)
        
        # Start process
        print(f" Starting {self.name}...")
        self.process = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        print(f"   PID: {self.process.pid}")
    
    def stop(self):
        """Stop the process gracefully."""
        if self.process and self.process.poll() is None:
            print(f" Stopping {self.name}...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   Force killing {self.name}...")
                self.process.kill()
    
    def is_alive(self) -> bool:
        """Check if process is still running."""
        return self.process is not None and self.process.poll() is None
    
    def check_and_restart(self) -> bool:
        """Check if process died and restart if configured. Returns True if restarted."""
        if not self.is_alive() and self.restart and self.restart_count < self.max_restarts:
            print(f" {self.name} died. Restarting... ({self.restart_count + 1}/{self.max_restarts})")
            self.restart_count += 1
            self.start()
            return True
        return False


class LaunchSystem:
    """Main launch system to manage multiple processes."""
    
    def __init__(self):
        self.nodes: List[ProcessNode] = []
        self.running = False
    
    def add_node(self, node: ProcessNode):
        """Add a node to the launch system."""
        self.nodes.append(node)
    
    def start_all(self):
        """Start all nodes."""
        print("\n" + "="*60)
        print("  TE2004B Robot Launch System")
        print("="*60 + "\n")
        
        self.running = True
        
        for node in self.nodes:
            node.start()
            time.sleep(0.5)  # Small delay between starts
        
        print(f"\n✓ All {len(self.nodes)} nodes started successfully")
        print("\nPress Ctrl+C to stop all nodes\n")
    
    def stop_all(self):
        """Stop all nodes."""
        print("\n" + "="*60)
        print("  Shutting down...")
        print("="*60 + "\n")
        
        self.running = False
        
        for node in reversed(self.nodes):  # Stop in reverse order
            node.stop()
        
        print("\n All nodes stopped\n")
    
    def monitor_loop(self):
        """Monitor all nodes and handle restarts."""
        try:
            while self.running:
                time.sleep(1)
                
                # Check all nodes
                for node in self.nodes:
                    if not node.is_alive() and not node.restart:
                        print(f" {node.name} stopped unexpectedly")
                    else:
                        node.check_and_restart()
                
                # Check if all non-restart nodes are dead
                alive_count = sum(1 for node in self.nodes if node.is_alive())
                if alive_count == 0:
                    print("\n All nodes stopped. Exiting...")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n Interrupt received")
        finally:
            self.stop_all()


# Pre-defined launch configurations
def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def launch_dashboard_only():
    """Launch only the dashboard."""
    launcher = LaunchSystem()
    
    project_root = get_project_root()
    
    launcher.add_node(ProcessNode(
        name="Dashboard",
        cmd=["streamlit", "run", "dashboard.py"],
        cwd=str(project_root / "cam_server_page")
    ))
    
    launcher.start_all()
    launcher.monitor_loop()


def launch_navigation_with_dashboard():
    """Launch unified navigation only (no dashboard)."""
    launcher = LaunchSystem()
    
    project_root = get_project_root()
    
    # Unified Navigation without dashboard streaming
    launcher.add_node(ProcessNode(
        name="Unified Navigation",
        cmd=["python3", "navigation/unified_navigation.py"],
        cwd=str(project_root / "on_board_cam")
    ))
    
    launcher.start_all()
    launcher.monitor_loop()


def launch_waypoint_with_dashboard():
    """Launch waypoint GUI only (no dashboard)."""
    launcher = LaunchSystem()
    
    project_root = get_project_root()
    
    # Waypoint GUI without dashboard streaming
    launcher.add_node(ProcessNode(
        name="Waypoint GUI",
        cmd=["python3", "waypoints_gui.py"],
        cwd=str(project_root / "waypoint_marker")
    ))
    
    launcher.start_all()
    launcher.monitor_loop()


def launch_full_system():
    """Launch both: navigation + waypoint."""
    launcher = LaunchSystem()
    
    project_root = get_project_root()
    
    # Unified Navigation
    launcher.add_node(ProcessNode(
        name="Unified Navigation",
        cmd=["python3", "navigation/unified_navigation.py"],
        cwd=str(project_root / "on_board_cam")
    ))
    
    # Waypoint GUI
    launcher.add_node(ProcessNode(
        name="Waypoint GUI",
        cmd=["python3", "waypoints_gui.py"],
        cwd=str(project_root / "waypoint_marker")
    ))
    
    launcher.start_all()
    launcher.monitor_loop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Launch system for TE2004B Robot (ROS2-style)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dashboard              # Dashboard only
  %(prog)s --navigation             # Unified Navigation only
  %(prog)s --waypoint               # Waypoint GUI only
  %(prog)s --full                   # Navigation + Waypoint

Pre-configured launch options are provided for common use cases.
For custom launches, modify this script or create a new launch file.
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dashboard', action='store_true',
                      help='Launch dashboard only')
    group.add_argument('--navigation', action='store_true',
                      help='Launch unified navigation')
    group.add_argument('--waypoint', action='store_true',
                      help='Launch waypoint GUI')
    group.add_argument('--full', action='store_true',
                      help='Launch full system (navigation + waypoint)')
    
    args = parser.parse_args()
    
    if args.dashboard:
        launch_dashboard_only()
    elif args.navigation:
        launch_navigation_with_dashboard()
    elif args.waypoint:
        launch_waypoint_with_dashboard()
    elif args.full:
        launch_full_system()


if __name__ == "__main__":
    main()
