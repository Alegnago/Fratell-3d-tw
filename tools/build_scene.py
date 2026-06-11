# Genera fratelli_city[_v2].glb + scene[_v2].blend
# Run: /Applications/Blender.app/Contents/MacOS/Blender --background --python tools/build_scene.py -- --version 2
import bpy
import bmesh
import math
import random
import os
import sys

VERSION = 2
if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
    if '--version' in args:
        VERSION = int(args[args.index('--version') + 1])

random.seed(7)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

SUFFIX = "" if VERSION == 1 else "_v2"

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = bpy.context.collection

# ---------------------------------------------------------------- mesh helpers
CUBE_V = [(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),
          (-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]
CUBE_F = [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]

class Builder:
    def __init__(self):
        self.verts = []
        self.faces = []

    def _emit(self, vs, fs):
        off = len(self.verts)
        self.verts.extend(vs)
        self.faces.extend(tuple(i + off for i in f) for f in fs)

    def box(self, cx, cy, cz, sx, sy, sz, rot=0.0):
        c, s = math.cos(rot), math.sin(rot)
        vs = []
        for x, y, z in CUBE_V:
            x, y, z = x * sx, y * sy, z * sz
            vs.append((cx + x * c - y * s, cy + x * s + y * c, cz + z))
        self._emit(vs, CUBE_F)

    def prism(self, cx, cy, cz, sx, sy, sz, rot=0.0):
        # prisma triangolare (dente di sega / tenda), cresta lato +y
        vs0 = [(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0),(-.5,.5,1),(.5,.5,1)]
        fs = [(0,1,2,3),(0,3,4),(1,5,2),(3,2,5,4),(0,4,5,1)]
        c, s = math.cos(rot), math.sin(rot)
        vs = []
        for x, y, z in vs0:
            x, y, z = x * sx, y * sy, z * sz
            vs.append((cx + x * c - y * s, cy + x * s + y * c, cz + z))
        self._emit(vs, fs)

    def gable(self, cx, cy, cz, sx, sy, sz, rot=0.0):
        # tetto a capanna, colmo lungo x
        vs0 = [(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0),(-.5,0,1),(.5,0,1)]
        fs = [(0,1,2,3),(0,1,5,4),(2,3,4,5),(0,4,3),(1,2,5)]
        c, s = math.cos(rot), math.sin(rot)
        vs = []
        for x, y, z in vs0:
            x, y, z = x * sx, y * sy, z * sz
            vs.append((cx + x * c - y * s, cy + x * s + y * c, cz + z))
        self._emit(vs, fs)

    def cylinder(self, cx, cy, cz, r, h, seg=10, r_top=None):
        if r_top is None:
            r_top = r
        vs, fs = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((cx + r * math.cos(a), cy + r * math.sin(a), cz))
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((cx + r_top * math.cos(a), cy + r_top * math.sin(a), cz + h))
        for i in range(seg):
            j = (i + 1) % seg
            fs.append((i, j, seg + j, seg + i))
        fs.append(tuple(range(seg - 1, -1, -1)))
        fs.append(tuple(range(seg, 2 * seg)))
        self._emit(vs, fs)

    def tube(self, p0, p1, r=0.03, seg=4):
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        if L < 1e-6:
            return
        ux, uy, uz = dx / L, dy / L, dz / L
        if abs(uz) < 0.9:
            ax, ay, az = -uy, ux, 0
        else:
            ax, ay, az = 1, 0, 0
        n = math.sqrt(ax * ax + ay * ay + az * az)
        ax, ay, az = ax / n, ay / n, az / n
        bx = uy * az - uz * ay
        by = uz * ax - ux * az
        bz = ux * ay - uy * ax
        vs, fs = [], []
        for t, (px, py, pz) in ((0, p0), (1, p1)):
            for i in range(seg):
                ang = 2 * math.pi * i / seg
                ca, sa = math.cos(ang) * r, math.sin(ang) * r
                vs.append((px + ax * ca + bx * sa, py + ay * ca + by * sa, pz + az * ca + bz * sa))
        for i in range(seg):
            j = (i + 1) % seg
            fs.append((i, j, seg + j, seg + i))
        self._emit(vs, fs)

    def sphere(self, cx, cy, cz, r, sub=2, squash=1.0):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
        vs = [(cx + v.co.x, cy + v.co.y, cz + v.co.z * squash) for v in bm.verts]
        fs = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        self._emit(vs, fs)

    def to_object(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        return ob


# ---------------------------------------------------------------- componenti
def windows_grid(b, face_x, face_y, face_z, w, h, cols, rows, axis, rot=0.0,
                 gap_x=None, gap_z=None, depth=0.06):
    gx = gap_x if gap_x else w * 0.55
    gz = gap_z if gap_z else h * 0.7
    total_w = cols * w + (cols - 1) * gx
    total_h = rows * h + (rows - 1) * gz
    for i in range(cols):
        for j in range(rows):
            ox = -total_w / 2 + w / 2 + i * (w + gx)
            oz = -total_h / 2 + h / 2 + j * (h + gz)
            c, s = math.cos(rot), math.sin(rot)
            if axis == 'y':
                lx, ly = ox, 0
            else:
                lx, ly = 0, ox
            wx = face_x + lx * c - ly * s
            wy = face_y + lx * s + ly * c
            if axis == 'y':
                b.box(wx, wy, face_z + oz, w, depth, h, rot)
            else:
                b.box(wx, wy, face_z + oz, depth, w, h, rot)


def slat_facade(b, cx, cy, z0, z1, width, axis, n=None, fin=0.07, depth=0.18):
    if n is None:
        n = max(2, int(width / 0.55))
    for i in range(n):
        o = -width / 2 + width * (i + 0.5) / n
        if axis == 'y':
            b.box(cx + o, cy, (z0 + z1) / 2, fin, depth, z1 - z0)
        else:
            b.box(cx, cy + o, (z0 + z1) / 2, depth, fin, z1 - z0)


def tree(b, x, y, scale=1.0, lollipop=True):
    h = 3.0 * scale
    b.cylinder(x, y, 0, 0.14 * scale, h, seg=6)
    if lollipop:
        b.sphere(x, y, h + 1.3 * scale, 1.7 * scale, sub=2, squash=0.95)
    else:
        b.sphere(x, y, h + 1.0 * scale, 1.5 * scale, sub=2, squash=0.8)
        b.sphere(x + 0.8 * scale, y + 0.3 * scale, h + 0.4 * scale, 1.0 * scale, sub=2)


def truck(b, x, y, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return x + lx * c - ly * s, y + lx * s + ly * c
    px, py = at(-0.9, 0)
    b.box(px, py, 1.5, 3.6, 2.0, 2.2, rot)
    px, py = at(1.8, 0)
    b.box(px, py, 1.05, 1.5, 1.9, 1.5, rot)
    for lx in (-2.0, -0.3, 1.9):
        for ly in (-0.95, 0.95):
            px, py = at(lx, ly)
            b.box(px, py, 0.38, 0.7, 0.25, 0.76, rot)


def car(b, x, y, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return x + lx * c - ly * s, y + lx * s + ly * c
    b.box(x, y, 0.72, 4.2, 1.8, 1.0, rot)            # corpo
    px, py = at(-0.3, 0)
    b.box(px, py, 1.55, 2.2, 1.65, 0.75, rot)        # abitacolo
    for lx in (-1.35, 1.35):
        for ly in (-0.85, 0.85):
            px, py = at(lx, ly)
            b.box(px, py, 0.3, 0.62, 0.2, 0.6, rot)


def pallet_stack(b, x, y, rot=0.0, n=3):
    for i in range(n):
        b.box(x, y, 0.12 + i * 0.16, 1.5, 1.2, 0.12, rot)
    b.box(x, y, 0.12 + n * 0.16 + 0.25, 1.3, 1.0, 0.5, rot)  # carico


def dumpster(b, x, y, rot=0.0):
    b.box(x, y, 0.7, 1.9, 1.1, 1.2, rot)
    b.prism(x, y, 1.3, 1.9, 1.1, 0.3, rot)


def bush(b, x, y, r=1.0):
    b.sphere(x, y, r * 0.55, r, sub=2, squash=0.62)


def ext_stair(b, x, y, rot=0.0, h=3.0, n=9, w=1.1):
    # scala esterna metallica: sale lungo +x locale, pianerottolo in cima
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return x + lx * c - ly * s, y + lx * s + ly * c
    run = 0.34
    for i in range(n):
        px, py = at((i + 0.5) * run, 0)
        b.box(px, py, (i + 0.7) * h / n, run, w, h / n * 0.55, rot)
    px, py = at(n * run + 0.55, 0)
    b.box(px, py, h + 0.04, 1.1, w, 0.09, rot)            # pianerottolo
    for ly in (-w / 2, w / 2):                            # corrimano
        p0 = at(0.2, ly)
        p1 = at(n * run, ly)
        b.tube((p0[0], p0[1], 1.0), (p1[0], p1[1], 1.0 + h), r=0.025)
        p2 = at(n * run + 1.05, ly)
        b.tube((p1[0], p1[1], 1.0 + h), (p2[0], p2[1], 1.0 + h), r=0.025)
        for lx, zb in ((0.3, 0.15), (n * run * 0.55, h * 0.55), (n * run + 0.9, h)):
            pp = at(lx, ly)
            b.tube((pp[0], pp[1], zb), (pp[0], pp[1], zb + 1.0), r=0.02)


def flat_sign(b, x, y, z_top, h=4.0, w=0.7, rot=0.0):
    # insegna verticale piatta a muro con listelli (ideogrammi astratti)
    c, s = math.cos(rot), math.sin(rot)
    b.box(x, y, z_top - h / 2, abs(c) * w + abs(s) * 0.14, abs(s) * w + abs(c) * 0.14, h, 0)
    n = int(h / 0.7)
    for i in range(n):
        z = z_top - h + h * (i + 0.5) / n
        b.box(x - s * 0.1, y + c * 0.1, z, abs(c) * w * 0.6 + abs(s) * 0.05, abs(s) * w * 0.6 + abs(c) * 0.05, 0.4)


def dark_tank(b, x, y, z, r=1.15, h=2.3):
    # serbatoio tondo su gambe corte
    for ang in range(3):
        a = ang * 2 * math.pi / 3
        b.box(x + 0.6 * math.cos(a), y + 0.6 * math.sin(a), z + 0.3, 0.14, 0.14, 0.6)
    b.cylinder(x, y, z + 0.6, r, h, seg=12)
    b.cylinder(x, y, z + 0.6 + h, r * 0.35, 0.3, seg=8)


def roller_shutter(b, x, y, z0, w, h, rot=0.0):
    # saracinesca: doghe orizzontali impilate
    c, s = math.cos(rot), math.sin(rot)
    n = max(3, int(h / 0.38))
    for i in range(n):
        z = z0 + h * (i + 0.5) / n
        b.box(x, y, z, w, 0.08, h / n * 0.78, rot)
    # guide laterali
    for o in (-w / 2 - 0.12, w / 2 + 0.12):
        b.box(x + o * c, y + o * s, z0 + h / 2, 0.18, 0.16, h, rot)
    b.box(x, y, z0 + h + 0.18, w + 0.6, 0.3, 0.35, rot)  # cassonetto


def water_tank(b, x, y, z):
    for ang in range(4):
        a = math.pi / 4 + ang * math.pi / 2
        b.box(x + 0.55 * math.cos(a), y + 0.55 * math.sin(a), z + 0.55, 0.12, 0.12, 1.1)
    b.cylinder(x, y, z + 1.1, 0.85, 1.5, seg=10)
    b.cylinder(x, y, z + 2.6, 0.85, 0.18, seg=10, r_top=0.15)


def ac_units(b, x, y, z, n=3):
    for i in range(n):
        b.box(x + (i - (n - 1) / 2) * 1.1, y, z + 0.35, 0.8, 0.45, 0.7)


def power_pole(b, x, y, h=7.0):
    b.cylinder(x, y, 0, 0.1, h, seg=6)
    b.box(x, y, h - 0.5, 1.8, 0.09, 0.09)
    b.box(x, y, h - 1.4, 1.4, 0.09, 0.09)


def sign_board(b, x, y, z_top, rot=0.0, w=1.1, h=4.2, depth=0.35):
    b.box(x, y, z_top - h / 2, w, depth, h, rot)
    c, s = math.cos(rot), math.sin(rot)
    n = int(h / 0.9)
    for i in range(n):
        z = z_top - h + h * (i + 0.5) / n
        b.box(x - s * (depth / 2), y + c * (depth / 2), z, w * 0.72, 0.06, 0.5, rot)


def flag_sign(b, x, y, z_top, rot=0.0, h=3.0, w=0.85, out=1.1):
    # insegna a bandiera: sporge ortogonale alla facciata (stile Taipei)
    # rot = direzione "fuori dalla facciata"
    c, s = math.cos(rot), math.sin(rot)
    # braccio
    b.tube((x, y, z_top - 0.15), (x + c * out, y + s * out, z_top - 0.15), r=0.05)
    # cassonetto verticale appeso al braccio
    cxx, cyy = x + c * (out * 0.75), y + s * (out * 0.75)
    b.box(cxx, cyy, z_top - h / 2, abs(c) * 0.18 + abs(s) * w, abs(s) * 0.18 + abs(c) * w, h)
    n = int(h / 0.75)
    for i in range(n):
        z = z_top - h + h * (i + 0.5) / n
        b.box(cxx + s * 0.12, cyy - c * 0.12, z, abs(c) * 0.06 + abs(s) * w * 0.66, abs(s) * 0.06 + abs(c) * w * 0.66, 0.42)


def clothesline(b, x, y, z, length=3.0, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    p0 = (x - c * length / 2, y - s * length / 2, z)
    p1 = (x + c * length / 2, y + s * length / 2, z)
    for p in (p0, p1):
        b.tube((p[0], p[1], z - 1.4), (p[0], p[1], z + 0.1), r=0.04)
    for dz in (0.0, -0.25):
        b.tube((p0[0], p0[1], z + dz), (p1[0], p1[1], z + dz), r=0.015)
    # panni appesi
    n = 3
    for i in range(n):
        t = (i + 0.7) / (n + 0.7)
        px, py = x + c * (t - 0.5) * length, y + s * (t - 0.5) * length
        b.box(px, py, z - 0.45, abs(c) * 0.5 + abs(s) * 0.06, abs(s) * 0.5 + abs(c) * 0.06, 0.8)


def antenna(b, x, y, z, h=2.2):
    b.tube((x, y, z), (x, y, z + h), r=0.03)
    b.tube((x - 0.4, y, z + h * 0.75), (x + 0.4, y, z + h * 0.75), r=0.02)
    b.tube((x - 0.3, y, z + h * 0.55), (x + 0.3, y, z + h * 0.55), r=0.02)


def roof_shack(b, x, y, z, rnd):
    w, d, h = rnd.uniform(2.2, 3.4), rnd.uniform(1.8, 2.6), rnd.uniform(1.6, 2.0)
    b.box(x, y, z + h / 2, w, d, h)
    b.prism(x, y, z + h, w * 1.08, d * 1.1, 0.5)


def roof_clutter(b, x, y, z, w, d, rnd):
    # tetto vissuto: serbatoio, antenne, AC, stenditoio, baracca
    if rnd.random() < 0.75:
        water_tank(b, x + rnd.uniform(-w / 4, w / 4), y + rnd.uniform(-d / 4, d / 4), z)
    if rnd.random() < 0.7:
        antenna(b, x + rnd.uniform(-w / 3, w / 3), y + rnd.uniform(-d / 3, d / 3), z, h=rnd.uniform(1.6, 3.0))
    if rnd.random() < 0.5:
        clothesline(b, x + rnd.uniform(-w / 4, w / 4), y + rnd.uniform(-d / 4, d / 4), z + 1.5, rot=rnd.uniform(0, math.pi))
    if rnd.random() < 0.45:
        roof_shack(b, x + rnd.uniform(-w / 5, w / 5), y + rnd.uniform(-d / 5, d / 5), z, rnd)
    if rnd.random() < 0.5:
        ac_units(b, x, y + d / 4, z, n=2)


def scooter(b, x, y, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return x + lx * c - ly * s, y + lx * s + ly * c
    for lx in (-0.55, 0.55):
        px, py = at(lx, 0)
        b.box(px, py, 0.22, 0.44, 0.12, 0.44, rot)  # ruota
    px, py = at(0, 0)
    b.box(px, py, 0.55, 1.3, 0.32, 0.35, rot)       # corpo
    px, py = at(0.55, 0)
    b.tube((px, py, 0.6), (px - c * 0.1, py - s * 0.1, 1.15), r=0.04)  # sterzo
    px, py = at(0.5, 0)
    b.box(px, py, 1.18, 0.1, 0.5, 0.08, rot)        # manubrio
    px, py = at(-0.35, 0)
    b.box(px, py, 0.82, 0.55, 0.3, 0.1, rot)        # sella


def stall(b, x, y, rot=0.0):
    # bancarella: banco + 2 montanti + tenda inclinata
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return x + lx * c - ly * s, y + lx * s + ly * c
    b.box(x, y, 0.55, 2.4, 1.2, 1.1, rot)
    for lx in (-1.05, 1.05):
        px, py = at(lx, 0.5)
        b.tube((px, py, 0), (px, py, 2.3), r=0.04)
    px, py = at(0, 0.25)
    b.prism(px, py, 2.05, 2.8, 1.6, 0.45, rot + math.pi)
    b.box(x, y, 1.35, 1.8, 0.8, 0.5, rot)  # merce


def hedge(b, x, y, length, rot=0.0, h=0.9):
    b.box(x, y, h / 2, length, 0.8, h, rot)


def planter(b, x, y, scale=0.6):
    b.box(x, y, 0.3, 0.9, 0.9, 0.6)
    tree(b, x, y, scale=scale, lollipop=True)


def flagpole(b, x, y, h=9.0):
    b.cylinder(x, y, 0, 0.07, h, seg=6)
    b.box(x + 0.65, y, h - 0.45, 1.3, 0.04, 0.8)


def gantry_crane(b, x, y, rot=0.0, span=10.0, h=6.5):
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return x + lx * c - ly * s, y + lx * s + ly * c
    for side in (-1, 1):
        for leg in (-1, 1):
            px, py = at(side * span / 2 + leg * 1.2, 0)
            qx, qy = at(side * span / 2, 0)
            b.tube((px, py, 0), (qx, qy, h), r=0.14, seg=4)
        px, py = at(side * span / 2 - 1.2, 0)
        qx, qy = at(side * span / 2 + 1.2, 0)
        b.box((px + qx) / 2, (py + qy) / 2, 0.15, 3.0, 0.5, 0.3, rot)
    px, py = at(-span / 2, 0)
    qx, qy = at(span / 2, 0)
    b.box((px + qx) / 2, (py + qy) / 2, h + 0.3, span + 2.4, 0.5, 0.6, rot)
    tx, ty = at(span * 0.18, 0)
    b.box(tx, ty, h - 0.1, 0.9, 0.7, 0.5, rot)
    b.tube((tx, ty, h - 0.3), (tx, ty, h - 2.0), r=0.03, seg=4)
    b.box(tx, ty, h - 2.2, 0.5, 0.4, 0.3, rot)


def chimney(b, x, y, h, r=0.8):
    b.cylinder(x, y, 0, r, h, seg=10, r_top=r * 0.72)
    b.cylinder(x, y, h, r * 0.78, 0.5, seg=10)


def fence(b, x, y, length, rot=0.0, h=2.2):
    b.box(x, y, h / 2, length, 0.12, h, rot)
    b.box(x, y, h + 0.06, length, 0.2, 0.12, rot)
    c, s = math.cos(rot), math.sin(rot)
    n = int(length / 2.4)
    for i in range(n + 1):
        o = -length / 2 + length * i / max(n, 1)
        b.box(x + o * c, y + o * s, h / 2, 0.16, 0.22, h, rot)


# ---------------------------------------------------------------- Fratelli HQ
def build_hq_v1(b):
    # palazzo originale (mockup) — invariato
    b.box(0, 0, 0.15, 34, 26, 0.3)
    b.box(0, -14.2, 0.08, 12, 3.0, 0.16)
    for i in range(4):
        b.box(0, -12.6 + i * 0.55, 0.34 + i * 0.14, 10 - i * 0.8, 0.7, 0.14)

    b.box(9.5, 2.0, 0.3 + 4.5, 13, 11, 9)
    windows_grid(b, 9.5, 2.0 - 5.5, 5.6, 1.05, 1.5, 5, 2, axis='y', gap_x=0.85, gap_z=1.6)
    windows_grid(b, 9.5 + 6.5, 2.0, 5.6, 1.05, 1.5, 4, 2, axis='x', gap_x=0.9, gap_z=1.6)
    b.box(9.5, 2.0, 9.55, 13.5, 11.5, 0.5)

    b.box(-1.5, 0.5, 0.3 + 6.0, 11, 9, 12)
    slat_facade(b, -1.5, 0.5 - 4.62, 2.6, 12.0, 10.2, axis='y')
    slat_facade(b, -1.5 - 5.62, 0.5, 2.6, 12.0, 8.2, axis='x')
    b.box(-1.5, 0.5, 12.55, 11.6, 9.6, 0.5)
    b.box(-1.5, 0.5 - 4.0, 1.55, 9.5, 1.6, 2.5)
    windows_grid(b, -1.5, 0.5 - 4.85, 1.55, 1.3, 1.9, 4, 1, axis='y', gap_x=0.6)

    b.box(-11.5, 1.5, 0.3 + 3.0, 9, 10, 6)
    slat_facade(b, -11.5, 1.5 - 5.12, 0.4, 6.0, 8.2, axis='y', fin=0.05, depth=0.12)
    slat_facade(b, -11.5 - 4.62, 1.5, 0.4, 6.0, 9.2, axis='x', fin=0.05, depth=0.12)
    b.box(-11.5, 1.5, 6.5, 9.5, 10.5, 0.4)

    b.box(-3.0, 1.5, 13.6, 6.5, 5.5, 2.2)
    b.box(-3.0, 1.5, 14.9, 7.0, 6.0, 0.4)
    b.box(7.0, 4.0, 10.7, 4.5, 4.0, 1.8)
    ac_units(b, 11.5, 5.5, 9.8, n=2)
    water_tank(b, -13.0, 4.0, 6.7)
    for x, y in ((-15.5, -10.5), (15.5, -10.5), (-16.0, 8.0), (16.0, 9.5), (4.5, -11.5)):
        tree(b, x, y, scale=1.0, lollipop=True)
    # logo sul fronte torre
    return (-1.5, 0.5 - 4.62 - 0.16, 7.6, 4.4)


def build_hq_v2(b):
    # sede reale (Street View Glory Wheel, Taichung) — riproduzione fedele:
    # uffici bianchi, volume nero alto 2 livelli con logo, capannone con
    # saracinesca + canopy scuro + insegna verticale, scala esterna,
    # serbatoio tondo scuro sul tetto, piazzale con stalli/SUV/scooter
    plaza_w, plaza_d = 56, 44
    hw, hd = plaza_w / 2, plaza_d / 2
    b.box(0, 0, 0.15, plaza_w, plaza_d, 0.3)
    b.box(5, -hd - 1.2, 0.08, 12, 3.0, 0.16)   # raccordo carraio centrale
    b.box(23, -hd - 1.2, 0.08, 6, 3.0, 0.16)   # raccordo carraio destro

    # ============ UFFICI (centro-destra): 2 piani + tetto praticabile
    b.box(8.0, 4.0, 0.3 + 4.25, 20, 14, 8.5)
    b.box(8.0, 4.0, 9.3, 20.5, 14.5, 0.45)                # coping
    b.box(8.0, 4.0 - 7.2, 9.95, 19.5, 0.1, 0.85)          # parapetto tetto fronte
    b.box(8.0 + 10.2, 4.0, 9.95, 0.1, 13.5, 0.85)         # parapetto lato dx
    # piano terra: ingresso vetrato centrato sotto il volume nero
    windows_grid(b, 5.0, 4.0 - 7.05, 1.65, 1.35, 2.7, 5, 1, axis='y', gap_x=0.3)
    b.box(5.0, -3.55, 3.25, 9.0, 1.7, 0.18)               # pensilina sottile
    # nastro vetri livello 2 a destra del volume nero + lato destro
    windows_grid(b, 15.5, 4.0 - 7.05, 6.3, 1.35, 1.25, 3, 1, axis='y', gap_x=0.45)
    windows_grid(b, 8.0 + 10.05, 4.0, 6.3, 1.3, 1.25, 5, 1, axis='x', gap_x=0.65)
    # volume tecnico arretrato sul tetto
    b.box(12.0, 8.0, 9.3 + 1.3, 7, 5, 2.6)
    b.box(12.0, 8.0, 12.05, 7.5, 5.5, 0.3)
    ac_units(b, 3.0, 8.0, 9.5, n=2)

    # ============ VOLUME NERO "GW": alto 2 livelli, a sbalzo sul fronte
    b.box(5.5, -3.6, 6.55, 13, 2.8, 5.1)                  # corpo z 4.0..9.1
    slat_facade(b, 5.5, -3.6 - 1.47, 4.15, 9.0, 12.6, axis='y', n=42, fin=0.07, depth=0.14)
    slat_facade(b, 5.5 - 6.54, -3.6, 4.15, 9.0, 2.5, axis='x', n=8, fin=0.07, depth=0.14)
    slat_facade(b, 5.5 + 6.54, -3.6, 4.15, 9.0, 2.5, axis='x', n=8, fin=0.07, depth=0.14)
    b.box(5.5, -3.6, 9.25, 13.4, 3.2, 0.35)               # bordo bianco sommitale
    b.box(5.5, -5.14, 7.4, 5.4, 0.1, 3.3)                 # pannello insegna liscio sul nero

    # ============ CAPANNONE SINISTRO: saracinesca, canopy, insegna, scala
    b.box(-13.5, 3.0, 0.3 + 2.9, 15, 14, 5.8)
    b.gable(-13.5, 3.0, 6.1, 15.5, 14.8, 1.5)
    roller_shutter(b, -15.0, 3.0 - 7.06, 0.45, 6.0, 3.8)
    # canopy scuro inclinato sopra la saracinesca + tiranti
    b.prism(-15.0, -5.05, 4.85, 8.2, 2.1, 1.05, rot=math.pi)
    for xx in (-18.6, -11.4):
        b.tube((xx, -4.15, 5.8), (xx, -6.0, 5.05), r=0.04)
    # insegna verticale a muro con ideogrammi (tra saracinesca e uffici)
    flat_sign(b, -10.6, -4.06, 5.2, h=4.4, w=0.75)
    # scala esterna metallica con pianerottolo (lato sinistro fronte)
    ext_stair(b, -20.6, -2.2, rot=math.pi / 2, h=3.1, n=9)
    pallet_stack(b, -19.6, -5.6, rot=0.2)
    pallet_stack(b, -17.8, -6.3, rot=-0.15, n=2)
    # pluviali
    for xx in (-20.8, -6.3):
        b.tube((xx, -4.0, 0.4), (xx, -4.0, 5.9), r=0.07)
    # tetto: penthouse bianco + serbatoio tondo scuro + tubi
    b.box(-10.5, 6.5, 6.7, 5.5, 4.5, 2.1)
    dark_tank(b, -17.0, 5.0, 6.9)
    b.tube((-17.0, 5.0, 6.9), (-13.2, 6.5, 6.9), r=0.06)
    chimney(b, -7.5, 9.0, 9.2, r=0.4)

    # ============ ALA DESTRA: capannone basso + muro con cancello carraio
    b.box(24.0, 9.0, 0.3 + 2.25, 8, 11, 4.5)
    b.prism(24.0, 9.0, 4.75, 8.3, 11.5, 1.2)
    # muro di confine con apertura cancello (x 20.5..26 varco)
    b.box(19.2, -3.0, 1.55, 2.4, 0.35, 2.5)
    b.box(27.2, -3.0, 1.55, 1.6, 0.35, 2.5)
    # blocco insegna in pietra con targa (a destra del cancello)
    b.box(26.8, -5.8, 1.05, 2.8, 0.9, 2.0)
    b.box(26.8, -6.32, 1.15, 2.2, 0.08, 1.2)

    # ============ CAPANNONE RETRO a dente di sega
    b.box(0.0, 16.0, 0.3 + 2.65, 38, 9, 5.3)
    for i in range(5):
        b.prism(-15.2 + i * 7.6, 16.0, 5.95, 7.6, 9, 1.7)
    b.tube((15.0, 16.0, 6.0), (15.0, 16.0, 9.2), r=0.3)
    water_tank(b, -12.0, 17.5, 7.7)

    # ============ PIAZZALE
    for i in range(5):                                     # stalli dipinti
        b.box(2.0 + i * 3.0, -13.5, 0.33, 0.14, 5.6, 0.04)
    car(b, 14.8, -7.6, rot=math.pi / 2)                    # SUV vicino agli uffici
    car(b, 9.6, -12.6, rot=math.pi / 2)
    truck(b, 22.8, -13.5, rot=math.pi / 2)
    for i in range(8):                                     # fila scooter fronte-sinistra
        scooter(b, -25.0 + i * 1.55, -18.6, rot=math.pi / 2 + 0.1 * (i % 3 - 1))
    dumpster(b, -5.5, -8.6, rot=0.15)
    pallet_stack(b, -8.0, -8.2, rot=0.4, n=2)

    # ============ CONFINE: muretto basso + varchi, siepi, verde
    b.box(-15.5, -hd + 0.2, 0.75, 25, 0.4, 1.5)            # muretto sx
    b.box(14.5, -hd + 0.2, 0.75, 7, 0.4, 1.5)              # muretto tra i varchi
    fence(b, -hw + 0.2, 0, plaza_d * 0.86, rot=math.pi / 2, h=1.7)
    fence(b, hw - 0.2, 6, plaza_d * 0.6, rot=math.pi / 2, h=1.7)
    fence(b, 0, hd - 0.2, plaza_w * 0.92, rot=0, h=1.7)
    # siepi tonde in fioriera ai lati dell'ingresso vetrato
    for x, y in ((0.2, -6.2), (10.0, -6.2)):
        b.box(x, y, 0.5, 2.6, 1.3, 0.5)
        bush(b, x - 0.5, y, r=0.95)
        bush(b, x + 0.6, y + 0.1, r=0.8)
    planter(b, 12.2, -6.0, scale=0.55)
    # cespugli lungo il fronte sinistro + grande albero d'angolo
    for i in range(5):
        bush(b, -26.5 + i * 2.1, -20.2, r=1.05)
    tree(b, -25.5, -16.0, scale=1.35, lollipop=False)
    # alberi dietro il muro destro e sul retro
    for y in (0, 7):
        tree(b, hw - 2.2, y, scale=0.95, lollipop=False)
    for x in (-22, -14, 8, 16, 24):
        tree(b, x, hd - 2.6, scale=1.0, lollipop=False)
    # logo sul pannello insegna del volume nero
    return (5.5, -5.14 - 0.08, 5.95, 2.9)


def build_fratelli():
    b = Builder()
    if VERSION == 1:
        logo_x, logo_y, logo_z, logo_s = build_hq_v1(b)
    else:
        logo_x, logo_y, logo_z, logo_s = build_hq_v2(b)

    ob = b.to_object("Fratelli_HQ")

    # logo plane con UV
    lb = bpy.data.meshes.new("Logo")
    s_w = s_h = logo_s
    lb.from_pydata(
        [(logo_x - s_w / 2, logo_y, logo_z), (logo_x + s_w / 2, logo_y, logo_z),
         (logo_x + s_w / 2, logo_y, logo_z + s_h), (logo_x - s_w / 2, logo_y, logo_z + s_h)],
        [], [(0, 1, 2, 3)])
    uv = lb.uv_layers.new(name="UVMap")
    for li, co in zip(lb.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[li.index].uv = co
    lb.validate(); lb.update()
    lob = bpy.data.objects.new("Logo", lb)
    col.objects.link(lob)
    return ob


# ---------------------------------------------------------------- city blocks
def fence_block(b, cx, cy, rot, half):
    fence(b, cx, cy - half, 2 * half * 0.92, rot=rot)
    fence(b, cx, cy + half, 2 * half * 0.92, rot=rot)
    fence(b, cx - half, cy, 2 * half * 0.92, rot=rot + math.pi / 2)
    fence(b, cx + half, cy, 2 * half * 0.92, rot=rot + math.pi / 2)


def block_factory(b, cx, cy, rot):
    c, s = math.cos(rot), math.sin(rot)
    def at(lx, ly):
        return cx + lx * c - ly * s, cy + lx * s + ly * c
    px, py = at(-3, 2)
    b.box(px, py, 3.0, 18, 13, 6, rot)
    for i in range(4):
        qx, qy = at(-3, 2 - 6.5 + 13 * (i + 0.5) / 4)
        b.prism(qx, qy, 6.0, 18, 13 / 4, 2.2, rot)
    px, py = at(8.5, -3)
    chimney(b, px, py, 13, r=0.9)
    px, py = at(10.5, 1)
    chimney(b, px, py, 10, r=0.7)
    px, py = at(2, -9)
    gantry_crane(b, px, py, rot=rot, span=9, h=6)
    px, py = at(-10, -7)
    truck(b, px, py, rot=rot + math.pi / 2)
    px, py = at(-12, 6)
    water_tank(b, px, py, 0)
    fence_block(b, cx, cy, rot, 15 if VERSION == 1 else 13)


def asian_tower(b, x, y, w, d, h, rnd, dense=True):
    b.box(x, y, h / 2, w, d, h)
    b.box(x, y, h + 0.2, w + 0.5, d + 0.5, 0.4)
    b.box(x, y, h + 0.8, w * 0.85, d * 0.85, 0.8)
    floors = int(h / 3)
    for f in range(1, floors):
        b.box(x, y - d / 2 - 0.04, f * 3.0 + 0.4, w * 0.82, 0.08, 1.1)
        b.box(x - w / 2 - 0.04, y, f * 3.0 + 0.4, 0.08, d * 0.82, 1.1)
    if dense:
        roof_clutter(b, x, y, h + 1.2, w, d, rnd)
        # insegne a bandiera sovrapposte sulla facciata fronte strada (-y)
        n_signs = rnd.randint(2, 4)
        for k in range(n_signs):
            zt = h * rnd.uniform(0.35, 0.95)
            side = rnd.choice([-1, 1])
            flag_sign(b, x + side * w / 2 * rnd.uniform(0.2, 0.9), y - d / 2,
                      zt, rot=-math.pi / 2, h=rnd.uniform(2.2, 3.8), out=rnd.uniform(0.9, 1.4))
        if rnd.random() < 0.7:
            sign_board(b, x - w / 2 - 0.6, y - d / 2 + 1.0, h * rnd.uniform(0.6, 0.85))
        if rnd.random() < 0.5:
            ac_units(b, x, y - d / 2 - 0.3, h - 2.5, n=2)
    else:
        if rnd.random() < 0.8:
            water_tank(b, x + rnd.uniform(-w / 4, w / 4), y + rnd.uniform(-d / 4, d / 4), h + 0.4)
        if rnd.random() < 0.6:
            ac_units(b, x, y - d / 2 - 0.3, h - 2.5, n=2)
        if rnd.random() < 0.85:
            sign_board(b, x - w / 2 - 0.6, y - d / 2 + 1.0, h * rnd.uniform(0.65, 0.9))


def block_towers(b, cx, cy, seed, half=14.8):
    rnd = random.Random(seed)
    dense = VERSION == 2
    n = rnd.randint(5, 7) if dense else rnd.randint(2, 4)
    placed = []
    for i in range(n):
        w = rnd.uniform(5.5, 8.5)
        d = rnd.uniform(5.5, 8.5)
        h = rnd.uniform(12, 26)
        for _ in range(12):
            x = cx + rnd.uniform(-(half - w / 2 - 1), half - w / 2 - 1)
            y = cy + rnd.uniform(-(half - d / 2 - 1), half - d / 2 - 1)
            ok = all(abs(x - px) > (w + pw) / 2 + 0.6 or abs(y - py) > (d + pd) / 2 + 0.6
                     for px, py, pw, pd in placed)
            if ok:
                break
        placed.append((x, y, w, d))
        asian_tower(b, x, y, w, d, h, rnd, dense=dense)
    if dense:
        # infill basso tra le torri + verde
        for i in range(rnd.randint(2, 3)):
            x = cx + rnd.uniform(-half + 4, half - 4)
            y = cy + rnd.uniform(-half + 4, half - 4)
            w, d, h = rnd.uniform(4, 6), rnd.uniform(3, 5), rnd.uniform(3, 4.5)
            b.box(x, y, h / 2, w, d, h)
            b.prism(x, y, h, w * 1.06, d * 1.1, 0.5)
            roof_clutter(b, x, y, h + 0.5, w, d, rnd)
        for i in range(rnd.randint(1, 3)):
            tree(b, cx + rnd.uniform(-half + 2, half - 2), cy + rnd.uniform(-half + 2, half - 2),
                 scale=rnd.uniform(0.6, 0.9))


def block_lowrise(b, cx, cy, seed, half=14.5):
    rnd = random.Random(seed)
    n = rnd.randint(4, 5) if VERSION == 2 else rnd.randint(2, 3)
    for i in range(n):
        x = cx + rnd.uniform(-half + 6, half - 6)
        y = cy + rnd.uniform(-half + 6, half - 6)
        w, d, h = rnd.uniform(6, 9), rnd.uniform(4.5, 6.5), rnd.uniform(3, 4.5)
        rot = rnd.choice([0, math.pi / 2])
        b.box(x, y, h / 2, w, d, h, rot)
        b.gable(x, y, h, w * 1.06, d * 1.12, rnd.uniform(1.4, 2.0), rot)
        if VERSION == 2:
            rnd2 = random.Random(seed * 7 + i)
            if rnd2.random() < 0.6:
                antenna(b, x + 1, y, h + 1.2, h=1.8)
            if rnd2.random() < 0.4:
                clothesline(b, x, y + d / 2 + 1.2, 2.2, rot=0)
    for i in range(rnd.randint(3, 5) if VERSION == 2 else rnd.randint(2, 4)):
        tree(b, cx + rnd.uniform(-half + 3, half - 3), cy + rnd.uniform(-half + 3, half - 3),
             scale=rnd.uniform(0.7, 1.1), lollipop=rnd.random() < 0.5)
    if rnd.random() < 0.5:
        truck(b, cx + rnd.uniform(-6, 6), cy + rnd.uniform(-6, 6), rot=rnd.uniform(0, math.pi))
    if VERSION == 2:
        for i in range(rnd.randint(2, 4)):
            scooter(b, cx + rnd.uniform(-half + 2, half - 2), cy + rnd.uniform(-half + 2, half - 2),
                    rot=rnd.uniform(0, math.pi * 2))
    fence_block(b, cx, cy, 0, half)


def parcel_house(b, x, y, rnd, lot=11.0):
    # proprietà privata: casetta + giardino + auto nel vialetto
    rot = rnd.choice([0, math.pi / 2])
    hx = x + rnd.uniform(-1.2, 1.2)
    hy = y + rnd.uniform(-1.2, 1.2)
    w, d, h = rnd.uniform(5.5, 7.0), rnd.uniform(4.5, 5.5), rnd.uniform(3.0, 4.0)
    b.box(hx, hy, h / 2, w, d, h, rot)
    b.gable(hx, hy, h, w * 1.08, d * 1.14, rnd.uniform(1.3, 1.8), rot)
    windows_grid(b, hx, hy - (d / 2 + 0.03) * math.cos(rot), 1.6, 1.0, 1.1, 2, 1,
                 axis='y' if rot == 0 else 'x', gap_x=1.2)
    if rnd.random() < 0.5:
        antenna(b, hx + 1.0, hy, h + 1.4, h=1.6)
    if rnd.random() < 0.4:
        water_tank(b, hx - w / 4, hy + d / 4, h + 1.2)
    # giardino: alberi, cespugli, siepe interna
    tree(b, x + rnd.uniform(2.5, 4.2) * rnd.choice([-1, 1]), y + rnd.uniform(2.5, 4.2),
         scale=rnd.uniform(0.55, 0.85), lollipop=rnd.random() < 0.6)
    for i in range(rnd.randint(1, 3)):
        bush(b, x + rnd.uniform(-4.2, 4.2), y + rnd.uniform(-4.2, 4.2), r=rnd.uniform(0.5, 0.85))
    hedge(b, x, y - lot / 2 + 0.7, lot * 0.55, rot=0, h=0.7)
    # auto nel vialetto
    car(b, x + rnd.uniform(2.6, 3.6) * rnd.choice([-1, 1]), y - rnd.uniform(2.4, 3.6),
        rot=rot + rnd.uniform(-0.1, 0.1))
    if rnd.random() < 0.4:
        scooter(b, x - 2.0, y - 1.5, rot=rnd.uniform(0, math.pi))


def parcel_tower(b, x, y, rnd):
    w = rnd.uniform(5.0, 6.8)
    d = rnd.uniform(5.0, 6.8)
    h = rnd.uniform(11, 21)
    asian_tower(b, x, y, w, d, h, rnd, dense=True)
    bush(b, x + w / 2 + 1.0, y - d / 2 - 0.5, r=0.7)
    if rnd.random() < 0.6:
        car(b, x - w / 2 - 1.8, y + rnd.uniform(-2, 2), rot=math.pi / 2)


def parcel_workshop(b, x, y, rnd):
    w, d, h = rnd.uniform(6.5, 8.0), rnd.uniform(5.5, 6.5), rnd.uniform(3.5, 4.5)
    b.box(x, y, h / 2, w, d, h)
    b.prism(x, y, h, w * 1.06, d * 1.1, rnd.uniform(0.8, 1.2))
    roller_shutter(b, x, y - d / 2 - 0.06, 0.15, min(3.4, w - 2.4), h - 1.4)
    pallet_stack(b, x + w / 2 + 1.0, y - 1.0, rot=rnd.uniform(0, 0.5), n=rnd.randint(1, 3))
    if rnd.random() < 0.6:
        truck(b, x - w / 2 - 2.4, y - 0.5, rot=math.pi / 2)
    else:
        car(b, x - w / 2 - 1.8, y - 0.5, rot=math.pi / 2)
    chimney(b, x + w / 4, y + d / 4, h + 2.0, r=0.25)


def parcel_garden(b, x, y, rnd, lot=11.0):
    # lotto a giardino: prato, alberi misti, cespugli, vialetto
    b.box(x, y, 0.34, lot * 0.85, lot * 0.85, 0.06)        # prato rialzato
    b.box(x, y - lot * 0.32, 0.37, 1.1, lot * 0.36, 0.05)  # vialetto
    for i in range(rnd.randint(4, 6)):
        tree(b, x + rnd.uniform(-lot * 0.36, lot * 0.36), y + rnd.uniform(-lot * 0.36, lot * 0.36),
             scale=rnd.uniform(0.55, 1.0), lollipop=rnd.random() < 0.5)
    for i in range(rnd.randint(3, 5)):
        bush(b, x + rnd.uniform(-lot * 0.4, lot * 0.4), y + rnd.uniform(-lot * 0.4, lot * 0.4),
             r=rnd.uniform(0.5, 0.9))
    hedge(b, x - lot * 0.42, y, lot * 0.7, rot=math.pi / 2, h=0.7)


def parcel_greens(b, lx, ly, rnd, lot=11.0):
    # verde di riempimento dove l'edificio non occupa tutto il lotto:
    # alberi e cespugli lungo i bordi, fuori dall'impronta centrale
    for i in range(rnd.randint(2, 3)):
        ang = rnd.uniform(0, 2 * math.pi)
        rad = rnd.uniform(lot * 0.40, lot * 0.48)
        gx, gy = lx + rad * math.cos(ang), ly + rad * math.sin(ang)
        if rnd.random() < 0.55:
            bush(b, gx, gy, r=rnd.uniform(0.45, 0.8))
        else:
            tree(b, gx, gy, scale=rnd.uniform(0.45, 0.7), lollipop=rnd.random() < 0.5)


def block_parcels(b, cx, cy, seed, half=13.0):
    # isolato diviso in 4 lotti privati con separatori (muretti)
    rnd = random.Random(seed)
    lot = half - 1.0
    # recinzione perimetrale + muretti divisori a croce
    fence_block(b, cx, cy, 0, half)
    b.box(cx, cy, 0.55, half * 2 * 0.9, 0.18, 1.1)
    b.box(cx, cy, 0.55, 0.18, half * 2 * 0.9, 1.1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = cx + sx * half / 2
            ly = cy + sy * half / 2
            r = rnd.random()
            if r < 0.4:
                parcel_house(b, lx, ly, rnd, lot=lot)
            elif r < 0.7:
                parcel_tower(b, lx, ly, rnd)
            elif r < 0.85:
                parcel_workshop(b, lx, ly, rnd)
            else:
                parcel_garden(b, lx, ly, rnd, lot=lot)
            parcel_greens(b, lx, ly, rnd, lot=lot)
    # angoli dell'isolato: alberi dove i lotti non arrivano
    for sx in (-1, 1):
        for sy in (-1, 1):
            if rnd.random() < 0.5:
                tree(b, cx + sx * (half - 1.6), cy + sy * (half - 1.6),
                     scale=rnd.uniform(0.5, 0.8), lollipop=rnd.random() < 0.5)


# ---------------------------------------------------------------- city v1
def build_city_v1():
    b = Builder()
    P = 38
    rnd = random.Random(3)
    for i in range(-2, 3):
        for j in range(-2, 3):
            if i == 0 and j == 0:
                continue
            cx, cy = i * P, j * P
            ring = max(abs(i), abs(j))
            r = rnd.random()
            if ring == 1:
                kind = 'factory' if (i + j) % 2 == 0 else ('towers' if r < 0.6 else 'lowrise')
            else:
                kind = 'towers' if r < 0.55 else ('lowrise' if r < 0.8 else 'factory')
            if kind == 'factory':
                block_factory(b, cx, cy, rot=rnd.choice([0, math.pi / 2]))
            elif kind == 'towers':
                block_towers(b, cx, cy, seed=i * 17 + j * 31)
            else:
                block_lowrise(b, cx, cy, seed=i * 13 + j * 7)
    b.to_object("City")

    rb = Builder()
    span = 2.5 * P + 10
    for line in (-1.5 * P, -0.5 * P, 0.5 * P, 1.5 * P):
        road_c = line + P / 2
        rb.box(0, road_c, 0.02, span, 7.0, 0.04)
        rb.box(road_c, 0, 0.03, 7.0, span, 0.04)
    for i in range(6):
        rb.box(-5.5 + i * 2.2, -P / 2, 0.06, 1.0, 5.6, 0.03)
    rb.to_object("Roads")

    pb = Builder()
    y_road = -P / 2
    xs = list(range(-66, 67, 22))
    for x in xs:
        power_pole(pb, x, y_road - 4.6)
    for a, bx in zip(xs, xs[1:]):
        for dz, dy in ((-0.5, -0.8), (-0.5, 0.8), (-1.4, -0.6), (-1.4, 0.6)):
            sag = 0.55
            mid = ((a + bx) / 2, y_road - 4.6 + dy, 7 + dz - sag)
            pb.tube((a, y_road - 4.6 + dy, 7 + dz), mid, r=0.022, seg=3)
            pb.tube(mid, (bx, y_road - 4.6 + dy, 7 + dz), r=0.022, seg=3)
    pb.to_object("Poles")

    cb = Builder()
    for (x, y, z, s) in ((-30, 20, 26, 1.0), (25, -28, 30, 1.3), (45, 30, 24, 0.8)):
        cb.sphere(x, y, z, 3.2 * s, sub=2, squash=0.45)
        cb.sphere(x + 2.6 * s, y + 0.6 * s, z - 0.3, 2.2 * s, sub=2, squash=0.5)
        cb.sphere(x - 2.8 * s, y - 0.4 * s, z - 0.4, 2.0 * s, sub=2, squash=0.5)
    cb.to_object("Clouds")


# ---------------------------------------------------------------- city v2
def build_city_v2():
    # blocchi a ±46 e ±78: clearance maggiore attorno alla plaza (±28)
    b = Builder()
    centers = [-78, -46, 0, 46, 78]
    half = 13
    rnd = random.Random(3)
    for cx in centers:
        for cy in centers:
            if cx == 0 and cy == 0:
                continue
            ring = max(abs(cx), abs(cy))
            seed = cx * 17 + cy * 31
            r = rnd.random()
            if ring == 78 and r < 0.12:
                block_factory(b, cx, cy, rot=rnd.choice([0, math.pi / 2]))
            else:
                # ogni isolato = 4 lotti privati separati da muretti
                block_parcels(b, cx, cy, seed=seed, half=half)
    # vie vive: bancarelle, scooter e verde su tutte le strade principali
    srnd = random.Random(11)
    for x in (-40, -34, 36, 42, -72, 68):
        stall(b, x, -27.5, rot=0)
    for x in (-50, -44, 50, 58):
        stall(b, x, 33.3, rot=math.pi)
    for y in (-50, -44, 44, 56):
        stall(b, -27.4, y, rot=math.pi / 2)
    for i in range(8):
        scooter(b, -18 + i * 2.0, -26.8, rot=math.pi / 2 + srnd.uniform(-0.15, 0.15))
    for i in range(6):
        scooter(b, 24 + i * 2.0, -33.2, rot=-math.pi / 2 + srnd.uniform(-0.15, 0.15))
    for i in range(7):
        scooter(b, -60 + i * 2.0, 26.9, rot=math.pi / 2 + srnd.uniform(-0.15, 0.15))
    for i in range(5):
        scooter(b, 33.2, -14 + i * 2.0, rot=srnd.uniform(-0.15, 0.15))
    for i in range(5):
        scooter(b, -33.2, 40 + i * 2.0, rot=math.pi + srnd.uniform(-0.15, 0.15))
    # vasi verdi lungo le vie
    for x in (-52, -48, 48, 52):
        planter(b, x, -33.5)
    for x in (-14, -8, 8, 14):
        planter(b, x, 26.8)
    for y in (-56, -48, 44, 52):
        planter(b, 26.8, y)
    b.to_object("City")

    # strade: griglia a ±30 e ±62
    rb = Builder()
    span = 196
    for line in (-62, -30, 30, 62):
        rb.box(0, line, 0.02, span, 6.0, 0.04)
        rb.box(line, 0, 0.03, 6.0, span, 0.04)
    for i in range(6):
        rb.box(-5.5 + i * 2.2, -30, 0.06, 1.0, 4.8, 0.03)   # strisce davanti all'ingresso
    for i in range(5):
        rb.box(-30, -8 + i * 2.2, 0.06, 4.8, 1.0, 0.03)     # strisce laterali
    rb.to_object("Roads")

    # pali con catenarie parallele pulite (stile v1)
    pb = Builder()
    def wire_run(coords, fixed, z_top, axis='x'):
        # axis='x': corre lungo x a y=fixed; axis='y': lungo y a x=fixed
        for v in coords:
            if axis == 'x':
                power_pole(pb, v, fixed, h=7.0)
            else:
                power_pole(pb, fixed, v, h=7.0)
        for a, c2 in zip(coords, coords[1:]):
            for dz, dt in ((-0.5, -0.8), (-0.5, 0.8), (-1.4, -0.6), (-1.4, 0.6)):
                sag = 0.55
                if axis == 'x':
                    p0 = (a, fixed + dt, z_top + dz)
                    p1 = (c2, fixed + dt, z_top + dz)
                    mid = ((a + c2) / 2, fixed + dt, z_top + dz - sag)
                else:
                    p0 = (fixed + dt, a, z_top + dz)
                    p1 = (fixed + dt, c2, z_top + dz)
                    mid = (fixed + dt, (a + c2) / 2, z_top + dz - sag)
                pb.tube(p0, mid, r=0.022, seg=3)
                pb.tube(mid, p1, r=0.022, seg=3)
    wire_run(list(range(-88, 89, 18)), -34.6, 7.0, axis='x')
    wire_run(list(range(-88, 89, 18)), 33.8, 7.0, axis='x')
    wire_run(list(range(-80, 81, 18)), -34.2, 7.0, axis='y')
    # due attraversamenti puliti sulla via principale
    for x in (-16, 40):
        for dz in (-0.5, -1.0):
            pb.tube((x, -34.6, 7 + dz), (x, -25.6, 6.6 + dz), r=0.022, seg=3)
    pb.to_object("Poles")

    cb = Builder()
    for (x, y, z, s) in ((-38, 26, 27, 1.0), (30, -34, 31, 1.3), (55, 36, 25, 0.8), (-60, -20, 29, 0.9)):
        cb.sphere(x, y, z, 3.2 * s, sub=2, squash=0.45)
        cb.sphere(x + 2.6 * s, y + 0.6 * s, z - 0.3, 2.2 * s, sub=2, squash=0.5)
        cb.sphere(x - 2.8 * s, y - 0.4 * s, z - 0.4, 2.0 * s, sub=2, squash=0.5)
    cb.to_object("Clouds")


# ---------------------------------------------------------------- build + export
build_fratelli()
if VERSION == 1:
    build_city_v1()
else:
    build_city_v2()

for ob in col.objects:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSETS, f"scene{SUFFIX}.blend"))
bpy.ops.export_scene.gltf(
    filepath=os.path.join(ASSETS, f"fratelli_city{SUFFIX}.glb"),
    export_format='GLB',
    export_apply=True,
    export_yup=True,
    export_materials='NONE',
    export_normals=True,
    export_texcoords=True,
)
print(f"EXPORT OK v{VERSION}:", os.path.join(ASSETS, f"fratelli_city{SUFFIX}.glb"))
