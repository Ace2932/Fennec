// =============================================================================
// NOVA chassis — BELLY BATTERY POCKET (4S Ovonic 6000, 155 x 46 x 35, 510g)
// =============================================================================
// Top-level design: docs/design-outline.md. Trunk frame (z0 = floor bottom,
// +x FRONT). Lowest-CoM pack, swap WITHOUT tools (design-outline service
// table: battery = strap only, 0 screws).
//
// PRINT: PETG-CF, FLOOR-DOWN (tray bottom on the bed; opening + rim flange
//   up) — zero supports. 3 walls / 0.25 / 20% (print-batch §2).
//
// Shape: open-TOP tray hanging under the stock shell — the shell floor caps
// the cavity. Pack slides in from the REAR opening; a velcro strap fences
// the opening through two side-wall slots. Front wall + side walls guide,
// tray bottom carries the pack.
//
// Mount: TOP-FLANGE MOUNT (AUD-1 fix, 2026-07-10 — replaces the retired
// full-height boss columns, which fouled the pack: their inner edge sat
// 1.15mm inside the pack half-width for the WHOLE column height, and no
// column position cleared the pack without also fouling the leg-sweep ROM;
// see docs/improvement-backlog.md AUD-1 for the full history). 6x M3x10
// driven from INSIDE the trunk, through the 3.9 floor slab, straight into
// a VERTICAL HEAT-SET INSERT (AUD-11 fix, 2026-07-10 — supersedes this
// mount's original side-loaded M3 nut trap) held in a LOCAL PAD thickening
// the rim flange (not a full-height column) at (x -40/0/+40, y +/-27.5).
// The AUD-1 nut trap put its bolt axis at y=26.5, flush on the cavity
// wall's OUTER face (24.0+3.2=27.2) — the trap's own Ø3.4 bore breached
// 0.0mm through into the LiPo bay (open window x6, confirmed defect: a
// loose nut could migrate onto the pouch). AUD-11 moves the bolt/insert
// axis to y=27.5 (a fixed M3x3.8 Ruthex heat-set, Ø4.0x4.2mm blind, pressed
// from the pad's TOP face before pack + trunk mate), which restores a
// >=1.5mm sealed wall to the cavity — see the pad union()/difference()
// comments below for the exact wall-thickness math. The pad's OUTER edge
// stays PINNED at y=30.75 (PAD_Y1, does NOT track the bolt axis) so this
// fix does not reopen the leg-sweep clearance question the AUD-1 pad
// geometry already closed (check_fit.py ~658-673). The stock floor gets a
// MODELED Ø3.4 clearance hole there — trunk.scad / trunk_build.py (DERIVED
// TRUNK): printed in, NO drilling at assembly. Retention = THIS part's own
// heat-set pad (below), never the trunk. **The part-5 floor boss plate
// must adopt this same 6-hole pattern** (unchanged XY — only the
// pocket-side mount depth/fastener changed): screws sandwich plate + floor
// + tray (plate spreads the load; the tray bores double as the drill
// template from below).
//
// Pack: 155 fore-aft (overhangs the 127 trunk by ~14.8/end, passing 0.25
// under the shoulder flange bottoms at z 0.05); leads exit the pack's REAR
// face into open air behind the trunk end, rise at x ~-70, and enter the
// trunk through the shoulder flange's NEW bottom-center notch (trunk
// y +/-10 up to z 12) to the MRBF-30 / Blue Sea 5191 block INSIDE.
// ⚠ 5191 block dims not in dimensions.md — block mounting = part-5 plate
// territory, note there.
//
// Clearances (mesh/gate-verified): rim top z -0.2 (0.2 under the floor);
// crouch-pose knees pass outboard (tibia plane y 30..55 vs walls +/-30.5).
// Fit gate: check_fit.py cases 6-7; case 13 verifies the 6 trunk.scad bores
// land on this part's own bolt axes. First article: pack slide fit
// (0.8/side on LISTING dims — caliper the real pack!), strap slot deburr —
// no drilling (the trunk hole is now printed-in).

$fn = 64;
EPS = 0.05;

PACK = [155, 46.8, 35];          // CALIPER 2026-07-07 (was 46 listing width)
CLR  = 0.6;                       // per side (width caliper landed +0.8 → keep
                                  // ~0.6/side; pack slides on the tray, EVA
                                  // pad + strap preload it, backlog #29)
CAV_X = PACK[0] / 2 + CLR;        // 78.1
CAV_Y = PACK[1] / 2 + CLR;        // 24.0
WALL  = 3.2;
RIM_Z = -0.2;                     // tray top plane (0.2 under the shell)
CAV_Z0 = RIM_Z - (PACK[2] + CLR); // -36.0 cavity floor
BOT_Z  = CAV_Z0 - WALL;           // -39.2 tray bottom
FRONT_X1 = CAV_X + WALL;          // 81.5 front wall outer

BOSS_X = [-35, 0, 40];   // #68 fix 2026-07-12: -x col -40->-35 (== floor_plate
                          // BAT_X + trunk_build BATT_BOSS_X) -- clears the
                          // -40.5 mezzanine standoff foot the -40 csk overlapped
BOSS_Y = 27.5;            // AUD-11 fix (heat-set, 2026-07-10): was 26.5, which
                          // put the bolt/pilot axis flush on the cavity wall
                          // (CAV_Y=24 + WALL=3.2 = 27.2 outer face) -- the
                          // nut-trap cut into that same axis breached the
                          // wall at 0.0mm (see AUD-11 writeup below). +1.0
                          // buys a 1.5mm sealed wall for the new heat-set
                          // pilot. PAD_Y1 below is PINNED (does not track
                          // this move) so leg-sweep clearance is unchanged.
HEATSET_D = 4.0;  HEATSET_L = 4.2;   // Ruthex M3x3.8 short insert: bore
                          // Ø4.0, 4.2mm deep blind (was 6.2, the old
                          // full-depth spec -- unused since the nut-trap
                          // scheme; now live again for the heat-set pilot)
MOUTH_D = 4.6;             // insert mouth chamfer diameter (0.3mm taper
                          // HEATSET_D -> MOUTH_D at the pad top, eases
                          // insert start during heat-press)
M3_CLEAR = 3.4;            // shared bolt-clearance diameter -- not cut
                          // directly in THIS part anymore (the insert bore
                          // itself is the top opening), kept here only so
                          // floor_plate.scad's BAT_Y-linked csk and
                          // trunk_build.py's BATT_CLEAR_D read as the same
                          // number as this file's documentation.
PAD_HW  = 4.25;            // pad half-width in x (unchanged -- old boss
                          // radius, still the local-pad half-width)
PAD_Y1  = 30.75;           // AUD-11 fix: pad OUTER edge, PINNED at the old
                          // BOSS_Y(26.5)+PAD_HW(4.25) value. Do NOT derive
                          // this from the new BOSS_Y (27.5+4.25=31.75) --
                          // check_fit.py lines ~658-673 document that a
                          // full-height column with outer edge at 30.0
                          // already HITs the leg-sweep ROM (inboard haa=15,
                          // hfe fold 45-50, every kfe, all four hips); this
                          // pad is short (6mm below the rim, nowhere near
                          // leg-sweep depth) but pinning the outer edge at
                          // the ALREADY-gate-clean 30.75 keeps leg
                          // clearance identical to the current build,
                          // rather than re-opening that question.
// AUD-11 fix (heat-set, 2026-07-10): the 6 nut-trap mounts are now VERTICAL
// HEAT-SET PILOTS in the same local pad -- see the union()/difference()
// comments below for the full writeup (this replaces the AUD-1 nut-trap
// scheme, which is the DEFECT this fix addresses).
PAD_Z0  = RIM_Z - 6;      // local pad bottom -> 6mm local flange thickness
                          // (vs the base flange's 4mm; +2mm local, HIGH near
                          // the rim -- old columns reached BOT_Z=-39.2)

module battery_pocket() {
    difference() {
        union() {
            // bottom
            translate([-CAV_X, -CAV_Y - WALL, BOT_Z])
                cube([FRONT_X1 + CAV_X, 2 * (CAV_Y + WALL), WALL]);
            // side walls
            for (sy = [-1, 1])
                translate([-CAV_X, min(sy * (CAV_Y + WALL), sy * CAV_Y), BOT_Z])
                    cube([FRONT_X1 + CAV_X, WALL, -BOT_Z + RIM_Z]);
            // front wall
            translate([CAV_X, -CAV_Y - WALL, BOT_Z])
                cube([WALL, 2 * (CAV_Y + WALL), -BOT_Z + RIM_Z]);
            // rim flange tying the wall tops to the front wall — thin,
            // full-length structural rib (KEPT; unrelated to the AUD-1/-2
            // fix). Outer edge PINNED to PAD_Y1 (not BOSS_Y+4.25) for the
            // same reason the pad below is pinned — this rib used to
            // coincide with the pad's old outer edge by construction, but
            // there's no reason to let it drift outboard just because
            // BOSS_Y moved; keeping it at the gate-clean 30.75 leaves the
            // whole rim silhouette, not just the 6 pads, leg-sweep-neutral.
            for (sy = [-1, 1])
                translate([-45, min(sy * PAD_Y1, sy * CAV_Y), RIM_Z - 4])
                    cube([90, PAD_Y1 - CAV_Y, 4]);
            // AUD-11 FIX (heat-set, 2026-07-10 — supersedes the AUD-1 nut-
            // trap): the 6 M3 mounts are still LOCAL PADS thickening the
            // rim flange only at (x BOSS_X, y +/-BOSS_Y) — the full-height
            // boss columns from before AUD-1 are still GONE, unchanged by
            // this fix. What changed is the fastener: AUD-1's side-loaded
            // nut trap cut its bolt-clearance bore + trap pocket straight
            // through to the pad's OUTBOARD face, at y=BOSS_Y=26.5 — but
            // the pad's INBOARD face sits flush at CAV_Y=24.0 (the cavity
            // wall's inner face) and the wall itself is only WALL=3.2mm
            // thick, so the wall's OUTER face is at CAV_Y+WALL=27.2 —
            // *inboard* of the old BOSS_Y=26.5 bolt axis by 0.7mm. A
            // vertical Ø3.4 bore centered ON that axis (radius 1.7) reached
            // to y=24.8, clean INSIDE the cavity's own wall face (27.2) —
            // i.e. the bore breached straight into the LiPo bay: a 0.0mm
            // wall, the confirmed DEFECT this fix closes (open window x6,
            // risk of a loose nut migrating onto the pouch).
            //
            // Fix: BOSS_Y moved 26.5 -> 27.5 (+1.0, see BOSS_Y comment
            // above), so the vertical heat-set pilot (below) now has its
            // inboard edge at 27.5 - 2.0(radius) = 25.5, a full 1.5mm
            // outboard of the cavity wall's inner face (CAV_Y=24.0) --
            // VERIFY (this fix's whole point): sealed >=1.5mm wall, not
            // 0.0mm. The pad's OUTER edge is PINNED at PAD_Y1=30.75 (does
            // NOT track BOSS_Y) — see PAD_Y1 comment above for why
            // (leg-sweep regression guard in check_fit.py ~658-673).
            //
            // Each pad spans a FIXED y [CAV_Y, PAD_Y1] = [24.0, 30.75] —
            // starts flush at CAV_Y, i.e. ALWAYS outboard of the pack
            // (half-width 23.4), never intruding it, and its outer edge
            // never grows past the already-gate-clean 30.75 no matter
            // where BOSS_Y sits inside that span.
            //
            // Each pad fuses to the full-height side wall along a whole
            // rectangular face (x 8.5 wide x 6mm tall, at y=CAV_Y+WALL=
            // 27.2, the wall's outer face) — real face-to-face fusion, not
            // the old boss's thin tangent-line contact at the flange top
            // (the old boss only really tied in through the 4mm top
            // flange down a 35mm cantilever — mesh_health said "1 body"
            // but a z-section showed the join was a near-tangent line).
            // Section-verified fused mass: see check_fit.py run notes.
            for (bx = BOSS_X, sy = [-1, 1])
                translate([bx - PAD_HW, min(sy * PAD_Y1, sy * CAV_Y), PAD_Z0])
                    cube([2 * PAD_HW, PAD_Y1 - CAV_Y, RIM_Z - PAD_Z0]);
        }
        // AUD-11 FIX (heat-set, 2026-07-10 — supersedes the AUD-1 nut trap,
        // the DEFECT this fix closes: the old trap cut a 0.0mm wall to the
        // LiPo cavity, see the union() comment above for the full
        // measurement). Each mount is now a VERTICAL, BLIND heat-set
        // pilot: Ø4.0 (HEATSET_D, Ruthex M3x3.8 short insert) x 4.2mm deep
        // (HEATSET_L), running DOWN from the pad top (RIM_Z=-0.2) to
        // z=-4.4 — leaves a 1.8mm floor to PAD_Z0(-6.2), well clear of the
        // cavity. A 0.3mm mouth chamfer (Ø4.6 mouth, MOUTH_D) eases insert
        // start. Mouth-up: the insert is heat-pressed into the pad from
        // its TOP face (RIM_Z) during battery sub-assembly, BEFORE the
        // pack + trunk mate — no in-place pressing needed post-assembly.
        // The M3 bolt then drives from ABOVE, down through floor_plate's
        // Ø3.4 CSK + the stock trunk floor's own Ø3.4 bore (trunk_build.py
        // SET 1), and threads straight into the insert bore below — this
        // part cuts no separate clearance hole of its own; the insert bore
        // (Ø4.0, bigger than the M3 shank) IS the top opening.
        //
        // Bolt: M3x10 (was M3x8 nut-trap spec). Reach budget: CSK head
        // seats at floor_plate top z5.9, insert bottom sits at z-4.0 (top
        // -0.2 minus 3.8mm of Ruthex thread engagement) — 5.9 - (-4.0) =
        // 9.9mm head-to-insert-bottom, so M3x10 lands flush with ~0.1mm to
        // spare (M3x8 would have come up 1.9mm short of the insert). The
        // 6.1mm floor_plate(2.0)+stock-floor(3.9)+web dead reach above the
        // pocket rim is unchanged from the AUD-1 note; only the terminal
        // 3.8mm engagement, not the reach, is new. BOM: 6x M3x10 socket/
        // CSK screws replace the AUD-1 M3x8 + M3 hex nut; add 6x Ruthex
        // M3x3.8 heat-set inserts.
        for (bx = BOSS_X, sy = [-1, 1]) {
            // 0.3mm mouth chamfer: HEATSET_D at the chamfer/bore junction
            // (bottom), tapering UP to MOUTH_D at the pad top face (top of
            // this cylinder pokes EPS above RIM_Z for a clean boolean cut)
            translate([bx, sy * BOSS_Y, RIM_Z - 0.3])
                cylinder(d1 = HEATSET_D, d2 = MOUTH_D, h = 0.3 + EPS);
            // straight Ø4.0 blind bore, RIM_Z-HEATSET_L (-4.4) up to the
            // chamfer base (RIM_Z-0.3) -- combined depth = HEATSET_L (4.2)
            translate([bx, sy * BOSS_Y, RIM_Z - HEATSET_L])
                cylinder(d = HEATSET_D, h = HEATSET_L - 0.3);
        }
        // strap slots AT the rear opening: the strap wraps the pack's REAR
        // CORNER (direct tension against slide-out — friction-only
        // retention was a design-review finding; shake-test at FA)
        for (sy = [-1, 1])
            translate([-77, sy * (CAV_Y + WALL / 2) - (WALL / 2 + EPS),
                       BOT_Z + 6])
                cube([16, WALL + 2 * EPS, 5]);
        // (lead path: the pack's rear face sits at x -78.3, BEHIND the
        //  trunk end — leads rise in open air at x ~-70 and enter the trunk
        //  through the shoulder flange's bottom-center notch (s_x +/-10 to
        //  trunk z 12, shoulder.scad rev) to the MRBF block inside.)
        // strap under-pack groove: strap wraps the pack INSIDE the rear
        // opening; groove across the bottom lets it pass under the pack.
        // #71 fix (2026-07-12): 2->1.2mm deep so the tray floor stays 2.0mm
        // (was 1.18mm, thin under the 510g pack); 1.2 still clears a ~1mm strap.
        translate([-77, -CAV_Y - WALL - EPS, CAV_Z0 - 1.2])
            cube([16, 2 * (CAV_Y + WALL) + 2 * EPS, 1.2 + EPS]);

        // skid-rail key recesses (backlog #15, skid_rail.scad): 0.6 deep
        // in the 3.2 bottom (2.6 remains — pack load spreads over the
        // whole tray floor, bending trivial). Keys take the shear, CA/VHB
        // takes the peel; rails sacrificial + replaceable. Rails at
        // y +/-15, keys centered trunk x -43 / +58 (clear of the strap
        // groove x -77..-61; the AUD-1/-2 mount pads at y +/-BOSS_Y=27.5
        // are shallow, PAD_Z0=-6.2, nowhere near this BOT_Z=-39.2 tray
        // floor, so they don't constrain key placement here).
        for (sy = [-1, 1], kx = [-43, 58])
            translate([kx - 10.3, sy * 15 - 4.3, BOT_Z - EPS])
                cube([20.6, 8.6, 0.6 + EPS]);
    }
}

battery_pocket();
