from setuptools import find_packages, setup

package_name = "nova_locomotion"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/launch",
            ["launch/gait.launch.py", "launch/policy.launch.py"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Aiden Fox",
    maintainer_email="aidenfox2013@gmail.com",
    description="NovaSM3 locomotion: analytic 3-DOF leg IK/FK + scripted trot "
    "gait (Phase-2 baseline), plus the sim-trained RL policy's ROS 2 bridge.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            # thin glue; all logic in controller.py (pure, tested rclpy-free)
            "gait_node = nova_locomotion.node:main",
            # sim->real RL policy bridge (#289); pure logic in policy_node.py
            # itself (PolicyGate, ramp_alpha/ramp_blend), tested rclpy-free
            # via the stub pattern (see test_policy_node.py).
            "policy_node = nova_locomotion.policy_node:main",
        ],
    },
)
