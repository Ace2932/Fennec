#!/usr/bin/env python3
"""Reproducible mesh containment, shared by every CAD gate (#195 propagation).

WHY
---
trimesh's `contains()` casts a ray forward and backward and takes the parity.
When the two directions disagree and neither is free space it recurses:

    # try to run again with a new random vector
    new_direction = util.unitize(np.random.random(3) - 0.5)

That draw comes from numpy's GLOBAL RNG, so `contains()` can return DIFFERENT
ANSWERS ON IDENTICAL INPUT, and can return a different answer depending on how
much RNG anything EARLIER in the process happened to consume. Every gate verdict
in this repo is a threshold on a count derived from `contains()`, so a flipped
surface-adjacent point can move a verdict.

MEASURED, 2026-07-31 (trimesh 4.12.2, embreex 4.4.0 installed and active)
------------------------------------------------------------------------
READ THIS BEFORE CONCLUDING IT DOES NOT REPRODUCE. The instability is both
MESH-SPECIFIC and PER-PROCESS. Whether the ambiguous points flip depends on the
global RNG state the process happens to start in, so a single process usually
looks perfectly stable -- 12 identical calls in a row typically agree, and 8
consecutive whole-gate runs were byte-identical. The variation lives BETWEEN
processes, which is exactly where a CI job lives.

Rate over 20 FRESH PROCESSES, 12 calls x 3000 on-surface points each:

    leg_v6/coax_R.stl      6/20 processes flicker (1 to 44 points of 3000)
    leg_v6/shoulder.stl    1/20 processes flicker (1 point)
    femur_R, tibia_R, knee_arm, shoulder_plate(_L), riser_bay,
    battery_pocket, head, neck_bracket, jetson_case_mount,
    jetson_clamp_bar, trunk, constructed boxes  -- no flicker seen

    with install():        0/20 processes flicker, and all 20 processes
                           produce a SINGLE identical result

Two earlier single-shot readings (coax_R "5/3000", shoulder "1/3000") were
individually true but not reproducible on demand -- they were samples of the
6/20 and 1/20 rates above. Do not treat one clean run as disproof.

So "is this gate affected?" is a question about which meshes it casts INTO, and
it cannot be answered by reading the code. chassis/check_fit.py casts into
`shoulder.stl` (SH_STL) from `floor_thickness_check()`, `mating_fastener_checks()`
and the shoulder-vs-trunk sweep -- i.e. it IS affected. `floor_thickness_check()`
is the sharpest case: it derives a floor from the FIRST CONTIGUOUS SOLID RUN of
a 0.02mm scan, so a single flipped point lengthens the run by exactly one 0.02
step. A trunk-flange floor was observed once at 1.50mm where 70+ other runs gave
1.48mm -- one step -- and that bore passes on `floor >= 1.45`, a margin of 1.5
steps. One-in-twenty, against a 1.5-step margin, on the gate that authorises
printing the part.

WHY A PATCH AND NOT PER-CALL EDITS
----------------------------------
chassis/check_fit.py has ~62 `.contains(` call sites, several inside nested
helpers. Routing them one at a time is exactly the edit where one gets missed --
and a gate that is seeded at 61 of 62 sites is not reproducible, it is
reproducible-looking. Patching the method covers every site including any added
later, and `install()` is called explicitly (never as an import side effect) so
it stays greppable.

Seeding per call, with the global RNG state saved and restored, also buys
ORDER-INDEPENDENCE: a check's result no longer depends on how many draws
preceded it, so editing an unrelated earlier check cannot silently perturb a
later verdict. That is not hypothetical -- it is what made an unrelated flange
value appear to move when only the crouch-sweep windows had changed (#47 redux).
"""

import numpy as np
import trimesh

#: Any fixed value works; what matters is that it is fixed.
CONTAINS_SEED = 0

_ORIGINAL_CONTAINS = trimesh.Trimesh.contains
_installed = False


def contains_seeded(mesh, points):
    """`mesh.contains(points)` with the parity-retry draw pinned.

    The global RNG state is saved and restored, so seeding here cannot reach
    into anything else that draws from np.random (sampling, jitter, etc).
    """
    state = np.random.get_state()
    try:
        np.random.seed(CONTAINS_SEED)
        return _ORIGINAL_CONTAINS(mesh, points)
    finally:
        np.random.set_state(state)


def install(announce=True):
    """Make every Trimesh.contains() call in this process reproducible.

    Idempotent. Returns True if it patched, False if already installed.

    ASSERTS that the patch actually took, and says so on stdout. Without that
    this is an invariant nothing can observe: if a future trimesh turns
    `contains` into a property or descriptor, the assignment below would still
    "succeed" while every call site kept using the unseeded original, and the
    gate would go green having silently lost its reproducibility. A silent
    installer is indistinguishable from an absent one -- the same failure this
    module exists to remove, so it is checked rather than assumed.
    """
    global _installed
    if _installed:
        return False
    if not callable(getattr(trimesh.Trimesh, 'contains', None)):
        raise RuntimeError(
            'trimesh.Trimesh.contains is not a plain callable on this version '
            f'({trimesh.__version__}) -- the #195 seeding patch would not take. '
            'Re-derive the patch point before trusting any gate verdict.')
    trimesh.Trimesh.contains = contains_seeded
    if trimesh.Trimesh.contains is not contains_seeded:
        raise RuntimeError('#195 seeding patch did not take -- refusing to run '
                           'a gate whose verdicts would be non-reproducible.')
    _installed = True
    if announce:
        print(f'   contains() seeding ACTIVE (#195, seed={CONTAINS_SEED}, '
              f'trimesh {trimesh.__version__})')
    return True


def is_installed():
    return _installed and trimesh.Trimesh.contains is contains_seeded
