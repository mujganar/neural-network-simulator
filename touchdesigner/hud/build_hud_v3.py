# HUD v3: floating frosted-glass panels (real blur in TD) + Synapse Mono font
#   OUT -> glass_blur ; glass(OUT, glass_blur) ; hud over glass -> ig_comp -> OUT_IG
ROOT = '/Users/mujganar/VJ-PROJECTS/NEURON_SCALE/td/hud'
b = op('/project1/neuron_scale')
log = []
# panel rectangles in HUD pixels (x, y, w, h) - keep in sync with RECT in hud.html
RECTS = [(20, 168, 262, 214), (438, 168, 262, 150), (438, 330, 262, 150), (110, 1022, 500, 150)]

GLASS = r"""
uniform vec4 uR0; uniform vec4 uR1; uniform vec4 uR2; uniform vec4 uR3;
uniform vec4 uG;     // radius, brightness, refraction px, unused
out vec4 fragColor;
float sdr(vec2 p, vec4 r, float rad) {
    vec2 c = r.xy + r.zw * 0.5;
    vec2 q = abs(p - c) - r.zw * 0.5 + rad;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - rad;
}
float D(vec2 p) { return min(min(sdr(p, uR0, uG.x), sdr(p, uR1, uG.x)), min(sdr(p, uR2, uG.x), sdr(p, uR3, uG.x))); }
void main() {
    vec2 res = uTD2DInfos[0].res.zw;
    vec2 uv = vUV.st;
    vec2 p = vec2(uv.x * res.x, (1.0 - uv.y) * res.y);      // HUD pixel space (y down)
    float d = D(p);
    vec4 sharp = texture(sTD2DInputs[0], uv);
    float inside = smoothstep(1.0, -1.0, d);
    vec2 grad = normalize(vec2(D(p + vec2(1.0, 0.0)) - D(p - vec2(1.0, 0.0)), D(p + vec2(0.0, 1.0)) - D(p - vec2(0.0, 1.0))) + 1e-5);
    float rim = smoothstep(-22.0, 0.0, d) * inside;           // lens-like bend near the edge
    vec2 off = -grad * rim * uG.z;
    vec3 bl = texture(sTD2DInputs[1], uv + vec2(off.x, -off.y) / res).rgb;
    vec3 glass = bl * uG.y + vec3(0.012, 0.016, 0.026);
    fragColor = TDOutputSwizzle(vec4(mix(sharp.rgb, glass, inside), 1.0));
}
"""

for nm in ('glass', 'glass_blur', 'shader_glass'):
    o = b.op(nm)
    if o is not None and o.valid:
        o.destroy()

out = b.op('OUT'); comp = b.op('ig_comp')
sh = b.create(textDAT, 'shader_glass'); sh.text = GLASS
sh.nodeX, sh.nodeY = -200, -430

bl = b.create(blurTOP, 'glass_blur')
bl.nodeX, bl.nodeY = 2600, 50
bl.inputConnectors[0].connect(out)
for nm, val in (('size', 22), ('type', 'gaussian')):
    try:
        bl.par[nm] = val
    except Exception as ex:
        log.append('blur %s: %s' % (nm, ex))

gl = b.create(glslTOP, 'glass')
for d in list(getattr(gl, 'docked', [])):
    try: d.destroy()
    except Exception: pass
gl.nodeX, gl.nodeY = 2600, 300
gl.par.pixeldat = sh.name
gl.inputConnectors[0].connect(out)
gl.inputConnectors[1].connect(bl)
for i, r in enumerate(RECTS):
    gl.par['vec%dname' % i] = 'uR%d' % i
    for ax, v in zip('xyzw', r):
        gl.par['vec%dvalue%s' % (i, ax)] = v
gl.par.vec4name = 'uG'
gl.par.vec4valuex, gl.par.vec4valuey, gl.par.vec4valuez = 14, 0.78, 6

comp.inputConnectors[1].connect(gl)
comp.nodeX, comp.nodeY = 2800, 300
b.op('OUT_IG').nodeX, b.op('OUT_IG').nodeY = 3000, 300
b.op('hud').nodeX, b.op('hud').nodeY = 2600, 500
b.op('hud').par.reload.pulse()
open('/tmp/neuron_diag.txt', 'w').write('\n'.join(log) or 'hud v3 ok')
