"""Height-map sampler correctness — the tier-2 primitive that fails SILENTLY if
its geometry is wrong (feeds the policy a mis-oriented / mis-scaled terrain view).
Injects known terrain and checks orientation, relative-height, and yaw-alignment.

  JAX_PLATFORMS=cpu python test_heightmap.py
"""
import jax
import jax.numpy as jp
import numpy as np

from env import NovaJoystick, HM_N


def _env_with_terrain(data2d):
    e = NovaJoystick(heightmap=True)
    e.sys = e.sys.tree_replace({"hfield_data": jp.asarray(data2d.reshape(-1))})
    return e


def _pose(e, yaw=0.0):
    """A pipeline_state at the origin with the given yaw."""
    st = jax.jit(e.reset)(jax.random.PRNGKey(0))
    ps = st.pipeline_state
    w, z = np.cos(yaw / 2), np.sin(yaw / 2)          # quat about +Z
    q = ps.q.at[0].set(0.).at[1].set(0.).at[3].set(w).at[4].set(0.).at[5].set(0.).at[6].set(z)
    return ps.replace(q=q).tree_replace(
        {"x.pos": ps.x.pos.at[0, 0].set(0.).at[0, 1].set(0.)})


def _raised_plus_x(e, h=0.05):
    ncol = e._hf_ncol
    ztop = float(e._hf_size[2])
    data = np.zeros((e._hf_nrow, ncol), np.float32)
    data[:, ncol // 2:] = h / ztop                  # world +x half raised h
    return data


def test_orientation_and_relative_height():
    e = NovaJoystick(heightmap=True)
    e2 = _env_with_terrain(_raised_plus_x(e, 0.05))
    hm = np.asarray(e2._sample_heightmap(_pose(e2, 0.0))).reshape(HM_N, HM_N)
    bz = 0.17
    # yaw 0: gx (axis 0) is world +x forward -> the raised half is the high-index rows
    assert hm[-1].mean() > hm[0].mean() + 0.03, "step not on the +x/forward side"
    assert abs(hm[-1].mean() - (-bz + 0.05)) < 0.012, "raised cell height wrong"
    assert abs(hm[0].mean() - (-bz)) < 0.012, "flat cell should read -base_z"


def test_flat_reads_negative_base():
    e = NovaJoystick(heightmap=True)              # nominal flat terrain
    hm = np.asarray(e._sample_heightmap(_pose(e, 0.0)))
    assert np.allclose(hm, -0.17, atol=0.01), "flat ground should read -base_z everywhere"


def test_teacher_obs_is_227():
    # teacher obs = 105 (proprio+cmd+act) + 121 (11x11 heightmap) + 1 (commanded
    # footswing c, last dim) = 227. lift-v5 raised this from 226 by appending c.
    e = NovaJoystick(heightmap=True)
    s = jax.jit(e.reset)(jax.random.PRNGKey(0))
    assert s.obs.shape[-1] == 227, s.obs.shape


def test_yaw_rotates_the_view():
    # rotate the robot +90deg: world +x (the raised half) is now on the robot's
    # RIGHT (gy<0), so the forward axis should no longer carry the step.
    e = NovaJoystick(heightmap=True)
    e2 = _env_with_terrain(_raised_plus_x(e, 0.05))
    hm = np.asarray(e2._sample_heightmap(_pose(e2, np.pi / 2))).reshape(HM_N, HM_N)
    fwd_diff = hm[-1].mean() - hm[0].mean()          # forward axis
    lat_diff = hm[:, -1].mean() - hm[:, 0].mean()    # lateral axis
    assert abs(fwd_diff) < abs(lat_diff), "at yaw90 the +x step should show on the lateral axis"


if __name__ == "__main__":
    for fn in [test_orientation_and_relative_height, test_flat_reads_negative_base,
               test_teacher_obs_is_227, test_yaw_rotates_the_view]:
        fn(); print("OK", fn.__name__)
    print("ALL HEIGHT-MAP SAMPLER CHECKS PASSED")
