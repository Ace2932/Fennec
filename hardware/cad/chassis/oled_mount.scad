// =============================================================================
// OLED MOUNT — SSD1331 display bracket (split off the E-stop pod, #40)
// =============================================================================
// The OLED used to be fused to control_pod (a +y deck extension + a panel that
// dodged the Ø40 mushroom cap). Split off: this small bracket BOLTS to the pod
// deck's +y edge (2× M2 into the pod heat-sets at x-96/-71, y23) and stands a
// panel that FACES -X (rearward) beside + behind the mushroom, readable by an
// operator behind the robot. The pod deck is symmetric again.
// SPI cable (7-wire) drops off the panel back down to the Arduino Nano in the bay.
// World/trunk frame (matches control_pod). PRINT: PETG/PA6-CF, foot-down, ~5 g.

$fn = 32; EPS = 0.05; M2_CLEAR = 2.3;

module oled_mount() {
    difference() {
        union() {
            // foot on the pod deck +y edge (z95..98)
            translate([-99, 22, 95]) cube([30, 5, 3]);
            // panel: vertical, faces -X (rear), on the +y side behind the mushroom
            translate([-99, 26, 98]) cube([3, 27, 26]);        // x-99..-96, y26..53, z98..124
        }
        // 2x M2 down into the pod deck heat-sets
        for (mx = [-96, -71])
            translate([mx, 23, 95 - EPS]) cylinder(d = M2_CLEAR, h = 3 + 2 * EPS);
        // OLED window (on the -X face) + 4x M2 for the SSD1331 module
        translate([-99 - EPS, 30, 102]) cube([3 + 2 * EPS, 20, 16]);
        for (my = [32, 48], mz = [103, 119])
            translate([-99 - EPS, my, mz]) rotate([0, 90, 0])
                cylinder(d = M2_CLEAR, h = 3 + 2 * EPS);
    }
}

oled_mount();
