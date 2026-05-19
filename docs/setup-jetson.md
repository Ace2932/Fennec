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

`nvpmodel` persists across reboots; `jetson_clocks` does not. Systemd-enable a oneshot service to peg clocks on every boot:

```bash
sudo tee /etc/systemd/system/jetson_clocks.service > /dev/null <<'EOF'
[Unit]
Description=Set Jetson clocks to max
After=nvpmodel.service

[Service]
Type=oneshot
ExecStart=/usr/bin/jetson_clocks
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jetson_clocks.service
sudo systemctl start jetson_clocks.service
systemctl status jetson_clocks.service
```

Expect `Active: active (exited)`. Heredoc gotcha: paste-mangled `tee` blocks can drop trailing lines and break `RemainAfterExit` parsing — confirm with `cat -A /etc/systemd/system/jetson_clocks.service` that lines end with `$` and there are no stray indented lines after `WantedBy=multi-user.target`.

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

## 11. Persistence verification (run after any reboot)

Paste this block to confirm everything stuck. Expect 8 green checks:

```bash
echo "=== JetPack ==="; cat /etc/nv_tegra_release | head -1
echo "=== Power ==="; sudo nvpmodel -q
echo "=== jetson_clocks ==="; systemctl is-active jetson_clocks.service
echo "=== CPU freq ==="; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
echo "=== DNS ==="; cat /etc/resolv.conf; lsattr /etc/resolv.conf
echo "=== Route ==="; ip route | grep default
echo "=== Internet ==="; ping -c 2 google.com | tail -2
echo "=== BT ==="; hciconfig hci0 | grep "UP"
```

Expected:
- JetPack: REVISION 5.0
- Power: MAXN_SUPER / id 2
- jetson_clocks: active
- CPU max freq: 1728000 kHz (1.728 GHz — A78AE peak)
- DNS: 8.8.8.8 + 1.1.1.1 with `----i---------e-------` (`i` = immutable flag)
- Route: `default via X.X.X.1 dev wlP1p1s0`
- Internet: <20 ms RTT to google.com
- BT: `UP RUNNING`

Verified 2026-05-17 on actual hardware — all 8 persist across `sudo reboot`.

---

## 12. ROS 2 Humble install (done 2026-05-17)

**Heads up:** the legacy `curl ros.key + sources.list` approach is deprecated. Use the new **ros2-apt-source deb package** (deb822 format, auto-handles key rotation).

```bash
# 1. Locale
sudo apt update
sudo apt install -y locales software-properties-common curl gnupg lsb-release
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
sudo add-apt-repository universe -y

# 2. Install ros2-apt-source (check github.com/ros-infrastructure/ros-apt-source/releases for latest tag)
curl -L -o /tmp/ros2-apt-source.deb https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.2.0/ros2-apt-source_1.2.0.jammy_all.deb
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update

# 3. Install ROS 2 Humble Desktop
sudo apt install -y ros-humble-desktop python3-colcon-common-extensions python3-rosdep python3-argcomplete

# 4. rosdep
sudo rosdep init
rosdep update           # no sudo — writes to ~/.ros

# 5. Auto-source
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc

# 6. Sanity
ros2 --help
echo $ROS_DISTRO    # humble
which ros2          # /opt/ros/humble/bin/ros2
```

### Smoke test (talker/listener)

Two SSH sessions:

```bash
# session A
ros2 run demo_nodes_cpp talker

# session B
ros2 run demo_nodes_py listener
```

Listener should print `I heard: [Hello World: N]`. Confirms DDS middleware works end-to-end.

### Paste-gotcha (terminal mangling)

Long curl URLs get newline-broken by some terminal pasters. If `curl: no URL specified!` or `bad/illegal format`, write the command to a file via `nano` (or `echo > install.sh`) then `bash install.sh`. See [`docs/setup-network.md`](./setup-network.md) for the heredoc paste-gotcha pattern.

---

## 13. Intel RealSense D456 install (done 2026-05-18)

Intel ships ARM64 binaries via their apt repo. Stock JetPack 6.2.2 kernel modules expose Color + Depth but **not the IMU streams** — must rebuild 3 in-tree driver modules with RealSense patches.

### Step A — librealsense2 apt install

```bash
sudo apt install -y curl gnupg

# Add Intel repo. Their signing key rotates — fetch current one direct from keyserver.
sudo mkdir -p /etc/apt/keyrings
sudo gpg --no-default-keyring --keyring /etc/apt/keyrings/librealsense.gpg --keyserver keyserver.ubuntu.com --recv-keys FB0B24895113F120
sudo chmod 644 /etc/apt/keyrings/librealsense.gpg

echo "deb [signed-by=/etc/apt/keyrings/librealsense.gpg] https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/librealsense.list

sudo apt update
sudo apt install -y librealsense2-utils librealsense2-dev
```

Verify D456 plugs in clean:
```bash
rs-enumerate-devices | head -20
```

At this point Color + Depth + Infrared streams work. **No IMU yet.**

### Step B — IMU enablement via kernel module patch

Two repos clone to `~/code/`:

```bash
mkdir -p ~/code && cd ~/code
git clone https://github.com/jetsonhacks/jetson-orin-librealsense.git
git clone https://github.com/jetsonhacks/jetson-orin-kernel-builder.git
```

#### B.1 Fetch kernel sources

```bash
cd ~/code/jetson-orin-kernel-builder
./scripts/get_kernel_sources.sh
```

Downloads NVIDIA L4T BSP matching your running kernel (5.15.185-tegra for JP 6.2.2) → `/usr/src/kernel/kernel-jammy-src/`. Copies current `/boot/config-$(uname -r)` as `.config` baseline. ~5-10 min.

#### B.2 Apply RealSense patches

```bash
cd ~/code/jetson-orin-librealsense/build
./patch-for-realsense.sh
```

Applies 2 of 3 patches (the 3rd HID patch is intentionally skipped — already in-tree since L4T 5.15.148).

#### B.3 Enable HID sensor modules in config

```bash
cd ~/code/jetson-orin-kernel-builder
./scripts/edit_config_cli.sh    # opens make menuconfig
```

Use `/` (search) to find + jump to each. Press `M` to toggle to module:
- `HID_SENSOR_HUB` (Device Drivers → HID support → Special HID drivers)
- `HID_SENSOR_ACCEL_3D` (Device Drivers → Industrial I/O support → Accelerometers)
- `HID_SENSOR_GYRO_3D` (Device Drivers → Industrial I/O support → Digital gyroscope sensors)

Save → exit. Confirm:

```bash
grep -E "HID_SENSOR_HUB|HID_SENSOR_ACCEL_3D|HID_SENSOR_GYRO_3D" /usr/src/kernel/kernel-jammy-src/.config
```

All three should be `=m`.

#### B.4 Compile modules

```bash
./scripts/make_kernel_modules.sh
```

~20-30 min on Orin Nano 6-core. Script auto-runs `make modules_install` + `depmod` at the end.

#### B.5 Unplug D456, reboot, plug back in

```bash
sudo reboot
# 90 sec wait
ssh aiden@<ip>
# plug D456 back into USB 3 (blue port)
lsmod | grep hid_sensor
rs-enumerate-devices | grep -A 5 "Motion Module"
```

Expected:
- `lsmod` shows `hid_sensor_hub`, `hid_sensor_accel_3d`, `hid_sensor_gyro_3d`, `hid_sensor_iio_common`, `hid_sensor_trigger`, `uvcvideo`
- `rs-enumerate-devices` Motion Module section shows Accel @ 400/200/100 Hz + Gyro @ 400/200 Hz

### Step C — ROS 2 wrapper

```bash
sudo apt install -y ros-humble-realsense2-camera
ros2 launch realsense2_camera rs_launch.py enable_color:=true enable_depth:=true enable_gyro:=true enable_accel:=true
```

Other session:
```bash
ros2 topic list | grep camera
ros2 topic hz /camera/camera/color/image_raw       # ~30 Hz
ros2 topic hz /camera/camera/depth/image_rect_raw  # ~30 Hz
ros2 topic hz /camera/camera/accel/sample          # ~100 Hz default (settable to 400)
ros2 topic hz /camera/camera/gyro/sample           # ~200 Hz default (settable to 400)
```

For unified IMU topic (single `/camera/camera/imu` at the higher of the two rates), add `unite_imu_method:=2` to the launch line. Most SLAM packages handle separate accel + gyro fine, so the unified topic is optional.

### Verified 2026-05-18

D456 firmware 5.15.0.2 / recommended 5.17.0.10 (firmware update deferred). All streams green at the rates above. Cost: ~$0 (kernel patch path is free, just CPU time).

---

## Next (separate sessions — Phase 1 plan)

- NVMe install + rootfs migration **(deferred — NAND shortage, see BOM §1; run from 128 GB microSD until prices recover)**
- unilidar_sdk2 + `unitree_lidar_ros2` (done 2026-05-17 — see status log)
- POINT-LIO ROS 2 (dfloreaa fork) + RTAB-Map eval
- Combined D456 + L2 + ROS 2 sensor stream test once switch + Cat6 arrive
- D456 firmware update to 5.17.0.10 via `rs-fw-update` (low priority)

---

> **Status:** updated 2026-05-17 with verified procedure from initial bring-up. JetPack 6.2.2 / L4T 36.5 / MAXN_SUPER / BT confirmed working.
