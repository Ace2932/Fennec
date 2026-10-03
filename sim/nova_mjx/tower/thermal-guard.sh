#!/bin/bash
# Fennec tower thermal guard (Fennec#490): SEPARATE guards for the GPU and the CPU.
#   GPU >= GPU_LIMIT (90 C) for CHECKS (3) consecutive 30 s readings -> stop every active
#       fennec-train@ unit. Training is GPU work; this is the guard that protects it.
#   CPU >= CPU_LIMIT (95 C) for CHECKS readings -> one `CPU HOT` log line, NEVER a stop.
#       The Ryzen 9 9950X (Tctl rated 95 C) boosts toward its limit under any all-core load
#       by design. A shared 90 C limit logged 8 CPU-only THERMAL STOPs on 2026-10-02 with the
#       GPU at 28 C, caused by unrelated CPU jobs (Vulpes lab), not by training.
#   CPU >= IDLE_HOT_C (70 C) while the CPU is < IDLE_UTIL (3%, about one thread) busy, for
#       CHECKS readings -> `CPU IDLE HOT` log line + one tower-alert per day. It idles around 41 C,
#       so that is ~30 C over baseline with no workload: the cooler (fan, pump, paste). Never a
#       stop. Not 80 C at < 10%: measured 2026-10-02, four single-threaded jobs (6-9% of 32
#       threads) already read 70-74 C, because a few boosting cores heat Tctl on their own.
# dashboard/dashboard.py parses the `<date> gpu NC cpu NC NW` prefix and `THERMAL STOP` lines:
# keep both. Run from thermal-guard.service (Restart=always).
GPU_LIMIT=${THERMAL_GPU_LIMIT:-90}
CPU_LIMIT=${THERMAL_CPU_LIMIT:-95}
CHECKS=${THERMAL_CHECKS:-3}
LOG=${THERMAL_LOG:-$HOME/fennec-runs/thermal-guard.log}
IDLE_HOT_C=${THERMAL_IDLE_HOT_C:-70}
IDLE_UTIL=${THERMAL_IDLE_UTIL:-3}
ALERT=${THERMAL_ALERT_CMD:-tower-alert}

read_gpu() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1; }
read_cpu() { sensors 2>/dev/null | awk '/Tctl/ {gsub(/[+°C]/,"",$2); print int($2)}' | head -1; }
read_pw()  { nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null | head -1; }
# Sets UTIL = % of CPU time busy since the previous call ('' on the first call). Not called in
# $(...): it keeps the previous /proc/stat totals in globals between readings.
prev_total=""; prev_idle=""; UTIL=""
read_util() {
  local cpu user nice sys idle iow irq sirq steal rest total idl
  read -r cpu user nice sys idle iow irq sirq steal rest < /proc/stat
  total=$((user+nice+sys+idle+iow+irq+sirq+steal)); idl=$((idle+iow)); UTIL=""
  if [ -n "$prev_total" ] && [ "$total" -gt "$prev_total" ]; then
    UTIL=$(( 100 * ((total-prev_total) - (idl-prev_idle)) / (total-prev_total) ))
  fi
  prev_total=$total; prev_idle=$idl
}
stop_training() {
  for u in $(systemctl --user list-units --state=active --no-legend 'fennec-train@*' | awk '{print $1}'); do
    systemctl --user stop "$u"
  done
}

gbad=0; cbad=0; ibad=0; idle_alerted=""   # ponytail: the daily alert latch is in memory, a restart may re-alert once
check_once() {  # one reading; returns 10 when the GPU guard stopped training, else 0
  local g c p
  g=$(read_gpu); c=$(read_cpu); p=$(read_pw); read_util
  # A missing or non-numeric reading counts as cool (the test errors to false), same as before.
  if [ "${g:-0}" -ge "$GPU_LIMIT" ] 2>/dev/null; then gbad=$((gbad+1)); else gbad=0; fi
  if [ "${c:-0}" -ge "$CPU_LIMIT" ] 2>/dev/null; then cbad=$((cbad+1)); else cbad=0; fi
  if [ -n "$UTIL" ] && [ "$UTIL" -lt "$IDLE_UTIL" ] 2>/dev/null && [ "${c:-0}" -ge "$IDLE_HOT_C" ] 2>/dev/null; then
    ibad=$((ibad+1)); else ibad=0; fi
  echo "$(date '+%F %T') gpu ${g}C cpu ${c}C ${p}W gpu_bad=$gbad cpu_bad=$cbad util=${UTIL:-?}% idle_hot=$ibad" >> "$LOG"
  if [ "$ibad" -ge "$CHECKS" ]; then
    echo "$(date '+%F %T') CPU IDLE HOT: cpu ${c}C at ${UTIL}% load for $CHECKS checks -- check the cooler (fan, pump, paste)" >> "$LOG"
    if [ "$idle_alerted" != "$(date +%F)" ]; then
      $ALERT -t thermometer "tower CPU hot while idle" "cpu ${c}C at ${UTIL}% CPU load for $CHECKS checks (idle is ~41C) -- check the cooler: fan, pump, thermal paste" >/dev/null 2>&1
      idle_alerted=$(date +%F)
    fi
    ibad=0
  fi
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
