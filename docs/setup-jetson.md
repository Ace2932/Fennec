# Jetson Orin Nano Super — Setup

Walked through 2026-05-17 on the actual hardware. Captures the verified procedure for JetPack 6.2.2.

## 1. Flash microSD on Mac

- Download `jp62-r1-orin-nano-sd-card-image.zip` from `developer.nvidia.com/downloads/embedded/L4T/r36_Release_v4.4/jp62-r1-orin-nano-sd-card-image.zip` (NVIDIA Dev account required)
- Unzip
- Flash via Balena Etcher → 128 GB microSD. **Enable "Skip validation"** in settings + run `caffeinate -d` in a terminal to prevent macOS sleep mid-write. Validation hangs if the Mac sleeps.
- ~10 min write

## 2. Pre-boot

- Insert SD card into Jetson SD slot (underside of carrier board)
- Connect: DisplayPort cable to monitor, USB-A keyboard + mouse (the **wired** kind — bluetooth peripherals don't pair until WiFi is up)
- Optional: USB-C cable from Jetson UFP port to Mac (for serial console access — but see Gotcha 2 in [`setup-network.md`](./setup-network.md), it'll hijack the default route later)
- Plug in 12V barrel jack (use included PSU)

## 3. First-boot wizard (text-mode oem-config)

- **APP partition size**: accept default (max — fills the card, ~119 GB)
- **Locale, timezone, keyboard**: as appropriate
- **Hostname**: `nova-jetson`
- **User**: full name "Aiden Fox" → username `aiden`
- **Encrypt home directory**: No
- **Network**: WiFi setup at this stage **WILL FAIL** with cryptic key-exchange error even with correct password. Select "do not configure network at this time" and continue. (See [`setup-network.md`](./setup-network.md) Gotcha 1.)
- **Install Chromium**: Yes (snap install fails without network — that's fine, install later)

Wizard reboots Jetson when done.

## 4. First real boot — fix networking

Login at the text console (or via USB-C serial from Mac with `screen /dev/cu.usbmodem<TAB> 115200`).

Apply the **full WiFi + DNS recovery sequence** documented in [`setup-network.md`](./setup-network.md). Three things to do in order:
1. Connect WiFi via `nmcli` (oem-config WPA bug doesn't affect CLI)
2. Pin DNS in the NM profile + `ignore-auto-dns yes`
3. Write `/etc/resolv.conf` manually + `chattr +i` (NetworkManager on this image doesn't write it)

Verify: `ping -c 2 google.com` works.

## 5. Bump JetPack 6.2.1 → 6.2.2

NVIDIA doesn't ship a 6.2.2 SD image; the upgrade is apt-based but requires bumping the L4T repo from r36.4 to r36.5 first:

```bash
sudo sed -i 's|r36.4|r36.5|g' /etc/apt/sources.list.d/nvidia-l4t-apt-source.list
sudo apt update
sudo apt list --upgradable 2>/dev/null | grep -E "nvidia|l4t" | head    # should show 36.5.0 packages
sudo apt full-upgrade -y
```

Mid-upgrade you'll get one config-file prompt:
> Configuration file `/etc/systemd/nv-oem-config-post.sh` … Deleted by you or by a script.

Hit **Y** (install package maintainer's version). Same answer for any other NVIDIA-shipped config-file prompts unless you've hand-tweaked them.

After upgrade:
```bash
cat /etc/nv_tegra_release   # should show R36 / REVISION 5.0
sudo reboot
```

## 6. Power mode + clocks

After reboot, set MAXN_SUPER (not mode 0 — that's 15W on the Orin Nano Super):

```bash
sudo nvpmodel -p --verbose | grep "POWER_MODEL: ID"
```

Look for `ID=2 NAME=MAXN_SUPER` on the Orin Nano Super Dev Kit (P3766). Set it:

```bash
sudo nvpmodel -m 2
sudo nvpmodel -q       # confirm "MAXN_SUPER"
sudo jetson_clocks     # peg clocks high (with 's', not 'clock')
```

`nvpmodel` persists across reboots; `jetson_clocks` does not. If you want clocks pegged on every boot, systemd-enable a oneshot service that runs it.

## 7. Bluetooth presence check (resolves Open Decision 2b)

```bash
hciconfig -a           # should show hci0 UP RUNNING + Realtek manufacturer + HCI version
bluetoothctl list
```

On the P3766 dev kit: Realtek controller, BT 5.1, confirmed 2026-05-17.

## 8. SSH key from Mac (kill password prompts)

On Mac:
```bash
ssh-copy-id aiden@10.0.1.135   # use whatever IP the Jetson got
```

Generate the key first if needed: `ssh-keygen -t ed25519 -C "afox@mac"`. After: `ssh aiden@10.0.1.135` no password.

## 9. Optional: mDNS hostname

```bash
sudo apt install -y avahi-daemon
```

Then from Mac: `ssh aiden@nova-jetson.local` — survives IP changes.

## 10. Install jetson-stats (jtop)

```bash
sudo apt install -y python3-pip
sudo -H pip install -U jetson-stats
sudo reboot
```

After reboot: `jtop` runs a TUI showing CPU/GPU/temps/memory/power. Use instead of `htop`.

## Next (separate sessions — Phase 1 plan)

- NVMe install + rootfs migration **(deferred — NAND shortage, see BOM §1; run from 128 GB microSD until prices recover)**
- ROS 2 Humble install
- librealsense2 ARM64 build + `realsense2_camera`
- unilidar_sdk2 + `unitree_lidar_ros2` (discodyer fork)
- POINT-LIO and/or RTAB-Map
- Sensor smoke tests via `realsense-viewer` + rviz2 with L2 cloud

---

> **Status:** updated 2026-05-17 with verified procedure from initial bring-up. JetPack 6.2.2 / L4T 36.5 / MAXN_SUPER / BT confirmed working.
