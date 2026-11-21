"""
NEURON LIBRARY - realistic cortical cell morphologies for instancing
Blender 4.x / 5.x.  Builds several variants and exports each as a LOCAL OBJ
(soma at origin, Y-up) + library.json for TouchDesigner instancing.

Variants
  pyramidal_*  : teardrop soma, thick apical dendrite with obliques + tuft,
                 5-7 basal dendrites, spiny, descending axon with collaterals + boutons
  stellate_*   : round soma, radial spiny dendrites, local axon
  astro_*      : protoplasmic astrocyte - small soma, dense bushy fine processes, endfeet
Units: 1 = ~40 um.  Branch radii follow Rall's 3/2 rule at bifurcations.
"""
import bpy, bmesh, math, random, json, os
from mathutils import Vector, Matrix, noise

OUT_DIR = os.path.expanduser("~/VJ-PROJECTS/NEURON_SCALE/geo/library")
EXPORT = True
SEED = 11

PLAN = [("pyramidal", 4), ("stellate", 3), ("astro", 3)]


# ------------------------------------------------------------------ helpers
def rand_perp(d):
    a = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    p = d.cross(a).normalized()
    return (Matrix.Rotation(random.uniform(0, math.tau), 3, d) @ p).normalized()


def deviate(d, angle_deg):
    p = rand_perp(d)
    return (Matrix.Rotation(math.radians(angle_deg), 3, p) @ d).normalized()


class Morph:
    def __init__(self):
        self.tubes = []    # list of [(co, r), ...]  (main arbor, smooth)
        self.spines = []   # tiny splines (low-res)

    # smooth, persistent random walk (tortuosity from coherent noise, not white noise)
    def grow(self, start, d, r0, length, depth, *, rmin=0.006, taper=0.75, branch_every=(0.35, 0.8),
             child_angle=(25, 50), spines=0.0, tort=0.35, gravity=None, bias_dir=None, end_bulb=False,
             boutons=False, flare=1.8):
        step = 0.05
        n = max(3, int(length / step))
        pts = []
        p, r = start.copy(), r0
        seed_off = Vector((random.uniform(0, 100), random.uniform(0, 100), random.uniform(0, 100)))
        next_branch = random.uniform(*branch_every)
        travelled = 0.0
        r_end = max(rmin, r0 * taper)
        for i in range(n + 1):
            t = i / n
            rr = r0 + (r_end - r0) * (t ** 0.7)
            if boutons and i % 9 == 4:
                rr *= 2.2
            rr *= 1.0 + 0.12 * noise.noise(seed_off + p * 9.0)   # natural calibre variation
            if i == 0:
                pts.append((p.copy(), rr * flare))    # flare where it leaves the parent
            else:
                pts.append((p.copy(), rr))
            if i == n:
                break
            wob = noise.noise_vector(seed_off + p * 1.7) * tort
            d = (d + wob * step * 4.0).normalized()
            if gravity is not None:
                d = (d + gravity * step * 0.6).normalized()
            if bias_dir is not None:
                d = (d + bias_dir * step * 0.8).normalized()
            p = p + d * step
            travelled += step
            # spines along thin dendrites
            if spines > 0 and rr < 0.05 and random.random() < spines:
                self.add_spine(p, d, rr)
            # bifurcation
            if depth > 0 and travelled >= next_branch and t < 0.85:
                travelled = 0.0
                next_branch = random.uniform(*branch_every)
                rc = max(rmin, rr * 0.79)              # Rall 3/2 rule
                ang = random.uniform(*child_angle)
                self.grow(p, deviate(d, ang), rc, length * (1 - t) * random.uniform(0.55, 0.9), depth - 1,
                          rmin=rmin, taper=taper, branch_every=branch_every, child_angle=child_angle,
                          spines=spines, tort=tort, gravity=gravity, bias_dir=bias_dir,
                          end_bulb=end_bulb, boutons=boutons, flare=1.15)
                d = deviate(d, ang * 0.4)
                r0 = rr * 0.85; r_end = max(rmin, r_end * 0.9)
        if end_bulb:
            q, rq = pts[-1]
            pts.append((q + d * 0.03, rq * 3.0))
            pts.append((q + d * 0.07, rq * 1.2))
        self.tubes.append(pts)

    def add_spine(self, p, d, r_dend):
        s = rand_perp(d)
        neck = random.uniform(0.025, 0.06)
        head = random.uniform(0.012, 0.02)
        base = p + s * r_dend * 0.7
        self.spines.append([(base, 0.007), (base + s * neck * 0.55, 0.0045),
                            (base + s * neck, head * 0.65), (base + s * (neck + head * 0.6), head),
                            (base + s * (neck + head * 1.25), head * 0.7), (base + s * (neck + head * 1.6), head * 0.15)])


def tubes_to_mesh(name, tube_list, bevel_res, res_u):
    cu = bpy.data.curves.new(name + "_c", 'CURVE')
    cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = bevel_res
    cu.resolution_u = res_u; cu.use_fill_caps = True
    for pts in tube_list:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for pt, (co, r) in zip(sp.points, pts):
            pt.co = (*co, 1.0); pt.radius = r
    ob = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.curves.remove(cu)
    return me


def soma_mesh(kind, r):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=r)
    for v in bm.verts:
        c = v.co
        if kind == "pyramidal":            # teardrop pointing into the apical dendrite (+Z)
            if c.z > 0:
                k = c.z / r
                c.x *= 1 - 0.55 * k; c.y *= 1 - 0.55 * k; c.z *= 1 + 0.9 * k
            else:
                c.z *= 0.8
        elif kind == "astro":
            c *= 1 + 0.15 * noise.noise(c * 9)
        c *= 1 + 0.06 * noise.noise(c * 6 + Vector((3, 1, 2)))
    return bm


# ------------------------------------------------------------------ cell types
def build(kind, idx):
    random.seed(SEED * 100 + idx * 7 + sum(map(ord, kind)) % 97)
    m = Morph()
    if kind == "pyramidal":
        rs = 0.22 * random.uniform(0.9, 1.15)
        up = Vector((0, 0, 1))
        # apical trunk: few branches until the tuft
        m.grow(Vector((0, 0, rs * 1.6)), deviate(up, 6), 0.07, random.uniform(4.0, 5.2), 2,
               taper=0.35, branch_every=(0.5, 1.0), child_angle=(35, 60), spines=0.55, tort=0.18,
               bias_dir=up * 0.4, rmin=0.008)
        # apical tuft
        tuft_base = Vector((0, 0, 0))
        for pts in m.tubes[-1:]:
            tuft_base = pts[-1][0]
        for _ in range(random.randint(3, 5)):
            m.grow(tuft_base, deviate(up, random.uniform(30, 70)), 0.025, random.uniform(0.8, 1.4), 2,
                   spines=0.6, tort=0.4, branch_every=(0.25, 0.5))
        # basal dendrites
        for _ in range(random.randint(5, 7)):
            d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.9, 0.1))).normalized()
            m.grow(d * rs * 0.8, d, 0.04, random.uniform(1.4, 2.2), 3, spines=0.55, tort=0.35,
                   branch_every=(0.2, 0.5))
        # axon: thin, long, collaterals at near-right angles, en passant boutons
        dn = Vector((0, 0, -1))
        m.grow(dn * rs * 0.8, deviate(dn, 8), 0.016, random.uniform(5, 7), 2, taper=0.9, rmin=0.009,
               branch_every=(1.2, 2.2), child_angle=(70, 90), tort=0.2, boutons=True)
        soma = soma_mesh(kind, rs); radius = 6.0
    elif kind == "stellate":
        rs = 0.18 * random.uniform(0.9, 1.1)
        for _ in range(random.randint(6, 9)):
            d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
            m.grow(d * rs * 0.85, d, 0.035, random.uniform(1.2, 1.9), 3, spines=0.45, tort=0.4,
                   branch_every=(0.2, 0.45))
        d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
        m.grow(d * rs * 0.8, d, 0.014, random.uniform(3, 4.5), 3, taper=0.9, rmin=0.008,
               branch_every=(0.6, 1.2), child_angle=(50, 85), tort=0.35, boutons=True)
        soma = soma_mesh(kind, rs); radius = 3.5
    else:  # protoplasmic astrocyte
        rs = 0.12 * random.uniform(0.9, 1.1)
        for _ in range(random.randint(14, 22)):
            d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
            m.grow(d * rs * 0.8, d, 0.025, random.uniform(0.6, 1.2), 4, taper=0.3, rmin=0.004,
                   branch_every=(0.08, 0.2), child_angle=(30, 70), tort=0.8,
                   end_bulb=random.random() < 0.3)
        soma = soma_mesh(kind, rs); radius = 1.6

    arbor = tubes_to_mesh(f"{kind}_{idx}", m.tubes, 2, 1)
    spines = tubes_to_mesh(f"{kind}_{idx}_sp", m.spines, 1, 2) if m.spines else None
    soma.from_mesh(arbor)
    if spines:
        soma.from_mesh(spines)
    me = bpy.data.meshes.new(f"{kind}_{idx}")
    soma.to_mesh(me); soma.free()
    bpy.data.meshes.remove(arbor)
    if spines:
        bpy.data.meshes.remove(spines)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(f"LIB_{kind}_{idx}", me)
    return ob, radius, len(m.spines)


def main():
    coll = bpy.data.collections.get("NEURON_LIBRARY") or bpy.data.collections.new("NEURON_LIBRARY")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    lib = []
    x = 0.0
    for kind, count in PLAN:
        for i in range(count):
            ob, radius, nsp = build(kind, i)
            coll.objects.link(ob)
            entry = {"name": ob.name, "kind": kind, "radius": radius, "verts": len(ob.data.vertices), "spines": nsp}
            if EXPORT:
                os.makedirs(OUT_DIR, exist_ok=True)
                path = os.path.join(OUT_DIR, ob.name + ".obj")
                bpy.ops.object.select_all(action='DESELECT')
                ob.select_set(True); bpy.context.view_layer.objects.active = ob
                bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True, apply_modifiers=False,
                                      export_materials=False, export_uv=False,
                                      forward_axis='NEGATIVE_Z', up_axis='Y')
                entry["file"] = path
            ob.location = (x, 0, 0); x += 4.0
            lib.append(entry)
    if EXPORT:
        json.dump(lib, open(os.path.join(OUT_DIR, "library.json"), "w"), indent=1)
    return lib


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
