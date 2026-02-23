# Plan: `scripts/pi-setup-sd.sh` — Automated Pi SD Card Provisioning

## Context
The Pi demo pipeline has a gap: `pi-deploy.sh` assumes the Pi already has OS + SSH + Docker. Currently that's manual (Imager GUI, SSH in, apt install). This script fills the gap so the flow is fully automated from bare SD card to running demo.

## Approach: Two-Stage Boot Provisioning

**Stage 1 — `firstrun.sh`** (runs before systemd, no network):
- Create user with SSH key
- Set hostname to `marge-pi`
- Enable SSH
- Configure WiFi (optional)
- Install Stage 2 systemd service
- Reboot

**Stage 2 — `marge-provision.sh`** (runs as systemd oneshot after reboot, with network):
- Wait for network (120s timeout with ping loop)
- `apt-get update`
- Install Docker via `get.docker.com`
- Add user to docker group
- Write marker file `~/.marge-provisioned`
- Disable itself

Why not cloud-init: only added to Pi OS Nov 2025, not battle-tested. `firstrun.sh` is what Imager itself uses.

## Deliverable

One file: `scripts/pi-setup-sd.sh` (~250 LOC) with Stage 1 and Stage 2 scripts embedded as heredocs.

```
Usage: sudo ./scripts/pi-setup-sd.sh /dev/sdX [OPTIONS]

Options:
  --wifi-ssid SSID       WiFi (optional, ethernet assumed if omitted)
  --wifi-pass PASSWORD   WiFi password
  --ssh-key PATH         SSH pubkey (default: ~/.ssh/id_ed25519.pub)
  --hostname NAME        Default: marge-pi
  --user USERNAME        Default: pi
  --password PASSWORD    Default: marge-demo
  --image PATH           Pre-downloaded .img/.img.xz (otherwise downloads Pi OS Lite 64-bit)
  --yes                  Skip confirmation
```

## Script Flow

1. Parse args, validate
2. **Device safety checks**: must be block device, not mounted, removable (or mmcblk), not root device, explicit "yes" confirmation
3. Download/cache Pi OS Lite 64-bit image (~450MB), SHA256 verify, decompress
4. `dd` image to SD card with progress
5. Mount boot + rootfs partitions (handle sdX1 vs mmcblk0p1 naming)
6. Inject: `ssh` file, `userconf.txt`, `firstrun.sh`, modify `cmdline.txt`
7. Inject: `/opt/marge-provision/marge-provision.sh` + `.service` on rootfs
8. Optional: WiFi NetworkManager `.nmconnection` on rootfs
9. Unmount, print next-steps instructions

## Safety

- Refuses non-block devices, mounted devices, non-removable drives, root filesystem
- Requires typing "yes" to confirm (bypass with `--yes`)
- Uses `lsblk` RM/HOTPLUG/TRAN flags + mmcblk detection
- trap + cleanup on exit

## Files to Modify

| File | Change |
|------|--------|
| `scripts/pi-setup-sd.sh` | **NEW** — main script (~250 LOC) |
| `docs/pi-preflight.md` | Add "Section 0: SD Card Setup" referencing the script |

## Style Reference
- Match `pi-deploy.sh` conventions: color codes, `set -euo pipefail`, section headers, `die()/info()/ok()` helpers

## End-to-End Flow After Implementation

```
sudo ./scripts/pi-setup-sd.sh /dev/sdX --wifi-ssid MyNet --wifi-pass secret
  --> insert SD, boot Pi, wait ~7 min (2 min boot + 5 min Docker install)
ssh pi@marge-pi.local 'docker --version'
  --> confirms provisioning complete
./scripts/pi-deploy.sh pi@marge-pi.local
  --> existing pipeline takes over
```

## Verification
1. Run with invalid device — should refuse
2. Run with `--help` — should print usage
3. Full write to real SD card, boot Pi, verify: SSH key auth works, hostname is `marge-pi`, Docker installed, `~/.marge-provisioned` exists
4. Then run `pi-deploy.sh` against it
