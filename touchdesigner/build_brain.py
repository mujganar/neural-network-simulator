# NEURON SCALE v2 - endless instanced brain tissue in fluid
# Run inside TouchDesigner (Textport):
#   exec(open('/Users/mujganar/VJ-PROJECTS/NEURON_SCALE/td/build_brain_v5.py').read())
# Rebuilds the visual side of /project1/neuron_scale; keeps midi / brain / ctrl.

import json

ROOT = '/Users/mujganar/VJ-PROJECTS/NEURON_SCALE'
LIB = json.load(open(ROOT + '/geo/library/library.json'))
COUNTS = {'pyramidal': 22, 'stellate': 18, 'astro': 22}      # instances per variant
PARTICLES = 3500
BOX = (12.0, 20.0, 40.0, 4.0)       # half-width, half-height, depth, z of the near wrap plane
FOG = (0.04, 40.0)                 # density, depth normaliser
KIND = {'pyramidal': (1.0, 0.0), 'stellate': (0.0, 0.03), 'astro': (0.0, 0.10)}   # align, hue offset

base = op('/project1/neuron_scale')
log = []

# ------------------------------------------------------------------ clean old visuals
for name in ['bloom', 'glsl_info', 'neuron_vert', 'neuron_frag']:
    o = base.op(name)
    if o: o.destroy()
old_names = [o.name for o in base.children
             if o.name.startswith(('neuron_', 'mat_', 'cells_', 'cmat_', 'part', 'inst_', 'dof', 'fluid', 'shader_', 'grade', 'pmat', 'dbg_'))]
for nm in old_names:
    o = base.op(nm)
    if o is not None and o.valid:
        o.destroy()


def make(optype, name, x, y):
    o = base.create(optype, name)
    o.nodeX, o.nodeY = x, y
    for d in list(getattr(o, 'docked', [])):     # drop the default shader DATs TD docks to GLSL ops
        try:
            d.destroy()
        except Exception:
            pass
    return o


def text(name, body, x, y):
    t = make(textDAT, name, x, y)
    t.text = body
    return t


# ------------------------------------------------------------------ ctrl: extra channels
ctrl = base.op('ctrl')
for i, nm in [(8, 'flow'), (9, 'since'), (10, 'vel'), (11, 'clock')]:
    ctrl.par['const%dname' % i] = nm

# ------------------------------------------------------------------ shaders
COMMON = r'''
vec3 hash3(float n) { return fract(sin(vec3(n, n + 1.31, n + 2.77)) * vec3(43758.5453, 22578.1459, 19642.3490)); }
mat3 rotAxis(vec3 a, float ang) {
    a = normalize(a); float s = sin(ang), c = cos(ang), oc = 1.0 - c;
    return mat3(oc*a.x*a.x + c,     oc*a.x*a.y + a.z*s, oc*a.z*a.x - a.y*s,
                oc*a.x*a.y - a.z*s, oc*a.y*a.y + c,     oc*a.y*a.z + a.x*s,
                oc*a.z*a.x + a.y*s, oc*a.y*a.z - a.x*s, oc*a.z*a.z + c);
}
vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}
// position of an instance inside the endless, flowing tissue block
vec3 tissuePos(vec3 h, vec4 box, float flow, float t) {
    vec3 pos;
    pos.x = (h.x - 0.5) * 2.0 * box.x;
    pos.y = (h.y - 0.5) * 2.0 * box.y;
    float fr = fract(h.z + flow / box.z);
    pos.z = box.w - (1.0 - fr) * box.z;
    pos.x += sin(pos.z * 0.09 + t * 0.21) * 1.2;          // slow lateral current
    pos.y += sin(pos.z * 0.07 + t * 0.17 + 1.7) * 0.8;
    // keep a clear corridor in front of the lens: cells slide past instead of through the camera
    float nearK = smoothstep(-12.0, 2.0, pos.z);
    vec2 d2 = pos.xy + vec2(1e-3, 0.0);
    float r = length(d2);
    pos.xy += d2 / r * nearK * max(0.0, 6.5 - r);
    return pos;
}
'''

CELL_VERT = r'''
uniform vec4 uCtrl;   // hue, sat, bri, pulse
uniform vec4 uCtrl2;  // intensity, spike, wobble, time
uniform vec4 uFlow;   // flow, since(note), vel, clock
uniform vec4 uBox;
uniform vec4 uVar;    // seed, radius, align, hue offset
out Vertex {
    vec3 worldPos; vec3 worldNorm; vec3 localPos; vec3 camPos;
    float dist; float ph1; float g1; float ph2; float g2;
} oVert;
''' + COMMON + r'''
void main() {
    float id = float(TDInstanceID()) + uVar.x * 137.0;
    vec3 h1 = hash3(id * 1.13 + 0.5), h2 = hash3(id * 2.71 + 5.0);
    mat3 R;
    if (uVar.z > 0.5)   // pyramidal cells stand in columns, apical dendrite toward the pia (+Y)
        R = rotAxis(vec3(0, 1, 0), h2.x * 6.2832) * rotAxis(vec3(1, 0, 0), (h2.y - 0.5) * 0.45) * rotAxis(vec3(0, 0, 1), (h2.z - 0.5) * 0.45);
    else
        R = rotAxis(h2 * 2.0 - 1.0 + 1e-3, h1.x * 6.2832);
    float sc = 1.35 + 0.6 * h2.z;
    float t = uCtrl2.w;

    vec3 p0 = TDPos();
    vec3 n0 = TDNormal();
    vec3 q = p0 * 0.5 + h1 * 10.0;
    vec3 sway = vec3(TDSimplexNoise(q + vec3(t, 0, 0)), TDSimplexNoise(q + vec3(0, t, 5.0)), TDSimplexNoise(q + vec3(9.0, 0, t)));
    vec3 pl = p0 + sway * uCtrl2.z * 0.3 * clamp(length(p0) / uVar.y, 0.0, 1.0);   // tips drift, soma stays
    pl += n0 * TDSimplexNoise(p0 * 18.0) * uCtrl2.y * 0.02;

    vec3 pos = tissuePos(h1, uBox, uFlow.x, uFlow.w);
    pos += 0.35 * vec3(sin(t * 0.37 + h2.x * 6.28), sin(t * 0.29 + h2.y * 6.28), 0.0);
    vec4 wp = TDDeform(R * (pl * sc) + pos);

    oVert.worldPos = wp.xyz;
    oVert.worldNorm = normalize(TDDeformNorm(R * n0));
    oVert.localPos = p0;
    oVert.camPos = uTDMats[TDCameraIndex()].camInverse[3].xyz;
    oVert.dist = length(p0) / uVar.y;

    // music-driven action potentials cascade through a velocity-dependent share of cells
    float respond = step(h1.y, 0.12 + 0.45 * uFlow.z);
    oVert.ph1 = (uFlow.y - h2.x * 0.9) / 0.7;
    oVert.g1 = respond * uFlow.z * step(0.0, oVert.ph1) * step(oVert.ph1, 1.3);
    // spontaneous background firing keeps the tissue alive between notes
    float period = 3.0 + 9.0 * h2.y;
    oVert.ph2 = mod(uFlow.w + h1.x * period, period) / 0.9;
    oVert.g2 = 0.35 * step(oVert.ph2, 1.3) * step(0.7, h2.z);
    gl_Position = TDWorldToProj(wp);
}
'''

CELL_FRAG = r'''
uniform vec4 uCtrl;
uniform vec4 uCtrl2;
uniform vec4 uVar;
uniform vec4 uFog;    // density, depth normaliser
in Vertex {
    vec3 worldPos; vec3 worldNorm; vec3 localPos; vec3 camPos;
    float dist; float ph1; float g1; float ph2; float g2;
} iVert;
out vec4 fragColor[TD_NUM_COLOR_BUFFERS];
''' + COMMON + r'''
void main() {
    TDCheckDiscard();
    vec3 V = normalize(iVert.camPos - iVert.worldPos);
    vec3 N = normalize(iVert.worldNorm);
    if (!gl_FrontFacing) N = -N;
    vec3 lp = iVert.localPos * 38.0;      // membrane micro-texture
    N = normalize(N + 0.10 * vec3(TDSimplexNoise(lp), TDSimplexNoise(lp + 17.1), TDSimplexNoise(lp + 31.7)));

    float hue = fract(uCtrl.x + uVar.w);
    vec3 tint = hsv2rgb(vec3(hue, uCtrl.y * 0.55, 1.0));
    vec3 albedo = mix(vec3(0.85, 0.87, 0.92), tint, 0.5) * (0.7 + 0.5 * uCtrl.z);

    vec3 L1 = normalize(vec3(0.35, 0.85, 0.45));
    vec3 L2 = normalize(vec3(-0.2, -0.3, -1.0));
    float dif = max(0.0, (dot(N, L1) + 0.6) / 1.6);                         // wrap light
    float trans = pow(max(0.0, dot(V, -L2)), 3.0) * 0.6 + pow(max(0.0, dot(-N, L1)), 2.0) * 0.25;
    vec3 H = normalize(L1 + V);
    float NdV = max(0.0, dot(N, V));
    float fres = 0.04 + 0.96 * pow(1.0 - NdV, 5.0);
    float spec = pow(max(0.0, dot(N, H)), 90.0) * (0.25 + fres);           // wet sheen
    vec3 col = albedo * (0.12 + 1.1 * dif) + albedo * tint * trans * 1.4 + vec3(spec) * 0.6
             + tint * pow(1.0 - NdV, 2.5) * 0.45 + tint * 0.05;   // faint autofluorescence

    float b1 = exp(-pow((iVert.dist - (iVert.ph1 * 1.15 - 0.05)) * 8.0, 2.0)) * iVert.g1;
    float b2 = exp(-pow((iVert.dist - (iVert.ph2 * 1.15 - 0.05)) * 8.0, 2.0)) * iVert.g2;
    vec3 glowC = hsv2rgb(vec3(hue, uCtrl.y, 1.0));
    col += glowC * (b1 * 1.8 + b2 * 0.6) + vec3(b1 * 0.25);

    float d = length(iVert.camPos - iVert.worldPos);
    vec3 fogC = hsv2rgb(vec3(fract(uCtrl.x + 0.55), 0.5, 0.06 + 0.05 * uCtrl.z));
    col = mix(col, fogC, 1.0 - exp(-d * uFog.x));
    if (d < 0.8) discard;
    col = mix(fogC * 0.6, col, smoothstep(0.8, 4.0, d));          // anything brushing the lens melts into the fluid
    fragColor[0] = TDOutputSwizzle(vec4(col, clamp(d / uFog.y, 0.002, 1.0)));   // alpha carries depth for DOF
}
'''

PART_VERT = r'''
uniform vec4 uCtrl2;
uniform vec4 uFlow;
uniform vec4 uBox;
out Vertex { vec3 worldPos; vec3 worldNorm; vec3 camPos; float rnd; } oVert;
''' + COMMON + r'''
void main() {
    float id = float(TDInstanceID());
    vec3 h = hash3(id * 0.731 + 11.0), h2 = hash3(id * 1.977 + 3.0);
    float t = uFlow.w;
    float sc = 0.007 + 0.028 * pow(h2.x, 6.0);                // tiny vesicles, rare small flecks
    vec3 pos = tissuePos(h, uBox, uFlow.x * 1.15, t);
    vec3 q = pos * 0.12 + vec3(0.0, 0.0, t * 0.05);
    pos += vec3(TDSimplexNoise(q), TDSimplexNoise(q + 7.7), TDSimplexNoise(q + 13.3)) * 1.6;   // turbulent drift
    vec4 wp = TDDeform(TDPos() * sc + pos);
    oVert.worldPos = wp.xyz;
    oVert.worldNorm = normalize(TDDeformNorm(TDNormal()));
    oVert.camPos = uTDMats[TDCameraIndex()].camInverse[3].xyz;
    oVert.rnd = h2.y;
    gl_Position = TDWorldToProj(wp);
}
'''

PART_FRAG = r'''
uniform vec4 uCtrl;
uniform vec4 uCtrl2;
uniform vec4 uFog;
in Vertex { vec3 worldPos; vec3 worldNorm; vec3 camPos; float rnd; } iVert;
out vec4 fragColor[TD_NUM_COLOR_BUFFERS];
''' + COMMON + r'''
void main() {
    TDCheckDiscard();
    vec3 V = normalize(iVert.camPos - iVert.worldPos);
    float NdV = abs(dot(normalize(iVert.worldNorm), V));
    vec3 c = hsv2rgb(vec3(fract(uCtrl.x + 0.1 * iVert.rnd), 0.6, 1.0));
    float rim = pow(1.0 - NdV, 2.5);
    vec3 col = c * (0.04 + 0.5 * rim) * (0.45 + 0.35 * uCtrl2.x);   // dim, translucent-looking vesicles
    float d = length(iVert.camPos - iVert.worldPos);
    if (d < 3.0) discard;                     // nothing right on the lens
    vec3 fogC = hsv2rgb(vec3(fract(uCtrl.x + 0.55), 0.5, 0.06 + 0.05 * uCtrl.z));
    col = mix(col, fogC, 1.0 - exp(-d * uFog.x * 1.2));
    col = mix(fogC, col, smoothstep(3.0, 9.0, d));   // near particles melt into the fluid instead of blowing out
    col = min(col, vec3(0.45));                // never bright enough to bloom into white discs
    fragColor[0] = TDOutputSwizzle(vec4(col, clamp(d / uFog.y, 0.002, 1.0)));
}
'''

DOF_FRAG = r'''
uniform vec4 uDof;   // focus (0..1 depth), range, max radius px
out vec4 fragColor;
float coc(float a) { float d = a <= 0.0 ? 1.0 : a; return clamp(abs(d - uDof.x) / uDof.y, 0.0, 1.0) * uDof.z; }
void main() {
    vec2 uv = vUV.st;
    vec4 c = texture(sTD2DInputs[0], uv);
    float r0 = coc(c.a);
    vec2 px = uTD2DInfos[0].res.xy;
    vec3 acc = c.rgb; float ws = 1.0;
    for (int i = 0; i < 32; i++) {
        float a = float(i) * 2.39996;
        float rr = sqrt((float(i) + 0.5) / 32.0);
        vec2 o = vec2(cos(a), sin(a)) * rr * r0 * px;
        vec4 s = texture(sTD2DInputs[0], uv + o);
        float w = smoothstep(0.0, 1.0, coc(s.a) / (rr * r0 + 1e-3) + 0.25);
        acc += s.rgb * w; ws += w;
    }
    fragColor = TDOutputSwizzle(vec4(acc / ws, 1.0));
}
'''

FLUID_FRAG = r'''
uniform vec4 uF;     // time, refraction, aberration, grain
uniform vec4 uTint;  // caustic rgb, vignette
out vec4 fragColor;
void main() {
    vec2 uv = vUV.st; float t = uF.x;
    vec2 w = vec2(TDSimplexNoise(vec3(uv * 3.0, t * 0.15)), TDSimplexNoise(vec3(uv * 3.0 + 7.3, t * 0.15)));
    w += 0.5 * vec2(TDSimplexNoise(vec3(uv * 9.0, t * 0.3)), TDSimplexNoise(vec3(uv * 9.0 + 3.1, t * 0.3)));
    vec2 duv = uv + w * uF.y;
    vec2 dir = uv - 0.5;
    vec3 col = vec3(texture(sTD2DInputs[0], duv + dir * uF.z).r,
                    texture(sTD2DInputs[0], duv).g,
                    texture(sTD2DInputs[0], duv - dir * uF.z).b);
    float ca = pow(abs(TDSimplexNoise(vec3(uv * vec2(4.0, 7.0), t * 0.25))), 3.0);
    col += uTint.rgb * ca;
    float vig = smoothstep(0.95, 0.25, length(dir * vec2(1.0, 0.7)));
    col *= mix(1.0, vig, uTint.a);
    float n = fract(sin(dot(uv * uTD2DInfos[0].res.zw + t, vec2(12.9898, 78.233))) * 43758.5453);
    col += (n - 0.5) * uF.w;
    fragColor = TDOutputSwizzle(vec4(col, 1.0));
}
'''

cv = text('shader_cell_vert', CELL_VERT, 400, -300)
cf = text('shader_cell_frag', CELL_FRAG, 400, -400)
pv = text('shader_part_vert', PART_VERT, 400, -500)
pf = text('shader_part_frag', PART_FRAG, 400, -600)
dofd = text('shader_dof', DOF_FRAG, 1300, -300)
fld = text('shader_fluid', FLUID_FRAG, 1500, -300)


def bind_common(m, with_var=None):
    m.par.vec0name = 'uCtrl'; m.par.vec1name = 'uCtrl2'; m.par.vec2name = 'uFlow'
    m.par.vec3name = 'uBox';  m.par.vec4name = 'uVar';   m.par.vec5name = 'uFog'
    chans = [['hue', 'sat', 'bri', 'pulse'], ['intensity', 'spike', 'wobble', 'time'], ['flow', 'since', 'vel', 'clock']]
    for v, names in enumerate(chans):
        for ax, nm in zip('xyzw', names):
            m.par['vec%dvalue%s' % (v, ax)].expr = "op('ctrl')['%s']" % nm
    for ax, val in zip('xyzw', BOX):
        m.par['vec3value' + ax] = val
    if with_var:
        for ax, val in zip('xyzw', with_var):
            m.par['vec4value' + ax] = val
    m.par.vec5valuex, m.par.vec5valuey = FOG


# ------------------------------------------------------------------ instanced cells
geo_names = []
y = 300
for k, e in enumerate(LIB):
    n_inst = COUNTS[e['kind']]
    chop = make(patternCHOP, 'inst_%d' % k, 700, y)
    chop.par.length = n_inst
    chop.par.amp = 0
    g = make(geometryCOMP, 'cells_%d' % k, 900, y)
    for c in list(g.children):
        c.destroy()
    f = g.create(fileinSOP, 'filein')
    f.par.file = e['file']
    f.render = True; f.display = True
    try:
        g.par.instancing = True
        g.par.instanceop = chop.path
        g.par.instancetx = chop.chan(0).name if chop.numChans else 'chan1'
    except Exception as ex:
        log.append('instancing %s: %s' % (g.name, ex))
    m = make(glslMAT, 'cmat_%d' % k, 1100, y)
    m.par.vdat = cv.name; m.par.pdat = cf.name
    align, hoff = KIND[e['kind']]
    bind_common(m, (k * 3.17 + 1.0, e['radius'], align, hoff))
    g.par.material = m.path
    geo_names.append(g.name)
    y -= 120

# ------------------------------------------------------------------ fluid particles
pchop = make(patternCHOP, 'inst_particles', 700, y)
pchop.par.length = PARTICLES
pchop.par.amp = 0
pg = make(geometryCOMP, 'particles', 900, y)
for c in list(pg.children):
    c.destroy()
sph = pg.create(sphereSOP, 'sphere')
try:
    sph.par.type = 'polygon'
except Exception:
    pass
sph.par.rows, sph.par.cols = 6, 8
sph.render = True; sph.display = True
try:
    pg.par.instancing = True
    pg.par.instanceop = pchop.path
    pg.par.instancetx = pchop.chan(0).name if pchop.numChans else 'chan1'
except Exception as ex:
    log.append('instancing particles: %s' % ex)
pm = make(glslMAT, 'pmat', 1100, y)
pm.par.vdat = pv.name; pm.par.pdat = pf.name
bind_common(pm)
pg.par.material = pm.path
geo_names.append(pg.name)

# ------------------------------------------------------------------ camera + render
cam = base.op('cam')
cam.par.tx, cam.par.ty, cam.par.tz = 0, 0, 0
cam.par.rx = cam.par.ry = cam.par.rz = 0
cam.par.fov = 52
try:
    cam.par.near, cam.par.far = 0.05, 120
except Exception:
    pass
render = base.op('render')
render.par.geometry = ' '.join(geo_names)
render.par.bgcolora = 0
for nm, val in [('format', 'rgba16float'), ('antialias', 'aa4')]:
    try:
        render.par[nm] = val
    except Exception as ex:
        log.append('render %s: %s' % (nm, ex))

# ------------------------------------------------------------------ post: DOF -> fluid -> bloom -> OUT
dof = make(glslTOP, 'dof', 1300, -150)
dof.par.pixeldat = dofd.name
dof.inputConnectors[0].connect(render)
dof.par.vec0name = 'uDof'
dof.par.vec0valuex, dof.par.vec0valuey, dof.par.vec0valuez = 0.3, 0.38, 9.0

fluid = make(glslTOP, 'fluid', 1500, -150)
fluid.par.pixeldat = fld.name
fluid.inputConnectors[0].connect(dof)
fluid.par.vec0name = 'uF'
fluid.par.vec0valuex.expr = "absTime.seconds"
fluid.par.vec0valuey, fluid.par.vec0valuez, fluid.par.vec0valuew = 0.004, 0.0025, 0.025
fluid.par.vec1name = 'uTint'
fluid.par.vec1valuex, fluid.par.vec1valuey, fluid.par.vec1valuez, fluid.par.vec1valuew = 0.012, 0.018, 0.03, 0.6

grade = make(levelTOP, 'grade', 1600, -250)          # exposure / filmic lift
grade.inputConnectors[0].connect(fluid)
for nm, val in [('brightness1', 1.12), ('gamma1', 1.05), ('contrast', 1.15)]:
    try:
        grade.par[nm] = val
    except Exception as ex:
        log.append('grade %s: %s' % (nm, ex))
last = grade
try:
    bloom = make(bloomTOP, 'bloom', 1700, -150)
    bloom.inputConnectors[0].connect(grade)
    for nm, val in [('bloomintensity', 0.6), ('bloomthreshold', 0.55)]:
        try:
            bloom.par[nm] = val
        except Exception as ex:
            log.append('bloom %s: %s' % (nm, ex))
    last = bloom
except Exception as ex:
    log.append('bloom: %s' % ex)
out = base.op('OUT')
out.inputConnectors[0].connect(last)
out.nodeX, out.nodeY = 1900, -150

log.append('built: %d cell variants, %d cell instances, %d particles' %
           (len(LIB), sum(COUNTS[e['kind']] for e in LIB), PARTICLES))
open('/tmp/neuron_diag.txt', 'w').write('\n'.join(log))
