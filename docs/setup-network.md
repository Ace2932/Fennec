# Network Setup — Unitree L2 + Dev Access

Static IPs, Ethernet switch topology, and SSH-over-WiFi for the Jetson.

## Will cover
- Jetson `eth0` static IP: 192.168.1.2/24
- Unitree L2 default IP: 192.168.1.62, UDP target port 6101
- 5-port Gigabit unmanaged switch wiring (Jetson + L2 + dev laptop)
- Dev laptop static IP: 192.168.1.10
- Verifying L2 UDP packet flow (`tcpdump`, rviz2)
- Simultaneous SSH-over-WiFi while LiDAR streams on Ethernet
- WiFi 5 module (built into P3766) — connecting + signal verification
- Optional: mDNS / Avahi for hostname-based access

> **Status:** placeholder — populate when switch + cables arrive.
