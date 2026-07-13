"""LiDAR ear self-filter ROS 2 node — republishes the L2 cloud with the
robot's own ear-mast returns removed.

    ros2 run nova_ops lidar_selffilter_node

Sits between the L2 driver and SLAM: subscribes the raw PointCloud2, drops
points inside the fixed ear sectors (see mask.py), republishes the rest with
all fields (intensity/ring/time) preserved. Allowed-to-crash (nothing on the
gait critical path); SLAM simply keeps the last cloud if it dies.

Parameters:
  input_topic    (str,   /l2/points_raw)  — raw cloud in
  output_topic   (str,   /l2/points)      — filtered cloud out
  az_offset_deg  (double, 0.0)            — L2 mount-yaw correction. The Ø51
      4-hole base allows 4 orientations 90° apart; set this to the installed
      yaw or the ear sectors point at the wrong azimuth (see mask.py header).
  min_range      (double, 0.0)            — optional global near-field crop (m);
      0 disables (ear sectors alone do the work).
"""

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2

from .mask import EAR_SECTORS, keep_mask


class LidarSelfFilter(Node):
    def __init__(self):
        super().__init__("lidar_selffilter")
        self.declare_parameter("input_topic", "/l2/points_raw")
        self.declare_parameter("output_topic", "/l2/points")
        self.declare_parameter("az_offset_deg", 0.0)
        self.declare_parameter("min_range", 0.0)

        in_topic = self.get_parameter("input_topic").value
        out_topic = self.get_parameter("output_topic").value
        self._az_offset = float(self.get_parameter("az_offset_deg").value)
        self._min_range = float(self.get_parameter("min_range").value)

        self._pub = self.create_publisher(PointCloud2, out_topic, 10)
        self._sub = self.create_subscription(PointCloud2, in_topic, self._on_cloud, 10)

        self.get_logger().info(
            f"lidar_selffilter: {in_topic} -> {out_topic}; "
            f"{len(EAR_SECTORS)} ear sectors, az_offset={self._az_offset}deg, "
            f"min_range={self._min_range}m"
        )
        if self._az_offset == 0.0:
            self.get_logger().warn(
                "az_offset_deg=0 assumes the L2 zero-azimuth points ROBOT-FORWARD. "
                "Verify the 4-way mount orientation on the bench (see mask.py)."
            )

    def _on_cloud(self, msg: PointCloud2):
        # structured ndarray with every field (x,y,z,intensity,ring,...)
        arr = point_cloud2.read_points(msg, skip_nans=False)
        if arr.shape[0] == 0:
            self._pub.publish(msg)
            return
        xyz = np.column_stack([arr["x"], arr["y"], arr["z"]]).astype(float)
        keep = keep_mask(xyz, EAR_SECTORS, self._min_range, self._az_offset)
        out = point_cloud2.create_cloud(msg.header, msg.fields, arr[keep])
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = LidarSelfFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
