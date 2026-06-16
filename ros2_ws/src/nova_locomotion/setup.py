from setuptools import find_packages, setup

package_name = "nova_locomotion"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Aiden Fox",
    maintainer_email="aidenfox2013@gmail.com",
    description="NovaSM3 locomotion: analytic 3-DOF leg IK/FK + scripted trot "
    "gait (Phase-2 baseline). Pure-math, hardware-independent.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            # TODO(phase2): gait_node — subscribe gait params / cmd_vel, run
            # trot.foot_target -> leg_ik.inverse_kinematics -> /joint_commands
            # via config/joint_id_map.yaml. Pure logic below is already tested.
        ],
    },
)
