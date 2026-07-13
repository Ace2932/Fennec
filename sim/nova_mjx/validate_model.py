"""CPU sanity-check for nova.xml — compiles, has the right DOF, and STANDS from
the keyframe under gravity. No GPU/JAX needed (plain mujoco). Run after editing
build_mjcf.py / nova.xml.

  python validate_model.py
"""
import mujoco


def main():
    m = mujoco.MjModel.from_xml_path("nova.xml")
    d = mujoco.MjData(m)
    assert m.nu == 12, f"expected 12 actuators, got {m.nu}"
    assert m.nq == 19 and m.nv == 18, f"unexpected DOF nq={m.nq} nv={m.nv}"
    print(f"compiled OK: nq={m.nq} nv={m.nv} nu={m.nu} nbody={m.nbody}")

    mujoco.mj_resetDataKeyframe(m, d, 0)
    for _ in range(500):          # 2 s at 0.004
        mujoco.mj_step(m, d)
    base_z = float(d.qpos[2])
    upright = abs(float(d.qpos[3]) - 1.0) < 0.3
    print(f"after 2 s settle: base_z={base_z:.3f} m  contacts={d.ncon}  "
          f"quat={d.qpos[3:7].round(2)}")
    ok = base_z > 0.08 and upright and d.ncon >= 4
    print("STANDS ✓" if ok else "FELL / unstable ✗ — retune the keyframe")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
