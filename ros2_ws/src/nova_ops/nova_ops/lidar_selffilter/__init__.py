"""LiDAR self-filter: static angular+range mask that drops returns landing on
the robot's own rigid ear masts, so they never enter the SLAM cloud.

Pure logic lives in `mask.py` (numpy-only, unit-tested without a graph); the ROS
2 wrapper is `node.py`.
"""

from .mask import EAR_SECTORS, Sector, keep_mask

__all__ = ["EAR_SECTORS", "Sector", "keep_mask"]
