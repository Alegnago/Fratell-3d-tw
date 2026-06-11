# Genera fratelli_city.glb + scene.blend
# Run: /Applications/Blender.app/Contents/MacOS/Blender --background --python tools/build_scene.py
import bpy
import bmesh
import math
import random
import os

random.seed(7)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = bpy.context.collection

# ---------------------------------------------------------------- mesh helpers
# Tutte le geometrie sono pydata raw accumulate in "builder" liste, poi un
# mesh per gruppo: pochi oggetti, export veloce, niente operatori bpy.ops.

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
        # prisma triangolare (tetto a falda singola / dente di sega), cresta lato +y
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
        # tubo dritto tra due punti (cavi, pali inclinati)
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        if L < 1e-6:
            return
        # base ortonormale
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
    # griglia finestre: box sottili sporgenti -> edges disegnano la cornice
    gx = gap_x if gap_x else w * 0.55
    gz = gap_z if gap_z else h * 0.7
    total_w = cols * w + (cols - 1) * gx
    total_h = rows * h + (rows - 1) * gz
    for i in range(cols):
        for j in range(rows):
            ox = -total_w / 2 + w / 2 + i * (w + gx)
            oz = -total_h / 2 + h / 2 + j * (h + gz)
            c, s = math.cos(rot), math.sin(rot)
            if axis == 'y':  # facciata che guarda ±y
                lx, ly = ox, 0
            else:            # facciata che guarda ±x
                lx, ly = 0, ox
            wx = face_x + lx * c - ly * s
            wy = face_y + lx * s + ly * c
            if axis == 'y':
                b.box(wx, wy, face_z + oz, w, depth, h, rot)
            else:
                b.box(wx, wy, face_z + oz, depth, w, h, rot)


def slat_facade(b, cx, cy, z0, z1, width, axis, n=None, fin=0.07, depth=0.18):
    # doghe verticali (hatching della facciata Fratelli)
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
    # cargo
    px, py = at(-0.9, 0)
    b.box(px, py, 1.5, 3.6, 2.0, 2.2, rot)
    # cabina
    px, py = at(1.8, 0)
    b.box(px, py, 1.05, 1.5, 1.9, 1.5, rot)
    # ruote
    for lx in (-2.0, -0.3, 1.9):
        for ly in (-0.95, 0.95):
            px, py = at(lx, ly)
            b.box(px, py, 0.38, 0.7, 0.25, 0.76, rot)


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
    # insegna verticale a cassonetto (stile Taiwan) con listelli orizzontali
    b.box(x, y, z_top - h / 2, w, depth, h, rot)
    c, s = math.cos(rot), math.sin(rot)
    n = int(h / 0.9)
    for i in range(n):
        z = z_top - h + h * (i + 0.5) / n
        b.box(x - s * (depth / 2), y + c * (depth / 2), z, w * 0.72, 0.06, 0.5, rot)


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
    # carrello + gancio
    tx, ty = at(span * 0.18, 0)
    b.box(tx, ty, h - 0.1, 0.9, 0.7, 0.5, rot)
    b.tube((tx, ty, h - 0.3), (tx, ty, h - 2.0), r=0.03, seg=4)
    b.box(tx, ty, h - 2.2, 0.5, 0.4, 0.3, rot)


def chimney(b, x, y, h, r=0.8):
    b.cylinder(x, y, 0, r, h, seg=10, r_top=r * 0.72)
    b.cylinder(x, y, h, r * 0.78, 0.5, seg=10)


def fence(b, x, y, length, rot=0.0, h=2.2):
    # muro di cinta in lamiera: pannello + paletti
    b.box(x, y, h / 2, length, 0.12, h, rot)
    b.box(x, y, h + 0.06, length, 0.2, 0.12, rot)
    c, s = math.cos(rot), math.sin(rot)
    n = int(length / 2.4)
    for i in range(n + 1):
        o = -length / 2 + length * i / max(n, 1)
        b.box(x + o * c, y + o * s, h / 2, 0.16, 0.22, h, rot)


# ---------------------------------------------------------------- Fratelli HQ
def build_fratelli():
    b = Builder()
    # podio / plaza
    b.box(0, 0, 0.15, 34, 26, 0.3)
    b.box(0, -14.2, 0.08, 12, 3.0, 0.16)          # rampa marciapiede
    for i in range(4):                              # gradinata ingresso
        b.box(0, -12.6 + i * 0.55, 0.34 + i * 0.14, 10 - i * 0.8, 0.7, 0.14)

    # ala destra: 3 piani con griglia finestre
    b.box(9.5, 2.0, 0.3 + 4.5, 13, 11, 9)
    windows_grid(b, 9.5, 2.0 - 5.5, 5.6, 1.05, 1.5, 5, 2, axis='y', gap_x=0.85, gap_z=1.6)
    windows_grid(b, 9.5 + 6.5, 2.0, 5.6, 1.05, 1.5, 4, 2, axis='x', gap_x=0.9, gap_z=1.6)
    b.box(9.5, 2.0, 9.55, 13.5, 11.5, 0.5)         # cornicione

    # torre centrale con doghe
    b.box(-1.5, 0.5, 0.3 + 6.0, 11, 9, 12)
    slat_facade(b, -1.5, 0.5 - 4.62, 2.6, 12.0, 10.2, axis='y')      # fronte
    slat_facade(b, -1.5 - 5.62, 0.5, 2.6, 12.0, 8.2, axis='x')       # lato sx
    b.box(-1.5, 0.5, 12.55, 11.6, 9.6, 0.5)        # cornicione torre
    # vetrina piano terra (incassata)
    b.box(-1.5, 0.5 - 4.0, 1.55, 9.5, 1.6, 2.5)
    windows_grid(b, -1.5, 0.5 - 4.85, 1.55, 1.3, 1.9, 4, 1, axis='y', gap_x=0.6)

    # ala sinistra bassa con hatch diagonale reso a doghe fitte
    b.box(-11.5, 1.5, 0.3 + 3.0, 9, 10, 6)
    slat_facade(b, -11.5, 1.5 - 5.12, 0.4, 6.0, 8.2, axis='y', fin=0.05, depth=0.12)
    slat_facade(b, -11.5 - 4.62, 1.5, 0.4, 6.0, 9.2, axis='x', fin=0.05, depth=0.12)
    b.box(-11.5, 1.5, 6.5, 9.5, 10.5, 0.4)

    # volumi tecnici tetto
    b.box(-3.0, 1.5, 13.6, 6.5, 5.5, 2.2)
    b.box(-3.0, 1.5, 14.9, 7.0, 6.0, 0.4)
    b.box(7.0, 4.0, 10.7, 4.5, 4.0, 1.8)
    ac_units(b, 11.5, 5.5, 9.8, n=2)
    water_tank(b, -13.0, 4.0, 6.7)

    # alberi lollipop sulla plaza
    for x, y in ((-15.5, -10.5), (15.5, -10.5), (-16.0, 8.0), (16.0, 9.5), (4.5, -11.5)):
        tree(b, x, y, scale=1.0, lollipop=True)

    ob = b.to_object("Fratelli_HQ")

    # logo: plane separato con UV, materiale texture assegnato runtime
    lb = bpy.data.meshes.new("Logo")
    s_w, s_h = 4.4, 4.4
    # sul fronte della torre, appena sopra le doghe
    yf = 0.5 - 4.62 - 0.16
    lb.from_pydata(
        [(-1.5 - s_w / 2, yf, 7.6), (-1.5 + s_w / 2, yf, 7.6),
         (-1.5 + s_w / 2, yf, 7.6 + s_h), (-1.5 - s_w / 2, yf, 7.6 + s_h)],
        [], [(0, 1, 2, 3)])
    uv = lb.uv_layers.new(name="UVMap")
    for li, co in zip(lb.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[li.index].uv = co
    lb.validate(); lb.update()
    lob = bpy.data.objects.new("Logo", lb)
    col.objects.link(lob)
    return ob


# ---------------------------------------------------------------- city blocks
def block_factory(b, cx, cy, rot):
    # capannone dente di sega + ciminiere + gru + cisterna
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
    fence_block(b, cx, cy, rot, 15)


def fence_block(b, cx, cy, rot, half):
    fence(b, cx, cy - half, 2 * half * 0.92, rot=rot)
    fence(b, cx, cy + half, 2 * half * 0.92, rot=rot)
    fence(b, cx - half, cy, 2 * half * 0.92, rot=rot + math.pi / 2)
    fence(b, cx + half, cy, 2 * half * 0.92, rot=rot + math.pi / 2)


def block_towers(b, cx, cy, seed):
    rnd = random.Random(seed)
    # 2-4 palazzine strette stile Taiwan con insegne
    n = rnd.randint(2, 4)
    for i in range(n):
        w = rnd.uniform(6, 9)
        d = rnd.uniform(6, 9)
        h = rnd.uniform(12, 26)
        x = cx + rnd.uniform(-9, 9)
        y = cy + rnd.uniform(-9, 9)
        b.box(x, y, h / 2, w, d, h)
        b.box(x, y, h + 0.2, w + 0.5, d + 0.5, 0.4)             # cornicione
        b.box(x, y, h + 0.8, w * 0.85, d * 0.85, 0.8)           # parapetto tetto
        if rnd.random() < 0.8:
            water_tank(b, x + rnd.uniform(-w / 4, w / 4), y + rnd.uniform(-d / 4, d / 4), h + 0.4)
        if rnd.random() < 0.6:
            ac_units(b, x, y - d / 2 - 0.3, h - 2.5, n=2)
        if rnd.random() < 0.85:
            sign_board(b, x - w / 2 - 0.6, y - d / 2 + 1.0, h * rnd.uniform(0.65, 0.9))
        # bande finestre semplici (loop orizzontali come sporgenze sottili)
        floors = int(h / 3)
        for f in range(1, floors):
            b.box(x, y - d / 2 - 0.04, f * 3.0 + 0.4, w * 0.82, 0.08, 1.1)
            b.box(x - w / 2 - 0.04, y, f * 3.0 + 0.4, 0.08, d * 0.82, 1.1)


def block_lowrise(b, cx, cy, seed):
    rnd = random.Random(seed)
    # casette con tetto a capanna in lamiera + cortile
    for i in range(rnd.randint(2, 3)):
        x = cx + rnd.uniform(-8, 8)
        y = cy + rnd.uniform(-8, 8)
        w, d, h = rnd.uniform(7, 10), rnd.uniform(5, 7), rnd.uniform(3, 4.5)
        rot = rnd.choice([0, math.pi / 2])
        b.box(x, y, h / 2, w, d, h, rot)
        b.gable(x, y, h, w * 1.06, d * 1.12, rnd.uniform(1.4, 2.0), rot)
    for i in range(rnd.randint(2, 4)):
        tree(b, cx + rnd.uniform(-11, 11), cy + rnd.uniform(-11, 11),
             scale=rnd.uniform(0.7, 1.1), lollipop=rnd.random() < 0.5)
    if rnd.random() < 0.5:
        truck(b, cx + rnd.uniform(-6, 6), cy + rnd.uniform(-6, 6), rot=rnd.uniform(0, math.pi))
    fence_block(b, cx, cy, 0, 14.5)


def build_city():
    b = Builder()
    P = 38           # passo griglia
    half_block = 14.8
    kinds = {}
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
            kinds[(i, j)] = kind
            if kind == 'factory':
                block_factory(b, cx, cy, rot=rnd.choice([0, math.pi / 2]))
            elif kind == 'towers':
                block_towers(b, cx, cy, seed=i * 17 + j * 31)
            else:
                block_lowrise(b, cx, cy, seed=i * 13 + j * 7)
    b.to_object("City")

    # strade: nastri piatti tra i blocchi + strisce pedonali davanti al palazzo
    rb = Builder()
    span = 2.5 * P + 10
    for line in (-1.5 * P, -0.5 * P, 0.5 * P, 1.5 * P):
        road_c = line + P / 2
        rb.box(0, road_c, 0.02, span, 7.0, 0.04)
        rb.box(road_c, 0, 0.03, 7.0, span, 0.04)
    # strisce pedonali davanti al palazzo
    for i in range(6):
        rb.box(-5.5 + i * 2.2, -P / 2, 0.06, 1.0, 5.6, 0.03)
    rb.to_object("Roads")

    # pali della luce + cavi lungo la via principale davanti al palazzo
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

    # nuvole piatte
    cb = Builder()
    for (x, y, z, s) in ((-30, 20, 26, 1.0), (25, -28, 30, 1.3), (45, 30, 24, 0.8)):
        cb.sphere(x, y, z, 3.2 * s, sub=2, squash=0.45)
        cb.sphere(x + 2.6 * s, y + 0.6 * s, z - 0.3, 2.2 * s, sub=2, squash=0.5)
        cb.sphere(x - 2.8 * s, y - 0.4 * s, z - 0.4, 2.0 * s, sub=2, squash=0.5)
    cb.to_object("Clouds")


# ---------------------------------------------------------------- build + export
build_fratelli()
build_city()

# normali coerenti su tutti gli oggetti
for ob in col.objects:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSETS, "scene.blend"))
bpy.ops.export_scene.gltf(
    filepath=os.path.join(ASSETS, "fratelli_city.glb"),
    export_format='GLB',
    export_apply=True,
    export_yup=True,
    export_materials='NONE',
    export_normals=True,
    export_texcoords=True,
)
print("EXPORT OK:", os.path.join(ASSETS, "fratelli_city.glb"))
