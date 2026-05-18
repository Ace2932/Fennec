# Network Setup — Unitree L2 + Dev Access

Static IPs, Ethernet switch topology, and SSH-over-WiFi for the Jetson.

## Jetson interface naming (JetPack 6.2.x)

JetPack uses systemd predictable names, not `wlan0`/`eth0`:

| Interface | Role |
|-----------|------|
| `wlP1p1s0` | Built-in WiFi 5 (802.11ac/ab/gn) |
| `enP8p1s0` | Onboard Gigabit Ethernet |
| `l4tbr0` | L4T USB-C gadget bridge (192.168.55.1) — for headless serial console |
| `usb0` / `usb1` | USB net (Mac Internet Sharing path) |
| `can0` | CAN bus (unused for v1) |
| `docker0` | Docker virtual bridge (172.17.0.0/16) |

## Will cover
- Jetson `enP8p1s0` static IP: 192.168.1.2/24
- Unitree L2 default IP: 192.168.1.62, UDP target port 6101
- 5-port Gigabit unmanaged switch wiring (Jetson + L2 + dev laptop)
- Dev laptop static IP: 192.168.1.10
- Verifying L2 UDP packet flow (`tcpdump`, rviz2)
- Simultaneous SSH-over-WiFi while LiDAR streams on Ethernet
- WiFi 5 module (built into P3766) — connecting + signal verification
- Optional: mDNS / Avahi for hostname-based access

## Unitree L2 — confirmed launch params (from unitree_lidar_ros2/launch/launch.py)

After building `unilidar_sdk2` on the Jetson (verified 2026-05-17), the bundled ROS 2 wrapper hardcodes these defaults — match the network plan to these:

| Param | Value | Notes |
|-------|-------|-------|
| `lidar_ip` | `192.168.1.62` | L2 default per Unitree user manual |
| `lidar_port` | `6101` | L2 → Jetson UDP |
| `local_ip` | `192.168.1.2` | Jetson `enP8p1s0` must be set to this |
| `local_port` | `6201` | Jetson receive UDP |
| `cloud_topic` | `/unilidar/cloud` | point cloud out |
| `imu_topic` | `/unilidar/imu` | IMU out (~250 Hz) |
| `cloud_frame` | `unilidar_lidar` | TF frame for URDF |
| `imu_frame` | `unilidar_imu` | TF frame for URDF |
| `cloud_scan_num` | 18 | L2 vertical scan count |
| `range_min` / `range_max` | 0 / 100 m | L2 working range |
| `work_mode` | 0 | UDP mode (1 = serial) |

Launch command (once L2 is on the network + Jetson static IP set):
```bash
ros2 launch unitree_lidar_ros2 launch.py
```

Auto-spawns rviz2 with `view.rviz` config.

### POINT-LIO ROS 2 integration

When wiring POINT-LIO (Phase 2), set its YAML to subscribe:
- `lid_topic: /unilidar/cloud`
- `imu_topic: /unilidar/imu`

### URDF frame mapping

When `nova_description` URDF is written (Phase 1+), link these frames to the L2 mount point on the chassis:
- `unilidar_lidar` — point cloud origin
- `unilidar_imu` — IMU origin (small offset from LiDAR origin per L2 datasheet)

---

## First-boot WiFi / DNS gotchas (Jetson Orin Nano + JetPack 6.2.1)

Hit on 2026-05-17 during initial bring-up. Documenting because every future Jetson re-flash will hit the same things.

### Gotcha 1: oem-config WPA association fails

The text-mode network setup at first-boot has a buggy WPA key exchange. It will report "Failure of key exchange and association" even with correct password. **Don't fight it.** Pick "do not configure network at this time" and finish setup. WiFi works fine from the CLI after boot.

### Gotcha 2: `l4tbr0` USB-C bridge hijacks the default route

If you connected USB-C from Jetson to Mac for serial console access, the Jetson auto-creates `l4tbr0` (192.168.55.0/24) with a default route via 192.168.55.100. This **steals the default route** even when WiFi is up. All outbound packets go to the Mac and die (unless Mac is running Internet Sharing).

**Diagnostic:** `ip route` shows `default via 192.168.55.100 dev l4tbr0`.

**Fix (one of):**
- **Easiest:** unplug the USB-C cable to the Mac. The `l4tbr0` default route disappears, WiFi takes over.
- **Keep USB-C, prefer WiFi by metric:**
  ```bash
  sudo nmcli connection modify "<SSID>" ipv4.route-metric 100
  ```
  Lower metric wins. l4tbr0's default is at metric 32766, WiFi default is at 600 from DHCP — both lose to the L4T bridge's lower path until you override.

### Gotcha 3: NetworkManager doesn't write `/etc/resolv.conf` at all

Editing `/etc/resolv.conf` directly survives until the next `nmcli connection up`. Worse, even after pinning DNS in the NetworkManager profile, **NetworkManager on JetPack 6.2.x does not write the DNS entries to `/etc/resolv.conf` on reboot.** The file ends up empty (size 0), even though `nmcli connection show` reports the correct DNS servers. Result: `Temporary failure in name resolution` after every reboot.

**Step 1 — pin DNS in the NetworkManager profile** (so the connection profile is correct):

```bash
sudo nmcli connection modify "<SSID>" ipv4.dns "8.8.8.8 1.1.1.1"
sudo nmcli connection modify "<SSID>" ipv4.ignore-auto-dns yes
sudo nmcli connection down "<SSID>"
sudo nmcli connection up "<SSID>"
```

`ignore-auto-dns yes` keeps DHCP DNS from re-merging on every `up`.

**Step 2 — write resolv.conf manually + lock immutable** (so NetworkManager can't truncate it):

```bash
sudo chattr -i /etc/resolv.conf 2>/dev/null || true
printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" | sudo tee /etc/resolv.conf
sudo chattr +i /etc/resolv.conf
cat /etc/resolv.conf
ping -c 2 google.com
```

`chattr +i` sets the immutable filesystem flag. NetworkManager (or any other agent) cannot modify or truncate the file until you `chattr -i` first. Brute-force durable fix.

**Verify after reboot** — `cat /etc/resolv.conf` should still show the two nameservers. If it ever shows empty, the immutable flag got cleared by an `apt full-upgrade` of `resolvconf`-related packages; just re-apply Step 2.

### Full recovery sequence (copy-paste)

If WiFi association works but `ping google.com` fails:

```bash
# 1. Re-up WiFi to get a fresh default route
sudo nmcli connection up "<SSID>"

# 2. Confirm default route is via wlP1p1s0, not l4tbr0
ip route   # should show: default via 10.0.1.1 dev wlP1p1s0

# 3. Pin DNS + ignore DHCP DNS
sudo nmcli connection modify "<SSID>" ipv4.dns "8.8.8.8 1.1.1.1"
sudo nmcli connection modify "<SSID>" ipv4.ignore-auto-dns yes
sudo nmcli connection modify "<SSID>" ipv4.route-metric 100
sudo nmcli connection down "<SSID>" && sudo nmcli connection up "<SSID>"

# 4. Verify
cat /etc/resolv.conf
ping -c 2 google.com
```

### What was NOT the problem (red herrings tried)

- `iw reg set US` — regdomain. Didn't fix. JetPack 6.2.1 ships with sane defaults.
- WPA3 vs WPA2 on the router. Router was WPA2 already.
- Special characters in password. Password was simple.
- `/etc/resolv.conf` direct edit. Got overwritten on every `nmcli up`.

### After WiFi works — SSH from Mac

Once `ping google.com` works, SSH in from the Mac and drop the serial console:

```bash
# From Mac
ssh aiden@10.0.1.135
```

Replace IP with what `ip addr show wlP1p1s0` reports.

---

> **Status:** updated 2026-05-17 with JetPack 6.2.1 first-boot WiFi recovery sequence. Populate the L2 / static-IP / switch sections when switch + cables arrive (Phase 1).
