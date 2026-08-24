# Heat-set inserts — the process half

`print-batch.md` §3b covers the **geometry** of every insert site: which bore, what floor
thickness, vented or blind, which face to press from. That is the half that was written
down. This is the other half — how to actually set them without ruining a part — and until
2026-08-24 it lived nowhere in this repo.

**Status: nothing is heat-set anywhere on this robot yet.** ~68 M3 sites, counted off the
CAD against a documented 16. Inserts are in hand.

---

## 1. There are TWO insert sizes and swapping them gives ZERO grip

| insert | bore it goes in | where |
|---|---|---|
| **4.6 mm OD** ruthex (M3 × 5.7) | **4.0** — `leg_v6_common.scad:153` `HEATSET_D` | everywhere except the HFE block |
| **4.0 mm OD** slim (M3 × 6.0, uxcell `B07R9SP532`) | **3.5** — `leg_v6_common.scad:198` `BLOCK_HEATSET_D` | **HFE block only** |

The slim one exists because a 4.6 insert cannot travel the 4.4 mm mortise slot to reach its
bore. Put a 4.0 OD insert into a 4.0 bore and there is **no interference at all** — it drops
in, looks seated, and holds nothing. The failure is silent and it is not obvious by eye.

⚠️ **4.0 mm OD is the standard M2.5 OD.** A substitution at that OD will not take an M3×16.
Thread-check the slim inserts against a real M3 screw before the first one goes in.

## 2. Dry the part first — this hazard is nylon-specific

PA6-CF is hygroscopic. **A damp part foams when the insert goes in**: the bore mouth erupts,
the insert sinks crooked, and the site is unrecoverable. Dry per `print-batch.md` (80 °C /
10 h) and set the inserts while the parts are still dry — do not dry, print, shelve for a
fortnight, then set.

## 3. Temperature — REASONED, not measured

Start **250 °C**, expect to land **260–280**, hard cap **300**.

That is lower than the 280 °C printing nozzle temperature, deliberately, for three reasons:
CF-filled nylon conducts heat better than neat polymer, the inserts are small and reach
temperature quickly, and a 0.25 mm floor on this robot has **already melted through** once
(the shoulder deck plate bores, now Ø3 vented through — §3b).

**These numbers have never been measured on this material with this iron.** They are a
starting point derived from the above, not a verified setting. Record what actually worked.

## 4. Coupon before the only copy of a part

Print a scrap with the same bore and set one. Check: does it sit flush, is it square, did
the mouth bulge, does an M3 thread in cleanly and pull straight?

Only then go near a `coax` or a `shoulder` — those are 138 cm³ / ~165 g PA6-CF parts and a
foamed bore is a reprint, not a repair.

## 5. Press from the face the part header names

Several sites press from **inner** faces a bench press cannot reach, so it is an iron with an
M3 tip, by hand, and the direction is not optional. §3b lists them per site. Two that bite:

- **battery_pocket mount pads** — press during battery **sub-assembly**, before the pack and
  trunk mate. The pad top is only reachable from outside the tray until then.
- **shoulder D456 pads / lower flange bosses** — 0.75 mm floor. Press to flush and **STOP**.

## 6. Order of operations

Set inserts **before** any joint that needs them is assembled, and before a part is captured
by another part. An insert you cannot reach is a reprint.
