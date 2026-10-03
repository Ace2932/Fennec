#!/bin/bash
# Fennec tower thermal guard (Fennec#490): SEPARATE guards for the GPU and the CPU.
#   GPU >= GPU_LIMIT (90 C) for CHECKS (3) consecutive 30 s readings -> stop every active
#       fennec-train@ unit. Training is GPU work; this is the guard that protects it.
#   CPU >= CPU_LIMIT (95 C) for CHECKS readings -> one `CPU HOT` log line, NEVER a stop.
#       The Ryzen 9 9950X (Tctl rated 95 C) boosts toward its limit under any all-core load
#       by design. A shared 90 C limit logged 8 CPU-only THERMAL STOPs on 2026-10-02 with the
#       GPU at 28 C, caused by unrelated CPU jobs (Vulpes lab), not by training.
# dashboard/dashboard.py parses the `<date> gpu NC cpu NC NW` prefix and `THERMAL STOP` lines:
# keep both. Run from thermal-guard.service (Restart=always).
GPU_LIMIT=${THERMAL_GPU_LIMIT:-90}
CPU_LIMIT=${THERMAL_CPU_LIMIT:-95}
CHECKS=${THERMAL_CHECKS:-3}
LOG=${THERMAL_LOG:-$HOME/fennec-runs/thermal-guard.log}

read_gpu() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1; }
read_cpu() { sensors 2>/dev/null | awk '/Tctl/ {gsub(/[+°C]/,"",$2); print int($2)}' | head -1; }
read_pw()  { nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null | head -1; }
stop_training() {
  for u in $(systemctl --user list-units --state=active --no-legend 'fennec-train@*' | awk '{print $1}'); do
    systemctl --user stop "$u"
  done
}

gbad=0; cbad=0
check_once() {  # one reading; returns 10 when the GPU guard stopped training, else 0
  local g c p
  g=$(read_gpu); c=$(read_cpu); p=$(read_pw)
  # A missing or non-numeric reading counts as cool (the test errors to false), same as before.
  if [ "${g:-0}" -ge "$GPU_LIMIT" ] 2>/dev/null; then gbad=$((gbad+1)); else gbad=0; fi
  if [ "${c:-0}" -ge "$CPU_LIMIT" ] 2>/dev/null; then cbad=$((cbad+1)); else cbad=0; fi
  echo "$(date '+%F %T') gpu ${g}C cpu ${c}C ${p}W gpu_bad=$gbad cpu_bad=$cbad" >> "$LOG"
  if [ "$cbad" -ge "$CHECKS" ]; then
    echo "$(date '+%F %T') CPU HOT: cpu ${c}C >= ${CPU_LIMIT}C for $CHECKS checks -- logged only, training not stopped" >> "$LOG"
    cbad=0
  fi
  if [ "$gbad" -ge "$CHECKS" ]; then
    stop_training
    echo "$(date '+%F %T') THERMAL STOP: gpu ${g}C >= ${GPU_LIMIT}C for $CHECKS checks -- all fennec-train units stopped" >> "$LOG"
    gbad=0
    return 10
  fi
  return 0
}

# Sourced by the test with THERMAL_GUARD_LIB=1: define the functions, run nothing.
[ "${THERMAL_GUARD_LIB:-0}" = 1 ] && return 0 2>/dev/null

while true; do
  check_once
  [ $? -eq 10 ] && sleep "${THERMAL_STOP_PAUSE:-600}"
  sleep "${THERMAL_INTERVAL:-30}"
done
