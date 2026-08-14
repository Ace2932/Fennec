# Colab — teacher → blind student distillation (#304)

`fennec_train.ipynb` produces a **teacher**. This produces the thing that actually ships.

Every checkpoint on Drive is a privileged teacher — obs 226/234, including a *perfect* 11×11
simulated heightmap the real D456/L2 cannot supply. **No blind 105-d student exists yet.** Until
one does, `policy_node` has nothing to run: the bridge, the safety profile and the IMU driver are
all in place and pointed at an artifact that has never been produced.

`../distill.py` is the harness. It was verified end to end on CPU 2026-08-09 — collect → DAgger →
fit → export → eval all execute and the artifact loads — so the pipeline is not what you are
testing on the GPU. **You are testing whether a blind student can reproduce the teacher.**

## Setup

**Use [`fennec_distill.ipynb`](fennec_distill.ipynb)** — it implements everything below, with every
knob in one config cell (`SCALE` is normally the only number you touch; it drives BC episodes,
DAgger episodes and epochs together).

Setup is otherwise identical to `fennec_train.ipynb` — same clone, same pinned deps
(`../requirements.txt`, `brax 0.14.2` + `jax 0.6.0`, CUDA build). If a sanity cell reports
`backend cpu`, `Runtime → Restart session` and re-run from the config cell; the clone persists.

Three operational things this doc used to leave implicit, all of which bite on Colab specifically:

- **The teacher is NOT in the clone.** `sim/nova_mjx/artifacts/policies/*` is gitignored
  (`.gitignore:154`), so a fresh clone has no checkpoints and the run dies immediately. Copy the
  `.pkl` from Drive first — it is ~1.4 MB. The notebook does this and asserts it landed.
- **There is no resume and no intermediate checkpoint.** `distill.py`'s only write is the
  `pickle.dump` at export, so a Colab dropout loses the entire run. Point `--out` at a Drive path,
  and calibrate the wall-clock at small scale before committing hours to the full one.
- **`--eval-only` makes the second command cheap.** It reruns the paired eval against an
  already-exported student, so evaluating both `vx 0.35` and `vx 0.50` costs one eval, not a second
  distillation.

The teacher checkpoint must be on the machine. `nova_policy_hm234.pkl` is the one with a measured
flat baseline (below) — use it unless you have a reason not to, and **record which you used**,
because "the teacher" has meant four different files in this repo's history.

## Run

```
python distill.py \
    --teacher artifacts/policies/nova_policy_hm234.pkl \
    --out     artifacts/policies/nova_student_blind \
    --label   distill-v1 \
    --bc-episodes N --bc-steps 150 \
    --dagger-episodes M --dagger-steps 150 \
    --epochs E
```

**Scale is not decided here, deliberately.** The module docstring says the production run is
"10–100× the samples/epochs" of the defaults, and the defaults (`12/150` BC, `6/150` DAgger,
60 epochs) are a *CPU smoke*. Anyone who writes an exact number into this file without having run
it is guessing, and this project has paid for that before. Start at 10×, read the DAgger MSE
trend, and scale from evidence.

What you get: `nova_student_blind.pkl` + `.npz` (the numpy artifact `policy_runner` loads) +
`.meta.json` carrying the git SHA and label.

## Read the output in this order

1. **`numpy vs Brax max|err|`** — printed at export. On the CPU verification it was `5.25e-06`.
   This is the export self-check; if it is large, the `.npz` the robot would run is not the
   network that was trained, and nothing downstream matters.
2. **Fall rate and speed TOGETHER, never separately.** The eval prints its own warning and it is
   the right one: *a low fall rate at a speed well below command is a SLOW, conservative gait, not
   a better one.* A student that learns to creep scores beautifully on falls.
3. **`return` is not comparable** teacher-vs-student and the tool says so — the teacher's reward
   carries swingref/gait/climb/PBRS terms the blind reward does not have. Compare fall-rate,
   distance, speed.

## Acceptance bar

The bar is **the teacher's own measured numbers on the same paired eval**, because distillation's
job is to reproduce the teacher blind — not to beat it. Measured baseline for
`nova_policy_hm234` on FLAT, 8 paired episodes × 400 steps, nominal dynamics:

| command | fell | speed | % of cmd | distance |
|---|---|---|---|---|
| **vx = +0.35** | **0.0 %** | +0.346 | 99 % | +2.215 m |

A student that falls where the teacher does not, or tracks materially below 99 % of command, has
lost information in the distillation.

### ⚠ ALWAYS QUOTE THE COMMAND WITH THE NUMBER

`distill.py` defaults to `--vx 0.5`, "matches the #288 measured condition". **The same teacher
behaves completely differently at the two commands** — it never falls at vx 0.35 and falls ~50 %
of the time at vx 0.50. So a student evaluated at 0.5 is being compared against a teacher that is
itself falling half the time, and "the student falls 50 %" would be a meaningless sentence.

This is not hypothetical: a "teacher robustness is the blocker" conclusion was already reached in
this project on a fall rate quoted **without its command**, and had to be retracted. Run **both**
0.35 and 0.50, and never write a fall rate down without the vx beside it.

### Kill-switch

If DAgger MSE has plateaued and the student still falls where the teacher does not at vx 0.35,
more epochs will not fix it — the blind observation is missing something the teacher was using.
Stop and look at *what*, rather than spending GPU-hours. The heightmap is the obvious suspect and
the whole reason a student is needed.

## What this does NOT settle

- **#309** — the v7 swing-reference acceptance gate fails at the shipped `W_SWINGREF=100`, and the
  remedy its own design doc prescribes (raise the weight) was measured not to move it.
- **#311** — `cmd_c` is sampled identically for trot and crawl, and rear legs sustain 1.29 cm of
  clearance against a `FOOTSWING_MIN` of 1.5 cm, so *every* commanded value is above what they
  reach. Plausibly one defect with #309.

Distilling a teacher does not repair either — the student inherits whatever the teacher learned
under them. They are worth resolving before a *retrain*, not before this run.
