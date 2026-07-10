#!/usr/bin/env python3
"""Generate a self-contained interactive robot viewer (ROM sliders + explode).

Replicates the EXACT kinematic chain from chassis/preview_assembly.py +
check_fit.py so the articulated poses match the fit gates. Embeds
grid-decimated leg_v6 meshes as base64 Float32 triangle-soup; hand-written
WebGL in the HTML (no external libs -> works as a local file, any browser).

Output: hardware/cad/viewer/robot_viewer.html
"""
import base64
import json
import struct

import numpy as np
import trimesh

CAD = "/Users/afox/codebases/NOVA/proj/hardware/cad"
ORIG = "/Users/afox/codebases/NOVA/original_body_files"
OUT = f"{CAD}/viewer/robot_viewer.html"

HIP_FA, HIP_LAT, HIP_Z = 141.2, 39.05, 38.05


def T(v):
    return trimesh.transformations.translation_matrix(v)


def R(deg, axis, point=None):
    return trimesh.transformations.rotation_matrix(np.radians(deg), axis, point)


# ---- mesh -> decimated triangle-soup positions (base64 Float32) ----------
def load_soup(path, grid=0.8):
    m = trimesh.load(path)
    v, f = m.vertices, m.faces
    q = np.round(v / grid).astype(np.int64)
    uniq, inv = np.unique(q, axis=0, return_inverse=True)
    nv = np.zeros((len(uniq), 3))
    cnt = np.zeros(len(uniq))
    np.add.at(nv, inv, v)
    np.add.at(cnt, inv, 1)
    nv /= cnt[:, None]
    nf = inv[f]
    good = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
    nf = nf[good]
    tris = nv[nf].reshape(-1, 3).astype(np.float32)   # (3*Nface, 3)
    return base64.b64encode(tris.tobytes()).decode(), len(nf)


def mat_list(M):
    # column-major for WebGL
    return [float(x) for x in M.T.flatten()]


# ---- unique meshes -------------------------------------------------------
CH = f"{CAD}/chassis"
MESHES = {
    "coax_R": f"{CAD}/leg_v6/coax_R.stl",
    "femur_R": f"{CAD}/leg_v6/femur_R.stl",
    "tibia_R": f"{CAD}/leg_v6/tibia_R.stl",
    "knee_arm": f"{CAD}/leg_v6/knee_arm.stl",
    "knee_bump": f"{CAD}/leg_v6/knee_bumper.stl",   # TPU collapse guard (rides tibia)
    "shoulder": f"{CAD}/leg_v6/shoulder.stl",
    "splate_R": f"{CAD}/leg_v6/shoulder_plate.stl",
    "splate_L": f"{CAD}/leg_v6/shoulder_plate_L.stl",
    "shoe": f"{ORIG}/SM3_Foot.stl",
    "trunk": f"{ORIG}/SM3_Frame_ChassisTrunk.stl",
    "riser": f"{CH}/riser_bay.stl",
    "battery": f"{CH}/battery_pocket.stl",
    "floor": f"{CH}/floor_plate.stl",
    "skid": f"{CH}/skid_rail.stl",
    # --- forward HEAD re-arch (2026-07) + sensors ---
    "head": f"{CH}/head.stl",
    "ear_R": f"{CH}/head_ear.stl",
    "ear_L": f"{CH}/head_ear_L.stl",
    "neck": f"{CH}/neck_bracket.stl",
    "l2ad": f"{CH}/l2_adapter.stl",
    "l2": f"{CH}/l2_ref.stl",
    "d456": f"{CH}/d456_ref.stl",
    # --- electronics: Jetson case + cradle/cowl/clamps + E-stop/OLED pod ---
    "pod": f"{CH}/control_pod.stl",
    "jmount": f"{CH}/jetson_case_mount.stl",
    "jcowl": f"{CH}/jetson_cowl.stl",
    "jcase": f"{CH}/jetson_case_ref.stl",
    "jbar": f"{CH}/jetson_clamp_bar.stl",
    "oled": f"{CH}/oled_mount.stl",
}
geo = {}
total = 0
for name, path in MESHES.items():
    b64, nf = load_soup(path)
    geo[name] = b64
    total += nf
print(f"decimated total faces: {total}")

# ---- leg kinematic chain (coax frame), from preview_assembly.leg_mesh ----
# Each leg part is placed in the COAX frame by a chain that depends on
# hfe/kfe; the whole leg is then placed in the world by `base`, and haa is
# a world-space roll about the hip axis. JS composes:
#   world = HAA(haa) @ base @ coaxframe(part; hfe,kfe)
# We emit `base` (4x4) + hip point per leg + per-part op-lists JS evaluates.

# constants for the coax-frame chain
Mf = mat_list(T([33.8, 11.6, -9.5]) @ R(180, [0, 0, 1]) @ R(90, [0, 1, 0]))
HFE_PT = [33.8, 11.6, -9.5]
KNEE = mat_list(T([106.9, 0, 0]))
ARM_OFF = mat_list(T([59, 0, 17.75]))  # rev 3 (2026-07-10): 17.2->17.75
SHOE_OFF = mat_list(T([129, 0, -30.5]) @ R(54, [0, 0, 1]) @ T([0, -7.0, 0]))

# per-part op recipe in the coax frame (JS builds the matrix live):
#  ops: list of ["fixed", M] | ["hfe"] (rot about x through HFE_PT) |
#       ["knee", KNEE] | ["kfe"] (rot about z at knee origin) | ["mf"] | ...
PART_CHAIN = {
    "coax":  [],
    "femur": ["hfe", "mf"],
    "knee":  ["hfe", "mf", "arm"],
    "tibia": ["hfe", "mf", "knee", "kfe"],
    "kneebump": ["hfe", "mf", "knee", "kfe"],   # TPU bumper: same frame as tibia
    "shoe":  ["hfe", "mf", "knee", "kfe", "shoe"],
}

# ---- 4 leg bases (coax frame -> world), from coax_to_trunk_bases -------
# preview S2T_f for a front leg: [[0,1,0,HIP_FA],[1,0,0,0],[0,0,1,HIP_Z],..]
# then T(HIP_LAT) and MIR(y) for the right; front/rear via ±HIP_FA; L via MY.
MIR = np.eye(4); MIR[1, 1] = -1
S2T_f = np.array([[0, 1, 0, HIP_FA], [1, 0, 0, 0],
                  [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
W_FR = S2T_f @ T([HIP_LAT, 0, 0]) @ MIR
MY = np.eye(4); MY[1, 1] = -1
Trear = T([-2 * HIP_FA, 0, 0])
# preview: FR base=W_FR; RR = Trear@W_FR; FL = MY@W_FR; RL = MY@Trear@W_FR
LEGS = {
    "FR": {"base": mat_list(W_FR), "side": "R"},
    "RR": {"base": mat_list(Trear @ W_FR), "side": "R"},
    "FL": {"base": mat_list(MY @ W_FR), "side": "L"},
    "RL": {"base": mat_list(MY @ Trear @ W_FR), "side": "L"},
}
# hip axis point in world for the HAA roll (x-axis through the hip).
# MUST equal where each leg's base maps the coax spline (coax-frame origin)
# — else HAA rotates about an axis offset from the hip and the coax ORBITS
# (lifts + swings) instead of spinning in place. FR base -> (+FA,+LAT,Z);
# MY mirror flips y for the left legs; Trear flips x for the rear.
HIP_PT = {"FR": [HIP_FA, HIP_LAT, HIP_Z], "RR": [-HIP_FA, HIP_LAT, HIP_Z],
          "FL": [HIP_FA, -HIP_LAT, HIP_Z], "RL": [-HIP_FA, -HIP_LAT, HIP_Z]}
# haa roll sign so +slider = outboard for every leg (right y<0 -> +roll
# outboard needs -; left +). We expose signed range per side in JS.
HAA_SIGN = {"FR": -1, "RR": -1, "FL": 1, "RL": 1}

# ---- shoulders (2) + chassis + head + electronics (static transforms) ----
def s2t(end):
    return np.array([[0, end, 0, end * HIP_FA], [1, 0, 0, 0],
                     [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])

# world placements (match chassis/preview_assembly.py):
M2 = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
L2_M = T([126.5, 0, 133]) @ R(-22, [0, 0, 1]) @ T([-7.7, -14.66, 6.7])
D456_M = T([143, 0, 111.5]) @ R(27, [0, 1, 0]) @ M2 @ T([0, 0, 26])
_cb = trimesh.load(MESHES["jcase"]).bounds       # place the case: bbox-ctr x-6.85,y0,bottom z71.9
_bc = (_cb[0] + _cb[1]) / 2
CASE_M = T([-6.85 - _bc[0], -_bc[1], 71.9 - _cb[0][2]])
MY_BAR = np.eye(4); MY_BAR[1, 1] = -1     # -y clamp bar = +y bar mirrored

STATIC = [
    {"mesh": "shoulder", "M": mat_list(s2t(1)), "grp": "shoulder", "expl": [0, 0, 60]},
    {"mesh": "shoulder", "M": mat_list(s2t(-1)), "grp": "shoulder", "expl": [0, 0, 60]},
    {"mesh": "splate_R", "M": mat_list(s2t(1)), "grp": "shoulder", "expl": [0, 0, 90]},
    {"mesh": "splate_L", "M": mat_list(s2t(1)), "grp": "shoulder", "expl": [0, 0, 90]},
    {"mesh": "splate_R", "M": mat_list(s2t(-1)), "grp": "shoulder", "expl": [0, 0, 90]},
    {"mesh": "splate_L", "M": mat_list(s2t(-1)), "grp": "shoulder", "expl": [0, 0, 90]},
    # chassis
    {"mesh": "trunk", "M": mat_list(np.eye(4)), "grp": "chassis", "expl": [0, 0, 0]},
    {"mesh": "riser", "M": mat_list(np.eye(4)), "grp": "chassis", "expl": [0, 0, 70]},
    {"mesh": "battery", "M": mat_list(np.eye(4)), "grp": "chassis", "expl": [0, 0, -70]},
    {"mesh": "floor", "M": mat_list(np.eye(4)), "grp": "chassis", "expl": [0, 0, -35]},
    {"mesh": "skid", "M": mat_list(T([-55, 9, -39.2])), "grp": "chassis", "expl": [0, 40, -95]},
    {"mesh": "skid", "M": mat_list(T([-55, -21, -39.2])), "grp": "chassis", "expl": [0, -40, -95]},
    # forward HEAD + sensors
    {"mesh": "head", "M": mat_list(np.eye(4)), "grp": "head", "expl": [70, 0, 55]},
    {"mesh": "ear_R", "M": mat_list(np.eye(4)), "grp": "head", "expl": [40, 55, 110]},
    {"mesh": "ear_L", "M": mat_list(np.eye(4)), "grp": "head", "expl": [40, -55, 110]},
    {"mesh": "neck", "M": mat_list(np.eye(4)), "grp": "head", "expl": [35, 0, -25]},
    {"mesh": "l2ad", "M": mat_list(np.eye(4)), "grp": "head", "expl": [0, 0, 45]},
    {"mesh": "l2", "M": mat_list(L2_M), "grp": "head", "expl": [0, 0, 120]},
    {"mesh": "d456", "M": mat_list(D456_M), "grp": "head", "expl": [95, 0, 45]},
    # electronics
    {"mesh": "pod", "M": mat_list(np.eye(4)), "grp": "elec", "expl": [-70, 0, 55]},
    {"mesh": "jmount", "M": mat_list(np.eye(4)), "grp": "elec", "expl": [0, 0, -15]},
    {"mesh": "jcowl", "M": mat_list(np.eye(4)), "grp": "elec", "expl": [0, -70, 0]},
    {"mesh": "jcase", "M": mat_list(CASE_M), "grp": "elec", "expl": [0, 0, 35]},
    {"mesh": "oled", "M": mat_list(np.eye(4)), "grp": "elec", "expl": [-70, 30, 60]},
    {"mesh": "jbar", "M": mat_list(np.eye(4)), "grp": "elec", "expl": [0, 0, 55]},
    {"mesh": "jbar", "M": mat_list(MY_BAR), "grp": "elec", "expl": [0, 0, 55]},
]

DATA = {
    "geo": geo, "legs": LEGS, "hipPt": HIP_PT, "haaSign": HAA_SIGN,
    "static": STATIC, "chain": PART_CHAIN,
    "Mf": Mf, "hfePt": HFE_PT, "knee": KNEE, "arm": ARM_OFF, "shoe": SHOE_OFF,
    # leg part -> mesh key uses side; explode factors (proximal->distal)
    "legParts": {"coax": 0.0, "femur": 45, "knee": 45, "tibia": 95,
                 "kneebump": 95, "shoe": 140},
    "rom": {"haaIn": 15, "haaOut": 40, "hfeMin": -86, "hfeMax": 50,
            "kfe": 109},
}

HTML = r"""<!doctype html><html><head><meta charset=utf8>
<title>NOVA robot — ROM + explode viewer</title>
<style>
 html,body{margin:0;height:100%;background:#0e1116;color:#c8d0da;
   font:13px/1.4 -apple-system,system-ui,sans-serif;overflow:hidden}
 #c{position:fixed;inset:0;display:block}
 #ui{position:fixed;top:0;left:0;width:250px;max-height:100%;overflow:auto;
   padding:14px;background:rgba(16,20,27,.86);backdrop-filter:blur(6px);
   border-right:1px solid #232a35}
 h1{font-size:15px;margin:0 0 2px}
 .sub{color:#7f8b9c;font-size:11px;margin-bottom:12px}
 .row{margin:9px 0}
 label{display:flex;justify-content:space-between;font-size:11px;
   color:#9fb0c4;margin-bottom:3px}
 label b{color:#e6edf5;font-variant-numeric:tabular-nums}
 input[type=range]{width:100%;accent-color:#5b9dff;height:3px}
 .seg{display:flex;gap:4px;margin:4px 0 10px;flex-wrap:wrap}
 .seg button{flex:1;min-width:38px;background:#1a212b;color:#9fb0c4;
   border:1px solid #2a3340;border-radius:5px;padding:5px 0;cursor:pointer;
   font-size:11px}
 .seg button.on{background:#2b60b8;color:#fff;border-color:#3b74d6}
 .hd{margin:15px 0 4px;color:#6f7c8e;font-size:10px;letter-spacing:.08em;
   text-transform:uppercase}
 .ck{display:flex;align-items:center;gap:7px;margin:5px 0;cursor:pointer}
 .ck input{accent-color:#5b9dff}
 .tip{font-size:10px;color:#5c6675;margin-top:14px;
   border-top:1px solid #232a35;padding-top:10px}
 button.act{width:100%;background:#1a212b;color:#c8d0da;border:1px solid
   #2a3340;border-radius:6px;padding:8px;margin-top:6px;cursor:pointer}
 button.act:hover{background:#222b37}
</style></head><body>
<canvas id=c></canvas>
<div id=ui>
 <h1>NOVA</h1><div class=sub>leg_v6 · gate-verified poses</div>

 <div class=hd>articulate</div>
 <div class=seg id=legsel>
   <button data-l=all class=on>all</button>
   <button data-l=FR>FR</button><button data-l=FL>FL</button>
   <button data-l=RR>RR</button><button data-l=RL>RL</button>
 </div>
 <div class=row><label>HAA roll <b id=vhaa>0°</b></label>
   <input type=range id=haa min=-40 max=40 value=0 step=1></div>
 <div class=row><label>HFE hip <b id=vhfe>40°</b></label>
   <input type=range id=hfe min=-86 max=50 value=40 step=1></div>
 <div class=row><label>KFE knee <b id=vkfe>80°</b></label>
   <input type=range id=kfe min=-109 max=109 value=80 step=1></div>
 <button class=act id=stance>stance pose</button>
 <button class=act id=sweep>▶ sweep ROM</button>

 <div class=hd>explode <b id=vexp style=float:right;color:#e6edf5>0%</b></div>
 <input type=range id=exp min=0 max=100 value=0 step=1 style=width:100%>

 <div class=hd>show</div>
 <label class=ck><input type=checkbox id=gLegs checked>legs + feet</label>
 <label class=ck><input type=checkbox id=gShoulder checked>shoulders</label>
 <label class=ck><input type=checkbox id=gChassis checked>chassis</label>
 <label class=ck><input type=checkbox id=gHead checked>head + sensors</label>
 <label class=ck><input type=checkbox id=gElec checked>jetson + pod</label>
 <button class=act id=reset>reset view</button>
 <div class=tip>drag rotate · scroll zoom · right-drag pan.
   Sliders honor the CAD fit-gate ROM (haa inboard cap 15°, hfe +50 fold,
   kfe ±109).</div>
</div>
<script>
const D=__DATA__;
// ---------- tiny mat4 (column-major) ----------
const M4={
 id:()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
 mul:(a,b)=>{const o=new Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++){
   let s=0;for(let k=0;k<4;k++)s+=a[k*4+r]*b[c*4+k];o[c*4+r]=s;}return o;},
 trans:(x,y,z)=>[1,0,0,0,0,1,0,0,0,0,1,0,x,y,z,1],
 rot:(deg,ax)=>{const a=deg*Math.PI/180,c=Math.cos(a),s=Math.sin(a);
   let[x,y,z]=ax;const t=1-c;return[
   t*x*x+c,t*x*y+s*z,t*x*z-s*y,0, t*x*y-s*z,t*y*y+c,t*y*z+s*x,0,
   t*x*z+s*y,t*y*z-s*x,t*z*z+c,0, 0,0,0,1];},
 rotPt:(deg,ax,p)=>M4.mul(M4.trans(p[0],p[1],p[2]),
   M4.mul(M4.rot(deg,ax),M4.trans(-p[0],-p[1],-p[2]))),
 persp:(f,a,n,fa)=>{const t=1/Math.tan(f/2);return[t/a,0,0,0,0,t,0,0,
   0,0,(fa+n)/(n-fa),-1,0,0,2*fa*n/(n-fa),0];},
 look:(e,c,u)=>{const s=v=>{const l=Math.hypot(...v);return[v[0]/l,v[1]/l,v[2]/l];};
   const f=s([c[0]-e[0],c[1]-e[1],c[2]-e[2]]);
   const r=s([f[1]*u[2]-f[2]*u[1],f[2]*u[0]-f[0]*u[2],f[0]*u[1]-f[1]*u[0]]);
   const up=[r[1]*f[2]-r[2]*f[1],r[2]*f[0]-r[0]*f[2],r[0]*f[1]-r[1]*f[0]];
   return[r[0],up[0],-f[0],0,r[1],up[1],-f[1],0,r[2],up[2],-f[2],0,
   -(r[0]*e[0]+r[1]*e[1]+r[2]*e[2]),-(up[0]*e[0]+up[1]*e[1]+up[2]*e[2]),
   f[0]*e[0]+f[1]*e[1]+f[2]*e[2],1];}
};
function b64f32(b){const s=atob(b),n=s.length,u=new Uint8Array(n);
  for(let i=0;i<n;i++)u[i]=s.charCodeAt(i);return new Float32Array(u.buffer);}
// ---------- GL ----------
const cv=document.getElementById('c');
const gl=cv.getContext('webgl',{antialias:true});
const vs=`attribute vec3 p;uniform mat4 mvp,mv;varying vec3 vp;
 void main(){vp=(mv*vec4(p,1.)).xyz;gl_Position=mvp*vec4(p,1.);}`;
const fs=`precision mediump float;varying vec3 vp;uniform vec3 col;
 void main(){vec3 n=normalize(cross(dFdx(vp),dFdy(vp)));
 float d=abs(dot(n,normalize(vec3(.3,.5,.8))))*.75+.25;
 gl_FragColor=vec4(col*d,1.);}`;
const ext=gl.getExtension('OES_standard_derivatives');
function sh(t,s){const o=gl.createShader(t);gl.shaderSource(o,s);
  gl.compileShader(o);return o;}
const pr=gl.createProgram();
gl.attachShader(pr,sh(gl.VERTEX_SHADER,'#extension GL_OES_standard_derivatives:enable\n'+vs.replace('varying','varying')));
gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,'#extension GL_OES_standard_derivatives:enable\n'+fs));
gl.linkProgram(pr);gl.useProgram(pr);
const aP=gl.getAttribLocation(pr,'p');
const uMVP=gl.getUniformLocation(pr,'mvp'),uMV=gl.getUniformLocation(pr,'mv'),
  uCol=gl.getUniformLocation(pr,'col');
gl.enable(gl.DEPTH_TEST);gl.clearColor(.055,.067,.086,1);
// upload meshes
const buf={},cnt={};
for(const k in D.geo){const a=b64f32(D.geo[k]);const b=gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,a,gl.STATIC_DRAW);
  buf[k]=b;cnt[k]=a.length/3;}
const COL={R:[.62,.70,.82],L:[.58,.66,.78],knee_arm:[.80,.62,.36],
  shoe:[.85,.35,.30],shoulder:[.55,.72,.60],splate:[.80,.62,.36],
  chassis:[.48,.54,.64],trunk:[.40,.45,.55],riser:[.52,.60,.72],
  battery:[.75,.55,.30],floor:[.5,.56,.66],skid:[.85,.35,.30],
  head:[.62,.58,.74],ear_R:[.68,.60,.50],ear_L:[.68,.60,.50],neck:[.50,.62,.72],
  l2ad:[.72,.72,.50],l2:[.45,.55,.72],d456:[.70,.45,.55],
  pod:[.50,.78,.70],jmount:[.80,.62,.36],jcowl:[.85,.42,.32],
  jcase:[.50,.56,.66],jbar:[.90,.55,.30],oled:[.40,.85,.55]};
// ---------- build instance list ----------
const P=[];               // {mesh,color,base(mat),expl(vec),grp,legParts?}
function legPartMesh(part,side){
  // ALWAYS the R mesh: left legs are the R leg mirrored by the base MY
  // (matches preview_assembly — the L meshes are X-mirrors and would
  // double-mirror here).
  if(part==='coax')return 'coax_R';
  if(part==='femur')return 'femur_R';
  if(part==='tibia')return 'tibia_R';
  if(part==='knee')return 'knee_arm';
  if(part==='kneebump')return 'knee_bump';
  if(part==='shoe')return 'shoe';}
function coaxFrame(part,hfe,kfe){
  let m=M4.id();const ops=D.chain[part];
  for(const op of ops){
   if(op==='hfe')m=M4.mul(m,M4.rotPt(hfe,[1,0,0],D.hfePt));
   else if(op==='mf')m=M4.mul(m,D.Mf);
   else if(op==='knee')m=M4.mul(m,D.knee);
   else if(op==='kfe')m=M4.mul(m,M4.rot(kfe,[0,0,1]));
   else if(op==='arm')m=M4.mul(m,D.arm);
   else if(op==='shoe')m=M4.mul(m,D.shoe);}
  return m;}
for(const L in D.legs){const lg=D.legs[L];
 for(const part in D.legParts){
  const mk=legPartMesh(part,lg.side);
  P.push({leg:L,part:part,mesh:mk,grp:'legs',
   color: part==='knee'?COL.knee_arm: (part==='shoe'||part==='kneebump')?COL.shoe: COL[lg.side]});
 }}
for(const s of D.static)P.push({mesh:s.mesh,grp:s.grp,exS:s.expl,
  color:COL[s.mesh]||COL[s.grp]||COL.chassis, staticM:s.M});
// ---------- state ----------
let joints={FR:[0,40,80],FL:[0,40,80],RR:[0,40,80],RL:[0,40,80]};
let sel='all',explode=0;
let show={legs:1,shoulder:1,chassis:1,head:1,elec:1};
const CAM0={az:-0.9,el:0.42,r:600,tx:0,ty:0,tz:0};
let cam=Object.assign({},CAM0);
// center of assembly (approx, mm) for explode + camera target
const CTR=[0,0,-45];
function legWorld(part,L){
 const lg=D.legs[L],hp=D.hipPt[L];
 const cf=coaxFrame(part,joints[L][1],joints[L][2]);
 let m=M4.mul(lg.base,cf);
 m=M4.mul(M4.rotPt(joints[L][0]*D.haaSign[L],[1,0,0],hp),m);
 return m;}
function draw(){
 const w=cv.width,h=cv.height;gl.viewport(0,0,w,h);
 gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 const ce=Math.cos(cam.el),se=Math.sin(cam.el);
 // Z is the robot's UP axis (chassis frame); orbit in xy, elevate in z
 const eye=[CTR[0]+cam.tx+cam.r*ce*Math.cos(cam.az),
   CTR[1]+cam.ty+cam.r*ce*Math.sin(cam.az),
   CTR[2]+cam.tz+cam.r*se];
 const tgt=[CTR[0]+cam.tx,CTR[1]+cam.ty,CTR[2]+cam.tz];
 const V=M4.look(eye,tgt,[0,0,1]);
 const Pj=M4.persp(0.9,w/h,5,4000);
 const VP=M4.mul(Pj,V);
 gl.bindBuffer(gl.ARRAY_BUFFER,null);
 for(const it of P){
  if(!show[it.grp])continue;
  if(!cnt[it.mesh])continue;
  let world;
  if(it.leg){world=legWorld(it.part,it.leg);}
  else world=it.staticM;
  // explode offset
  if(explode>0){
   let dir;
   if(it.leg){
     // slide distal parts outward along the leg's proximal->distal dir
     const wl=legWorld(it.part,it.leg);
     const base=D.legs[it.leg].base;
     // direction = world position of part origin - hip, normalized
     const px=world[12]-D.hipPt[it.leg][0],py=world[13]-D.hipPt[it.leg][1],
       pz=world[14]-D.hipPt[it.leg][2];
     const l=Math.hypot(px,py,pz)||1;
     const f=D.legParts[it.part];
     dir=[px/l*f,py/l*f,pz/l*f];
   } else dir=it.exS;
   world=world.slice();
   world[12]+=dir[0]*explode/100;world[13]+=dir[1]*explode/100;
   world[14]+=dir[2]*explode/100;
  }
  const MV=M4.mul(V,world),MVP=M4.mul(VP,world);
  gl.uniformMatrix4fv(uMVP,false,MVP);gl.uniformMatrix4fv(uMV,false,MV);
  gl.uniform3fv(uCol,it.color);
  gl.bindBuffer(gl.ARRAY_BUFFER,buf[it.mesh]);
  gl.enableVertexAttribArray(aP);gl.vertexAttribPointer(aP,3,gl.FLOAT,false,0,0);
  gl.drawArrays(gl.TRIANGLES,0,cnt[it.mesh]);
 }
}
function resize(){cv.width=innerWidth*devicePixelRatio;
  cv.height=innerHeight*devicePixelRatio;draw();}
addEventListener('resize',resize);
// ---------- interaction ----------
let drag=null;
cv.addEventListener('mousedown',e=>drag={x:e.clientX,y:e.clientY,b:e.button});
addEventListener('mouseup',()=>drag=null);
addEventListener('mousemove',e=>{if(!drag)return;
 const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;
 if(drag.b===2){const k=cam.r/900;
   cam.tx-=(-Math.sin(cam.az))*dx*k;cam.ty-=(Math.cos(cam.az))*dx*k;
   cam.tz+=dy*k;}
 else{cam.az-=dx*.008;cam.el=Math.max(-1.35,Math.min(1.35,cam.el+dy*.008));}
 draw();});
cv.addEventListener('contextmenu',e=>e.preventDefault());
cv.addEventListener('wheel',e=>{e.preventDefault();
 cam.r=Math.max(120,Math.min(2000,cam.r*(1+Math.sign(e.deltaY)*.09)));draw();},
 {passive:false});
// ---------- UI ----------
const $=id=>document.getElementById(id);
function applyJoint(i,v){
 const legs=sel==='all'?['FR','FL','RR','RL']:[sel];
 for(const L of legs)joints[L][i]=v;draw();}
function refreshSliders(){const L=sel==='all'?'FR':sel;
 $('haa').value=joints[L][0];$('hfe').value=joints[L][1];$('kfe').value=joints[L][2];
 $('vhaa').textContent=joints[L][0]+'°';$('vhfe').textContent=joints[L][1]+'°';
 $('vkfe').textContent=joints[L][2]+'°';}
$('haa').oninput=e=>{$('vhaa').textContent=e.target.value+'°';applyJoint(0,+e.target.value);};
$('hfe').oninput=e=>{$('vhfe').textContent=e.target.value+'°';applyJoint(1,+e.target.value);};
$('kfe').oninput=e=>{$('vkfe').textContent=e.target.value+'°';applyJoint(2,+e.target.value);};
$('exp').oninput=e=>{explode=+e.target.value;$('vexp').textContent=explode+'%';draw();};
document.querySelectorAll('#legsel button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('#legsel button').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');sel=b.dataset.l;refreshSliders();});
for(const[id,g]of[['gLegs','legs'],['gShoulder','shoulder'],['gChassis','chassis'],['gHead','head'],['gElec','elec']])
 $(id).onchange=e=>{show[g]=e.target.checked;draw();};
$('stance').onclick=()=>{for(const L in joints)joints[L]=[0,40,80];
 explode=0;$('exp').value=0;$('vexp').textContent='0%';refreshSliders();draw();};
$('reset').onclick=()=>{cam=Object.assign({},CAM0);draw();};
let sweeping=null;
$('sweep').onclick=()=>{if(sweeping){clearInterval(sweeping);sweeping=null;
 $('sweep').textContent='▶ sweep ROM';return;}
 $('sweep').textContent='■ stop';let t=0;
 sweeping=setInterval(()=>{t+=0.03;
  const haa=Math.sin(t)*20, hfe=Math.sin(t*0.7)*40+10, kfe=Math.sin(t*1.3)*70+30;
  for(const L in joints)joints[L]=[haa,hfe,kfe];refreshSliders();draw();},33);};
resize();
</script></body></html>"""

html = HTML.replace("__DATA__", json.dumps(DATA))
import os
os.makedirs(f"{CAD}/viewer", exist_ok=True)
with open(OUT, "w") as fp:
    fp.write(html)
print(f"wrote {OUT}  ({len(html)/1e6:.1f} MB)")
