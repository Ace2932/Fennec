#!/usr/bin/python3
"""Fennec tower training dashboard: scan ~/fennec-runs, write ONE static index.html.

    /usr/bin/python3 dashboard.py [--runs ~/fennec-runs] [--out ~/fennec-dashboard/www]
    /usr/bin/python3 dashboard.py --selftest

Stdlib only, READ-ONLY on the runs tree (never imports the training code, never
touches the venv). Every file it reads may be missing, empty, or half-written by
a live run, so every read degrades to "no data" instead of raising.

Step accounting mirrors tower/fennec-train-status + ckpt_utils.stage_done_steps:
  - a stage's done steps = sum of every attempt's PROGRESS (run_*/PROGRESS, or the
    curriculum's stage*/PROGRESS), falling back to the largest checkpoint dir name.
  - eval_metrics.csv's `stage` column names the attempt (run_<ts>) or curriculum
    level (stage<i>_t<lvl>). Non-curriculum steps restart at 0 per attempt, so an
    attempt's x offset = PROGRESS of the attempts before it. Curriculum rows are
    already done_base+step, i.e. cumulative within their level, so the same rule
    (offset = PROGRESS of earlier labels) holds for both.
"""
import csv
import datetime
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import time

STALE_S = 15 * 60
GRAFANA = "http://100.118.31.63:3000/d/tower-metrics/tower"
THERMAL_LIMIT = 90
HEALTH_POINTS = 720          # thermal-guard.log is 1 line / 30 s: keep the last 24 h, thinned
FEET = ("FL", "FR", "RL", "RR")


# ---------------------------------------------------------------- readers ----

def read_json(p):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except (OSError, ValueError):
        return None


def progress_steps(d):
    """ckpt_utils.stage_done_steps, stdlib copy: PROGRESS steps, else max ckpt dir."""
    rec = read_json(pathlib.Path(d) / "PROGRESS")
    if isinstance(rec, dict) and isinstance(rec.get("steps"), int):
        return rec["steps"]
    if isinstance(rec, (int, float)):
        return int(rec)
    try:
        return max([int(e.name) for e in os.scandir(d) if e.is_dir() and e.name.isdigit()] or [0])
    except OSError:
        return 0


def attempt_dirs(sdir):
    """Every attempt/level dir of a stage: run_* (plain) or stage* (curriculum)."""
    try:
        return sorted(p for p in sdir.iterdir()
                      if p.is_dir() and (p.name.startswith("run_") or p.name.startswith("stage")))
    except OSError:
        return []


def stage_done(sdir):
    return sum(progress_steps(d) for d in attempt_dirs(sdir))


def mtime(p):
    try:
        return p.stat().st_mtime
    except OSError:
        return None


def train_log(sdir):
    rows = []
    try:
        for r in csv.reader((sdir / "train_log.csv").open()):
            try:
                rows.append((float(r[0]), int(r[1]), float(r[2])))
            except (ValueError, IndexError):
                pass      # half-written tail line
    except OSError:
        pass
    return rows


def f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def stage_curves(sdir, base):
    """Per-eval points of one plan stage, x = cumulative steps across the variant."""
    try:
        rows = list(csv.DictReader((sdir / "eval_metrics.csv").open()))
    except OSError:
        return []
    banked, order = {}, []
    for r in rows:
        lab = r.get("stage") or ""
        if lab not in banked:
            order.append(lab)
            banked[lab] = progress_steps(sdir / lab) if lab else 0
    offset, acc = {}, 0
    for lab in order:
        offset[lab] = acc
        acc += banked[lab]
    pts = []
    for r in rows:
        step, L = f(r.get("step")), f(r.get("avg_episode_length"))
        if step is None or L is None:
            continue      # half-written tail row
        per = (lambda k: (f(r.get(k)) / L) if (L and f(r.get(k)) is not None) else None)
        pts.append({
            "x": base + offset[r.get("stage") or ""] + step,
            "reward": f(r.get("episode_reward")),
            "speed": per("episode_fwd_speed"),
            "len": L,
            "air": [per(f"episode_airT_{ft}") for ft in FEET],
        })
    return pts


THERMAL_RE = re.compile(r"^(\S+ \S+) gpu (\d+)C cpu (\d+)C ([\d.]+)W")


def thermal_log(path):
    """thermal-guard.log -> {t, gpu, cpu, w} points (last 24 h, thinned) + THERMAL STOP times."""
    try:
        lines = path.read_text(errors="replace").splitlines()[-2880:]
    except OSError:
        return {"pts": [], "stops": []}
    pts, stops = [], []
    for l in lines:
        m = THERMAL_RE.match(l)
        if m:
            pts.append({"t": m.group(1), "gpu": int(m.group(2)), "cpu": int(m.group(3)),
                        "w": float(m.group(4))})
        elif "THERMAL STOP" in l:
            stops.append(l[:19])
    k = max(1, len(pts) // HEALTH_POINTS)
    return {"pts": pts[::k], "stops": stops}


def media(d):
    """render_rollout.py outputs: {stem: {"mp4","png": bool, "json": dict|None, "err": str|None}}."""
    out = {}
    try:
        files = list(d.iterdir())
    except OSError:
        return out
    for p in files:
        if p.name.startswith(".") or p.suffix not in (".mp4", ".png", ".json", ".err"):
            continue
        e = out.setdefault(p.stem, {"mp4": False, "png": False, "json": None, "err": None})
        if p.suffix == ".json":
            e["json"] = read_json(p)
        elif p.suffix == ".err":
            try:
                e["err"] = p.read_text(errors="replace").strip().splitlines()[-1:][0][:300]
            except (OSError, IndexError):
                e["err"] = "render failed"
        else:
            e[p.suffix[1:]] = True
    return out


def iso(t):
    return None if t is None else \
        datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def status(data):
    """status.json, schema 1: a stable contract read by the Grafana tower hub. Don't rename."""
    runs = []
    for q in data["queues"]:
        for v in q["variants"]:
            st = v["stages"]
            cur = next((s for s in st if not s["DONE"]), st[-1] if st else None)
            runs.append({
                "run": q["name"], "variant": v["name"],
                "stage": cur["name"] if cur else None,
                "steps_done": int(cur["done"]) if cur else None,
                "steps_planned": int(cur["timesteps"]) if cur else None,
                "last_eval_reward": cur["last_reward"] if cur else None,
                "running": bool(q["state"] == "active" and q.get("plan_variant") == v["name"]),
                "last_update": iso(v["last_update"]),
                "done": bool(st) and all(s["DONE"] for s in st)})
    return {"schema": 1, "generated": iso(data["generated"]), "runs": runs}


# ------------------------------------------------------------------ scan -----

def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def gpu():
    out = sh("nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,"
             "temperature.gpu,power.draw", "--format=csv,noheader,nounits")
    v = [f(x) for x in out.split("\n")[0].split(",")] if out else []
    return dict(zip(("util", "mem_used", "mem_total", "temp", "power"), v)) if len(v) == 5 else None


def service_log(path):
    """Last [plan] line, and the last Traceback block if it comes after it."""
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return {"plan": None, "error": None, "n_tb": 0}
    plan_i = max((i for i, l in enumerate(lines) if l.startswith("[plan]")), default=-1)
    tbs = [i for i, l in enumerate(lines) if l.startswith("Traceback")]
    err = None
    if tbs and tbs[-1] > plan_i:
        blk = [lines[tbs[-1]]]
        for l in lines[tbs[-1] + 1: tbs[-1] + 80]:
            blk.append(l)
            if l and not l[0].isspace():   # the exception line ends the block
                break
        err = "\n".join(blk)
    return {"plan": lines[plan_i] if plan_i >= 0 else None, "error": err, "n_tb": len(tbs)}


def scan_variant(vdir, now):
    plan = read_json(vdir / "plan.json") or {}
    stages, curves, bounds, base = [], [], [], 0
    rate, last_row_t, left_total, mtimes = None, None, 0, []
    for st in plan.get("stages", []):
        name, ts = st.get("name", "?"), int(st.get("timesteps", 0) or 0)
        sdir = vdir / name
        done, is_done = stage_done(sdir), (sdir / "DONE").exists()
        rows = train_log(sdir)
        mtimes += [mtime(sdir / "train_log.csv")] + [mtime(a / "PROGRESS") for a in attempt_dirs(sdir)]
        if rows:
            last_row_t = max(last_row_t or 0, rows[-1][0])
        stage_rate = None
        if len(rows) >= 2 and not is_done:
            (t0, s0, _), (t1, s1, _) = rows[-2], rows[-1]
            if t1 > t0 and s1 > s0:
                stage_rate = rate = (s1 - s0) / (t1 - t0)
        left = 0 if is_done else max(0, ts - done)
        left_total += left
        pts = stage_curves(sdir, base)
        curves += pts
        if base:
            bounds.append({"x": base, "name": name})
        stages.append({"name": name, "timesteps": ts, "done": done, "DONE": is_done,
                       "left": left, "rate": stage_rate,
                       "last_reward": rows[-1][2] if rows else None})
        base += max(done, ts if is_done else 0, max((p["x"] for p in pts), default=base) - base)
    evals = {}
    for p in sorted(vdir.glob("eval_*.json")):
        j = read_json(p)
        if isinstance(j, dict):
            evals[p.stem[5:]] = j
    return {"name": vdir.name, "stages": stages, "curves": curves, "bounds": bounds,
            "evals": evals, "rate": rate, "left": left_total, "last_row_t": last_row_t,
            "last_update": max((t for t in mtimes if t), default=None),
            "has_data": bool(curves or evals or any(s["done"] for s in stages))}


def scan(runs, media_dir=None):
    now = time.time()
    queues = []
    for q in sorted(p for p in runs.iterdir() if p.is_dir()) if runs.is_dir() else []:
        unit = f"fennec-train@{q.name}"
        state = sh("systemctl", "--user", "is-active", unit) or "unknown"
        restarts = sh("systemctl", "--user", "show", "-p", "NRestarts", "--value", unit)
        log = service_log(q / "service.log")
        variants = [scan_variant(v, now) for v in sorted(q.iterdir())
                    if v.is_dir() and (v / "plan.json").exists()]
        running = None
        m = re.search(r"/fennec-runs/[^/]+/([^/]+)/([^/\s]+)", log["plan"] or "")
        if state == "active" and m and "training" in (log["plan"] or ""):
            v = next((x for x in variants if x["name"] == m.group(1)), None)
            s = next((x for x in (v or {}).get("stages", []) if x["name"] == m.group(2)), None)
            if v and s:
                r = s["rate"] or v["rate"]
                running = {"variant": v["name"], "stage": s["name"], "done": s["done"],
                           "timesteps": s["timesteps"], "rate": r,
                           "eta_stage": s["left"] / r if r else None,
                           "eta_variant": v["left"] / r if r else None}
        last_t = max((v["last_row_t"] or 0 for v in variants), default=0) or None
        stale = bool(state == "active" and last_t and now - last_t > STALE_S)
        queues.append({"name": q.name, "state": state, "restarts": restarts, "log": log,
                       "plan_variant": m.group(1) if (m and state == "active") else None,
                       "running": running, "variants": variants, "last_row_t": last_t,
                       "stale": stale})
    return {"generated": now, "gpu": gpu(), "queues": queues,
            "health": thermal_log(runs / "thermal-guard.log"),
            "media": media(media_dir) if media_dir else {}}


# ------------------------------------------------------------------ html -----

def fmt(x, nd=1, suf=""):
    return "–" if x is None else f"{x:.{nd}f}{suf}"


def hrs(s):
    return "–" if s is None else (f"{s/3600:.1f} h" if s >= 3600 else f"{s/60:.0f} min")


def cls_speed(v):
    return "" if v is None else ("good" if v >= 90 else "bad" if v < 50 else "warn")


def cls_air(v):
    # ~1 = leg carried in the air, ~0 = dragged: both are a broken gait
    return "" if v is None else ("bad" if v > 0.9 or v < 0.05 else "")


def guard_cells(m):
    """Servo-protection columns; '–' in evals from code older than the field."""
    trip, slew, g = f(m.get("servos_tripped_end")), f(m.get("slew_clip_frac")), f(m.get("guard_trip_pct"))
    ms = [f(m.get(f"guard_run_ms_{k}")) for k in ("p50", "p99", "max")]
    return [f'<td class="{"bad" if trip else ""} num">{fmt(trip, 3)}</td>',
            f'<td class="num">{fmt(None if slew is None else 100 * slew)}</td>',
            f'<td class="{"bad" if g else ""} num">{fmt(g)}</td>',
            f'<td class="num">{"–" if ms[0] is None else "/".join(fmt(x, 0) for x in ms)}</td>']


def score_rows(data):
    out = []
    for q in data["queues"]:
        for v in q["variants"]:
            for ev, j in v["evals"].items():
                cells = [f"<td>{html.escape(q['name'])}/{html.escape(v['name'])}</td>",
                         f"<td>{html.escape(ev)}</td>"]
                for mode in ("fwd", "mixed"):
                    m = j.get(mode) if isinstance(j.get(mode), dict) else {}
                    spd, fall = f(m.get("spd_pct")), f(m.get("fall"))
                    fallp = None if fall is None else 100 * fall
                    air = m.get("air") if isinstance(m.get("air"), list) else []
                    airs = " ".join(f'<span class="{cls_air(f(a))}">{fmt(f(a), 2)}</span>'
                                    for a in air) or "–"
                    cells += [f'<td class="{cls_speed(spd)} num">{fmt(spd)}</td>',
                              f'<td class="{"bad" if fallp and fallp > 5 else ""} num">{fmt(fallp)}</td>',
                              f'<td class="num">{fmt(f(m.get("swing_cm")), 2)}</td>',
                              f'<td class="num air">{airs}</td>',
                              f'<td class="num">{fmt(f(m.get("cot")), 2)}</td>'] + guard_cells(m)
                out.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(out)


COURSE_TXT = {"flat": "flat, fwd 0.25 m/s", "curb": "3 cm one-cell ramp at x = 0.4 m, fwd 0.25 m/s"}


def media_html(data, vid):
    """Rollout video + gait diagram per course, from render_rollout.py's cache."""
    out = []
    for course, txt in COURSE_TXT.items():
        e = data["media"].get(f"{vid}__{course}")
        if not e:
            continue
        src = html.escape(f"media/{vid}__{course}")
        if e["err"] and not e["mp4"]:
            out.append(f'<div class="mcell"><b>{course}</b> <span class="bad">render failed</span>'
                       f'<div class="mono small">{html.escape(e["err"])}</div></div>')
            continue
        j = e["json"] or {}
        fell = j.get("fell_step")
        info = (f'dx {fmt(f(j.get("x_travel_m")), 2)} m · '
                f'{"<span class=bad>fell at step " + str(fell) + "</span>" if fell else "no fall"} · '
                f'≥90% duty {fmt(f(j.get("guard_cells_pct")))}% of joint-steps') if j else ""
        out.append(f'<div class="mcell"><b>{course}</b> <span class="muted small">{txt}</span>'
                   # #t=0.1: with preload=metadata, browsers then paint a frame instead of black
                   + (f'<video src="{src}.mp4#t=0.1" controls muted loop playsinline preload="metadata"></video>'
                      if e["mp4"] else "")
                   + (f'<img src="{src}.png" alt="gait diagram {course}" loading="lazy">' if e["png"] else "")
                   + f'<div class="small">{info}</div></div>')
    return f'<div class="media">{"".join(out)}</div>' if out else ""


def health_html(h):
    stops = "".join(f'<span class="pill bad">THERMAL STOP {html.escape(t)}</span> ' for t in h["stops"])
    chart = '<div class="hchart"><canvas id="health"></canvas></div>' if h["pts"] else \
        '<div class="muted">no thermal-guard.log data</div>'
    return (f'<div class="card"><b>Tower health</b> <span class="muted small">thermal-guard.log, last 24 h · '
            f'guard stops training at {THERMAL_LIMIT}°C for 3 checks · history: '
            f'<a id="grafana" href="{GRAFANA}">Grafana tower dashboard</a></span> {stops}{chart}</div>'
            # same host as this page, so an ssh tunnel (localhost:8765 + :3000) stays on the tunnel
            "<script>document.getElementById('grafana').href = location.protocol + '//' + "
            "location.hostname + ':3000/d/tower-metrics/tower'</script>")


def render(data):
    now = data["generated"]
    g = data["gpu"]
    gpu_html = ("GPU: unavailable" if not g else
                f"GPU <b>{fmt(g['util'], 0)}%</b> · VRAM <b>{fmt(g['mem_used']/1024 if g['mem_used'] else None)}"
                f"/{fmt(g['mem_total']/1024 if g['mem_total'] else None)} GB</b> · "
                f"<b>{fmt(g['temp'], 0)}°C</b> · <b>{fmt(g['power'], 0)} W</b>")
    qcards, errs, vsecs = [], [], []
    for q in data["queues"]:
        r = q["running"]
        run_html = (f"<div>running <b>{html.escape(r['variant'])}/{html.escape(r['stage'])}</b> "
                    f"{r['done']:,}/{r['timesteps']:,} · {fmt((r['rate'] or 0)*3600/1e6, 0)}M steps/h · "
                    f"stage ETA <b>{hrs(r['eta_stage'])}</b> · variant ETA {hrs(r['eta_variant'])}</div>"
                    if r else "")
        stale = (f'<div class="bad">STALE: last train_log row {hrs(now - q["last_row_t"])} ago '
                 f'while unit active</div>' if q["stale"] else "")
        last = f"last row {hrs(now - q['last_row_t'])} ago" if q["last_row_t"] else "no train_log rows"
        qcards.append(
            f'<div class="card"><div><b>{html.escape(q["name"])}</b> '
            f'<span class="pill {"good" if q["state"] == "active" else ""}">{html.escape(q["state"])}</span> '
            f'restarts {html.escape(q["restarts"] or "–")} · {last}</div>{run_html}{stale}'
            f'<div class="mono small">{html.escape(q["log"]["plan"] or "no [plan] line")}</div></div>')
        if q["log"]["error"]:
            errs.append(f"<h3>{html.escape(q['name'])}/service.log</h3>"
                        f"<pre>{html.escape(q['log']['error'])}</pre>")
        for v in q["variants"]:
            vid = f"{q['name']}__{v['name']}"
            st = " · ".join(
                f"{html.escape(s['name'])} " + ("DONE" if s["DONE"] else f"{s['done']:,}/{s['timesteps']:,}")
                for s in v["stages"])
            body = (f'<div class="charts" data-v="{vid}"></div>' if v["curves"]
                    else '<div class="muted">no training data yet</div>') + media_html(data, vid)
            vsecs.append(f'<details class="variant" {"open" if v["curves"] else ""}>'
                         f'<summary><b>{html.escape(q["name"])}/{html.escape(v["name"])}</b> '
                         f'<span class="muted small">{st}</span></summary>{body}</details>')
    n_old = sum(q["log"]["n_tb"] for q in data["queues"]) - len(errs)
    err_html = ("".join(errs) if errs else
                f'<div class="muted">No traceback since the last [plan] line'
                f'{f" ({n_old} older, superseded)" if n_old > 0 else ""}.</div>')
    series = {f"{q['name']}__{v['name']}": {"c": v["curves"], "b": v["bounds"]}
              for q in data["queues"] for v in q["variants"] if v["curves"]}
    series["_health"] = {**data["health"], "limit": THERMAL_LIMIT}
    blob = json.dumps(series, separators=(",", ":")).replace("</", "<\\/")
    gen = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(now))
    hdr = "".join(f"<th>{h}</th>" for h in ("spd%", "fall%", "swing cm", "air", "CoT",
                                              "trip", "slew%", "guard%", "guard ms"))
    return TEMPLATE.format(gen=gen, gpu=gpu_html, queues="".join(qcards), errors=err_html,
                           health=health_html(data["health"]), hdr=hdr,
                           scores=score_rows(data) or '<tr><td colspan="12" class="muted">no evals</td></tr>',
                           variants="".join(vsecs), blob=blob)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="120">
<title>Fennec Training</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{{--bg:#f7f7f5;--fg:#1d1d1b;--muted:#6b6b66;--card:#fff;--line:#deded8;
--good:#1f7a3a;--goodbg:#dff3e5;--bad:#b3261e;--badbg:#fbe1de;--warnbg:#fff1c9;
--s1:#2f6fdb;--s2:#d9480f;--s3:#2b8a3e;--s4:#9c36b5}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141413;--fg:#ececea;--muted:#9a9a94;--card:#1e1e1c;
--line:#33332f;--good:#6fd28b;--goodbg:#173222;--bad:#ff8a80;--badbg:#3a1a17;--warnbg:#3a3113;
--s1:#6ea0ff;--s2:#ff8f5a;--s3:#63d47d;--s4:#d38cf0}}}}
*{{box-sizing:border-box}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:16px;margin:24px 0 8px}} h3{{font-size:14px;margin:8px 0}}
.muted{{color:var(--muted)}} .small{{font-size:12px}} .mono,pre{{font-family:ui-monospace,Menlo,monospace}}
pre{{white-space:pre-wrap;word-break:break-word;font-size:12px;background:var(--badbg);padding:8px;border-radius:6px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;margin:8px 0}}
.pill{{padding:1px 6px;border-radius:9px;border:1px solid var(--line)}}
.good{{background:var(--goodbg);color:var(--good)}} .bad{{background:var(--badbg);color:var(--bad)}}
.warn{{background:var(--warnbg)}}
.tbl{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}
th,td{{padding:4px 6px;border-bottom:1px solid var(--line);white-space:nowrap}}
th{{position:sticky;top:0;background:var(--card);text-align:left}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
td.air span{{padding:0 2px;border-radius:3px}}
details.variant{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:8px 0}}
summary{{cursor:pointer}}
.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin-top:8px}}
.charts div{{position:relative;height:200px}}
.hchart{{position:relative;height:160px;margin-top:6px}}
a{{color:var(--s1)}}
.media{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px;margin-top:10px}}
.mcell video,.mcell img{{display:block;width:100%;max-width:640px;height:auto;margin-top:4px;border-radius:6px;background:#000}}
.mcell img{{background:#fff}}
</style></head><body>
<h1>Fennec training · tower</h1>
<div class="muted small">generated {gen} · page reloads every 2 min · read-only</div>
<div class="card">{gpu}</div>
{health}
{queues}
<h2>Latest errors</h2>{errors}
<h2>Scorecard (eval_*.json)</h2>
<div class="muted small">speed ≥90% green, &lt;50% red · fall &gt;5% red · air per foot FL FR RL RR: &gt;0.9 carried / &lt;0.05 dragged in red ·
trip = servos overload-tripped per robot at episode end · slew% = joint targets clipped by the firmware slew limit ·
guard% = episodes where the firmware stall guard (≥90% duty for 100 ms) trips, red if &gt;0 · guard ms = longest ≥90% run p50/p99/max · – = field not in that eval</div>
<div class="tbl"><table><thead>
<tr><th rowspan="2">variant</th><th rowspan="2">eval</th><th colspan="9">fwd</th><th colspan="9">mixed</th></tr>
<tr>{hdr}{hdr}</tr>
</thead><tbody>{scores}</tbody></table></div>
<h2>Training curves</h2>
<div class="muted small">x = cumulative steps across stages and resumes; dashed line = stage boundary. Speed and air are per-step means (episode sum / episode length).</div>
{variants}
<script id="data" type="application/json">{blob}</script>
<script>
(function(){{
if(!window.Chart) return;
const D=JSON.parse(document.getElementById('data').textContent);
const css=getComputedStyle(document.documentElement), c=n=>css.getPropertyValue(n).trim();
Chart.defaults.color=c('--muted'); Chart.defaults.borderColor=c('--line');
const bounds={{id:'bounds',afterDraw(ch,_,o){{const x=ch.scales.x,a=ch.chartArea,k=ch.ctx;
 (o.b||[]).forEach(b=>{{const px=x.getPixelForValue(b.x);k.save();k.setLineDash([4,4]);k.strokeStyle=c('--muted');
 k.beginPath();k.moveTo(px,a.top);k.lineTo(px,a.bottom);k.stroke();k.fillStyle=c('--muted');k.fillText(b.name,px+3,a.top+10);k.restore();}});}}}};
const S=[c('--s1'),c('--s2'),c('--s3'),c('--s4')];
const plots=[['eval reward',p=>[p.reward]],['fwd speed (m/s per step)',p=>[p.speed]],
 ['air fraction FL/FR/RL/RR',p=>p.air,['FL','FR','RL','RR']],['episode length',p=>[p.len]]];
document.querySelectorAll('.charts').forEach(el=>{{const v=D[el.dataset.v]; if(!v) return;
 plots.forEach(([t,fn,names])=>{{const box=document.createElement('div'),cv=document.createElement('canvas');
  box.appendChild(cv);el.appendChild(box);const n=fn(v.c[0]).length;
  new Chart(cv,{{type:'line',plugins:[bounds],data:{{datasets:[...Array(n).keys()].map(i=>({{label:names?names[i]:t,
   data:v.c.map(p=>({{x:p.x,y:fn(p)[i]}})),borderColor:S[i],backgroundColor:S[i],pointRadius:1.5,borderWidth:1.5}}))}},
   options:{{animation:false,maintainAspectRatio:false,parsing:true,
   plugins:{{bounds:{{b:v.b}},legend:{{display:!!names,labels:{{boxWidth:10}}}},title:{{display:true,text:t}}}},
   scales:{{x:{{type:'linear',ticks:{{callback:x=>(x/1e6)+'M'}}}}}}}}}});}});}});
const H=D._health, hc=document.getElementById('health');
if(H&&hc&&H.pts.length){{const lab=H.pts.map(p=>p.t.slice(11,16)), ds=(l,k,col,ax)=>({{label:l,data:H.pts.map(k),
  borderColor:col,backgroundColor:col,pointRadius:0,borderWidth:1.5,yAxisID:ax}});
 const stops={{id:'stops',afterDraw(ch){{const x=ch.scales.x,a=ch.chartArea,k=ch.ctx;
  H.stops.forEach(s=>{{let i=H.pts.findIndex(p=>p.t>=s);if(i<0)i=H.pts.length-1;const px=x.getPixelForValue(i);
  k.save();k.strokeStyle=c('--bad');k.lineWidth=2;k.beginPath();k.moveTo(px,a.top);k.lineTo(px,a.bottom);k.stroke();
  k.fillStyle=c('--bad');k.fillText('THERMAL STOP',px+3,a.top+10);k.restore();}});}}}};
 new Chart(hc,{{type:'line',plugins:[stops],data:{{labels:lab,datasets:[ds('GPU °C',p=>p.gpu,S[0],'t'),ds('CPU °C',p=>p.cpu,S[1],'t'),
  ds('GPU W',p=>p.w,S[2],'w'),{{...ds(H.limit+' °C limit',p=>H.limit,c('--bad'),'t'),borderDash:[5,4],borderWidth:1}}]}},
  options:{{animation:false,maintainAspectRatio:false,plugins:{{legend:{{labels:{{boxWidth:10}}}}}},
  scales:{{x:{{ticks:{{maxTicksLimit:12}}}},t:{{position:'left',suggestedMin:30,suggestedMax:95,title:{{display:true,text:'°C'}}}},
  w:{{position:'right',grid:{{drawOnChartArea:false}},title:{{display:true,text:'W'}}}}}}}}}});}}
}})();
</script></body></html>
"""


# --------------------------------------------------------------- main --------

def write_atomic(path, text):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)       # the web server never serves a half-written page


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        runs = pathlib.Path(td) / "runs"
        v = runs / "q" / "V"
        (v / "s1" / "run_1").mkdir(parents=True)
        (v / "s1" / "run_2").mkdir(parents=True)
        (runs / "q" / "EMPTY").mkdir()
        (runs / "q" / "EMPTY" / "plan.json").write_text('{"stages":[{"name":"s1","timesteps":10}]}')
        (v / "plan.json").write_text('{"stages":[{"name":"s1","timesteps":300},{"name":"s2","timesteps":100}]}')
        (v / "s1" / "run_1" / "PROGRESS").write_text('{"steps": 100}')
        (v / "s1" / "run_2" / "PROGRESS").write_text('{"steps": 200}')
        (v / "s1" / "DONE").write_text("300\n")
        hdr = "stage,step,avg_episode_length,episode_reward,episode_fwd_speed," + \
              ",".join(f"episode_airT_{x}" for x in FEET)
        (v / "s1" / "eval_metrics.csv").write_text(
            hdr + "\nrun_1,0,100,1,5,50,50,0,100\nrun_1,150,100,2,5,50,50,0,100\n"
                  "run_2,0,100,3,5,50,50,0,100\nrun_2,200,100,4,5,50,50,0,100\nrun_2,2")
        (v / "s2").mkdir()
        (v / "s2" / "train_log.csv").write_text("1,0,1\n")      # partial stage
        (v / "eval_x.json").write_text('{"fwd":{"spd_pct":107.7,"fall":0.1,"air":[1,0,0.3,0.3]}}')
        (runs / "q" / "service.log").write_text(
            "Traceback (most recent call last):\n  File x\nValueError: old\n[plan] s1: done\n")
        (runs / "thermal-guard.log").write_text(
            "2026-09-25 20:21:29 gpu 76C cpu 62C 301.41W bad=0\n"
            "2026-09-25 20:21:59 gpu 91C cpu 62C 305.00W bad=3\n"
            "2026-09-25 20:21:59 THERMAL STOP: all fennec-train units stopped\ngarbage\n")
        med = pathlib.Path(td) / "media"
        med.mkdir()
        (med / "q__V__flat.mp4").write_text("v")
        (med / "q__V__flat.png").write_text("p")
        (med / "q__V__flat.json").write_text('{"x_travel_m": 1.5, "fell_step": null, "guard_cells_pct": 3}')
        (med / "q__V__curb.err").write_text("Traceback\nValueError: obs size 105 != 111\n")
        (v / "eval_y.json").write_text('{"fwd":{"spd_pct":50,"guard_trip_pct":12.5,"guard_run_ms_p50":20,'
                                       '"guard_run_ms_p99":140,"guard_run_ms_max":200,"slew_clip_frac":0.4}}')
        d = scan(runs, med)
        h = d["health"]
        assert [p["gpu"] for p in h["pts"]] == [76, 91] and h["pts"][0]["w"] == 301.41, h
        assert h["stops"] == ["2026-09-25 20:21:59"], h["stops"]
        st = status(d)
        assert st["schema"] == 1 and isinstance(st["generated"], str) and st["generated"][10] == "T"
        types = {"run": str, "variant": str, "stage": (str, type(None)), "steps_done": (int, type(None)),
                 "steps_planned": (int, type(None)), "last_eval_reward": (float, type(None)),
                 "running": bool, "last_update": (str, type(None)), "done": bool}
        for r in st["runs"]:
            assert set(r) == set(types), r
            for k, t in types.items():
                assert isinstance(r[k], t), (k, r[k])
        sv = next(r for r in st["runs"] if r["variant"] == "V")
        # s1 DONE -> current stage is the partial s2 (its one train_log row, reward 1.0)
        assert (sv["stage"], sv["steps_planned"], sv["last_eval_reward"], sv["done"], sv["running"]) == \
            ("s2", 100, 1.0, False, False), sv
        assert sv["last_update"] is not None
        vv = next(x for x in d["queues"][0]["variants"] if x["name"] == "V")
        xs = [p["x"] for p in vv["curves"]]
        # run_2 starts at run_1's BANKED 100 (not its last logged 150); half row dropped
        assert xs == [0, 150, 100, 300], xs
        assert vv["bounds"] == [{"x": 300, "name": "s2"}], vv["bounds"]
        assert vv["curves"][0]["speed"] == 0.05 and vv["curves"][0]["air"] == [0.5, 0.5, 0.0, 1.0]
        assert d["queues"][0]["log"]["error"] is None          # traceback older than [plan]
        page = render(d)
        assert "107.7" in page and 'class="good num"' in page and 'class="bad num"' in page
        assert "no training data yet" in page                   # EMPTY variant
        assert '<video src="media/q__V__flat.mp4#t=0.1"' in page and 'src="media/q__V__flat.png"' in page
        assert "obs size 105 != 111" in page and "render failed" in page
        assert '<td class="bad num">12.5</td>' in page and "20/140/200" in page and "40.0" in page
        assert "THERMAL STOP 2026-09-25 20:21:59" in page
        assert f'<a id="grafana" href="{GRAFANA}"' in page and "location.hostname + ':3000/d/tower-metrics/tower'" in page
        # every other link is relative so the page works through an ssh tunnel
        assert set(re.findall(r'(?:src|href)="(https?://[^/"]+)', page)) <= \
            {"http://100.118.31.63:3000", "https://cdnjs.cloudflare.com"}, re.findall(r'(?:src|href)="(https?://[^"]+)', page)
        (runs / "q" / "service.log").write_text("[plan] s1\nTraceback (x)\n  File y\nKeyError: 'z'\n")
        assert "KeyError" in service_log(runs / "q" / "service.log")["error"]
    print("selftest OK")


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = dict(zip(argv[::2], argv[1::2]))
    runs = pathlib.Path(args.get("--runs", "~/fennec-runs")).expanduser()
    out = pathlib.Path(args.get("--out", "~/fennec-dashboard/www")).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    data = scan(runs, out / "media")
    write_atomic(out / "index.html", render(data))
    write_atomic(out / "status.json", json.dumps(status(data), indent=1))
    print(f"wrote {out / 'index.html'} and status.json")


if __name__ == "__main__":
    main(sys.argv[1:])
