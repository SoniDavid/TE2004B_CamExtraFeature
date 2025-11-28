"""
Navigation follower module for TE2004B Robot Tractor
Contains different navigation strategies:
- ArUco marker detection and distance estimation
- Color-based object tracking 
- Unified navigation with switchable targets
"""

from .base_navigation import BaseNavigationController
from .target_detectors import TargetDetector, ArucoTargetDetector, ColorTargetDetector
from .unified_navigation import UnifiedNavigationController

__all__ = [
    'BaseNavigationController',
    'TargetDetector',
    'ArucoTargetDetector', 
    'ColorTargetDetector',
    'UnifiedNavigationController'
]
