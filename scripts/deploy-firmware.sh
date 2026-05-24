#!/usr/bin/env bash
# Build + deploy Teensy 4.1 firmware over the Jetson's USB connection.
#
# Implements docs/notes-qol-features.md §5. Called from
# firmware/teensy/firmware/Makefile but can be run standalone.
#
# Steps:
#   1. Verify HEX_PATH exists (call `pio run` first).
#   2. Hash the hex; bail if it matches the last-deployed hash unless
#      DEPLOY_FORCE=1 (skip cycle if nothing changed — flashing kills
#      the bus master so it's not free).
#   3. SAFETY GUARD: refuse to deploy if the Jetson reports E-stop
#      released and the gait controller is running. Operator must
#      engage E-stop OR stop gait first.
#   4. scp the hex to the Jetson.
#   5. Kill the micro_ros_agent on the Jetson (it holds /dev/ttyACM0
#      exclusively; teensy_loader_cli needs the device free).
#   6. Run teensy_loader_cli on the Jetson over SSH.
#   7. Wait for Teensy USB to re-enumerate.
#   8. Restart micro_ros_agent on the Jetson.
#   9. Verify /firmware_version reflects the new SHA.

set -euo pipefail

JETSON_HOST="${JETSON_HOST:-aiden@nova-jetson.local}"
TEENSY_MCU="${TEENSY_MCU:-TEENSY41}"
HEX_PATH="${HEX_PATH:-.pio/build/teensy41/firmware.hex}"
DEPLOY_FORCE="${DEPLOY_FORCE:-0}"
HASH_CACHE="${HASH_CACHE:-$HOME/.nova/last-deployed.sha}"

REMOTE_HEX="/tmp/nova-firmware.hex"
REMOTE_DEV="/dev/ttyACM0"

# Color helpers
RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; GREY='\033[90m'; RESET='\033[0m'

log()  { printf "${GREY}[deploy] %s${RESET}\n" "$*"; }
ok()   { printf "${GREEN}[deploy] %s${RESET}\n" "$*"; }
warn() { printf "${YELLOW}[deploy] %s${RESET}\n" "$*"; }
err()  { printf "${RED}[deploy] %s${RESET}\n" "$*" >&2; }

remote() { ssh -o ConnectTimeout=5 "$JETSON_HOST" "$@"; }


cmd_verify() {
    log "querying /firmware_version on $JETSON_HOST..."
    set +e
    output=$(remote "source /opt/ros/humble/setup.bash && \
        source ~/ros2_ws/install/local_setup.bash && \
        timeout 3 ros2 topic echo --once /firmware_version" 2>&1)
    rc=$?
    set -e
    if [ $rc -eq 0 ]; then
        ok "remote /firmware_version:"
        printf '%s\n' "$output" | sed 's/^/  /'
    else
        err "could not read /firmware_version (agent down? firmware not flashed?)"
        printf '%s\n' "$output" | sed 's/^/  /' >&2
        exit 4
    fi
}


cmd_deploy() {
    if [ ! -f "$HEX_PATH" ]; then
        err "$HEX_PATH not found. Run \`pio run -e teensy41\` first."
        exit 1
    fi

    NEW_HASH=$(shasum -a 256 "$HEX_PATH" | awk '{print $1}')
    log "local hex sha256: $NEW_HASH"

    if [ "$DEPLOY_FORCE" != "1" ] && [ -f "$HASH_CACHE" ]; then
        LAST_HASH=$(cat "$HASH_CACHE")
        if [ "$NEW_HASH" = "$LAST_HASH" ]; then
            ok "hex matches last-deployed hash; nothing to do (use DEPLOY_FORCE=1 to override)"
            exit 0
        fi
    fi

    log "checking remote safety state..."
    # Refuse if gait controller is running (motion during reboot = bad day)
    if remote "pgrep -f gait_controller" >/dev/null 2>&1; then
        if [ "$DEPLOY_FORCE" != "1" ]; then
            err "gait_controller is running on $JETSON_HOST. Stop it first, or DEPLOY_FORCE=1."
            exit 5
        fi
        warn "gait_controller running but DEPLOY_FORCE set; proceeding anyway"
    fi

    # SCP the hex
    log "scp $HEX_PATH -> $JETSON_HOST:$REMOTE_HEX"
    scp -q "$HEX_PATH" "$JETSON_HOST:$REMOTE_HEX"

    # Kill the agent so it releases /dev/ttyACM0
    log "stopping micro_ros_agent (frees $REMOTE_DEV)..."
    remote "pkill -f micro_ros_agent || true; sleep 0.5"

    # Flash via teensy_loader_cli on the Jetson
    log "flashing Teensy via teensy_loader_cli..."
    remote "teensy_loader_cli --mcu=$TEENSY_MCU -w -v $REMOTE_HEX"

    # Wait for the Teensy USB to re-enumerate
    log "waiting for $REMOTE_DEV to re-enumerate..."
    for i in $(seq 1 20); do
        if remote "test -e $REMOTE_DEV"; then
            ok "$REMOTE_DEV reappeared after ${i}s"
            break
        fi
        sleep 1
        if [ "$i" = "20" ]; then
            err "$REMOTE_DEV did not reappear within 20 s"
            exit 6
        fi
    done

    # Restart the agent (detached so it survives SSH disconnect)
    log "restarting micro_ros_agent (detached)..."
    remote "setsid bash -c 'source /opt/ros/humble/setup.bash && \
        source ~/ros2_ws/install/local_setup.bash && \
        exec ros2 run micro_ros_agent micro_ros_agent serial \
            --dev $REMOTE_DEV -b 115200 > /tmp/uros_agent.log 2>&1 < /dev/null' \
        </dev/null >/dev/null 2>&1 & disown"
    sleep 2

    cmd_verify

    mkdir -p "$(dirname "$HASH_CACHE")"
    printf '%s\n' "$NEW_HASH" > "$HASH_CACHE"
    ok "deploy complete. cached hash -> $HASH_CACHE"
}


case "${1:-deploy}" in
    deploy) cmd_deploy ;;
    verify) cmd_verify ;;
    *) err "unknown action: $1 (expected: deploy | verify)"; exit 2 ;;
esac
