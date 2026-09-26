"""The Teensy's micro-ROS entity pools are big enough for what main.cpp creates.

WHY THIS EXISTS. rmw_microxrcedds allocates publishers/subscriptions/nodes from
STATIC pools sized at library build time. Upstream micro_ros_platformio's
teensy41 default (metas/colcon.meta at the pinned cfee17f) is
MAX_PUBLISHERS=10 / MAX_SUBSCRIPTIONS=5 / MAX_NODES=1, while main.cpp creates
26 publishers: the 11th rclc_publisher_init_default returns an error at boot and
RCCHECK halts the board. Nothing on the Mac or in CI runs setup(), so the only
place this showed was on the robot. firmware/teensy/firmware/nova_microros.meta
raises the caps; this test fails the day main.cpp outgrows them again, or the
day platformio.ini stops pointing at the meta.

WHAT THIS DOES NOT CHECK. That the meta reached the compiled library -- the
microros-build CI job greps the built config.h for that.
"""

import configparser
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[4]
FW = REPO / "firmware/teensy/firmware"
MAIN_CPP = FW / "src/main.cpp"


def _caps() -> dict[str, int]:
    ini = configparser.ConfigParser(interpolation=None)
    ini.read(FW / "platformio.ini")
    meta = FW / ini["env:teensy41"]["board_microros_user_meta"]
    args = json.loads(meta.read_text())["names"]["rmw_microxrcedds"]["cmake-args"]
    return {
        m.group(1): int(m.group(2))
        for a in args
        if (m := re.fullmatch(r"-DRMW_UXRCE_MAX_(\w+)=(\d+)", a))
    }


def _count(fn: str) -> int:
    return len(re.findall(rf"\b{fn}\s*\(", MAIN_CPP.read_text()))


def test_main_cpp_entities_fit_rmw_pools():
    caps = _caps()
    used = {
        "PUBLISHERS": _count(r"rclc_publisher_init_(?:default|best_effort)"),
        "SUBSCRIPTIONS": _count(r"rclc_subscription_init_(?:default|best_effort)"),
        "NODES": _count(r"rclc_node_init_default"),
        "SERVICES": _count(r"rclc_service_init_(?:default|best_effort)"),
        "CLIENTS": _count(r"rclc_client_init_(?:default|best_effort)"),
    }
    assert used["PUBLISHERS"] > 0, "regex found no publishers -- the check is blind"
    over = {k: (n, caps.get(k)) for k, n in used.items() if n > caps.get(k, 0) and n}
    assert not over, f"main.cpp creates more entities than the rmw pool holds: {over}"
