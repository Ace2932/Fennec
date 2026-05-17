# Backup Registry

SD card / data image backups. Update on every new backup.

## LeRobot Pi SD card

| Field | Value |
|-------|-------|
| Date | 2026-05-16 |
| Source | LeRobot Raspberry Pi microSD (128 GB Amazon Basics, FAT32 boot + ext4 root) |
| Source device on Mac | `/dev/disk8` (at time of backup) |
| Output file | `/Users/afox/Backups/lerobot-pi-128gb-2026-05-16.img.gz` |
| Compression | `pigz` (parallel gzip), default level |
| SHA256 | `39b571261b0cf24e8d55682b97e1932c1f0cfcfc76fa9c50d332c0924928f832` |
| Why | Pre-emptive backup before reformatting the card for Jetson JetPack 6.2.1 flash |

### Backup procedure used

```bash
sudo dd if=/dev/rdisk8 bs=4m | pigz -c > /Users/afox/Backups/lerobot-pi-128gb-2026-05-16.img.gz
```

Hit `Ctrl-T` during `dd` for progress (BSD dd built-in).

### Restore procedure

```bash
gunzip -c /Users/afox/Backups/lerobot-pi-128gb-2026-05-16.img.gz | sudo dd of=/dev/rdiskN bs=4m
```

Replace `N` with target SD card device (verify with `diskutil list external physical`). Re-hash to confirm bit-for-bit integrity before restoring:

```bash
shasum -a 256 /Users/afox/Backups/lerobot-pi-128gb-2026-05-16.img.gz
# should match: 39b571261b0cf24e8d55682b97e1932c1f0cfcfc76fa9c50d332c0924928f832
```

### Notes

- Compressed size: TBD (record once size is checked via `ls -lh`)
- The 128 GB Amazon Basics card was reformatted on 2026-05-17 to host JetPack 6.2.1 for the Jetson Orin Nano. Pi data lives only in this image.
- Off-Mac copy: TBD — consider transferring `.gz` to external drive / cloud for redundancy
