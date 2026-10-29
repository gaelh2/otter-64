#!/usr/bin/env python3
"""
Otto model generator — emits actors/otto/model.inc.c (Vtx + Gfx display lists)
and actors/otto/geo.inc.c (geo layout mirroring the vanilla player skeleton).

Model-space convention (matches vanilla Mario parts):
  +X = "up" along the body / limb direction (parts extend along +X)
  +Y = forward (face/muzzle direction)
  +Z = character's left

Each part is assembled from parametric sub-meshes (ellipsoids, tapered tubes).
Every triangle belongs to a color segment; each color change inside a display
list emits a gsSPLightColor pair (lit + ambient), like the vanilla shared-DL
pattern but self-contained per part.
"""
import math, os, sys

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "actors", "otto")

# --- palette: (lit RGBA, ambient RGBA) ---------------------------------------
def _c(r, g, b, a=0xFF):
    return (r << 24) | (g << 16) | (b << 8) | a

def _amb(r, g, b, k=0.5):
    return _c(int(r * k), int(g * k), int(b * k))

PALETTE = {
    "amber":      (_c(0xC8, 0x7A, 0x3C), _amb(0xC8, 0x7A, 0x3C)),
    "amber_dark": (_c(0x9A, 0x5B, 0x28), _amb(0x9A, 0x5B, 0x28)),
    "cream":      (_c(0xF2, 0xE3, 0xC9), _amb(0xF2, 0xE3, 0xC9)),
    "navy":       (_c(0x1F, 0x2A, 0x44), _amb(0x1F, 0x2A, 0x44)),
    "navy_dark":  (_c(0x16, 0x1E, 0x33), _amb(0x16, 0x1E, 0x33)),
    "paw":        (_c(0x6B, 0x3E, 0x1F), _amb(0x6B, 0x3E, 0x1F)),
    "dark":       (_c(0x24, 0x18, 0x12), _amb(0x24, 0x18, 0x12)),
}

# --- mesh primitives ----------------------------------------------------------
# Each sub-mesh: {"verts": [(x,y,z),...], "tris": [(a,b,c,color),...]}

def ellipsoid(cx, cy, cz, rx, ry, rz, lons=8, lats=5, color="amber"):
    """UV-style ellipsoid, poles on the +X/-X axis."""
    verts, tris = [], []
    verts.append((cx - rx, cy, cz))              # south pole (-X)
    for i in range(1, lats):
        phi = -math.pi / 2 + math.pi * i / lats  # -90..+90
        ring = []
        for j in range(lons):
            th = 2 * math.pi * j / lons
            ring.append(len(verts))
            verts.append((cx + rx * math.cos(phi),
                          cy + ry * math.sin(phi) * math.cos(th),
                          cz + rz * math.sin(phi) * math.sin(th)))
        if i > 1:
            for j in range(lons):
                a = ring[j]; b = ring[(j + 1) % lons]
                prev = len(verts) - lons - lons
                c = prev + j; d = prev + (j + 1) % lons
                tris.append((c, d, b, color)); tris.append((c, b, a, color))
    verts.append((cx + rx, cy, cz))              # north pole (+X)
    np_ = len(verts) - 1
    last = len(verts) - 1 - lons
    for j in range(lons):
        tris.append((last + j, last + (j + 1) % lons, np_, color))
    first = 1
    for j in range(lons):
        tris.append((0, first + (j + 1) % lons, first + j, color))
    return {"verts": verts, "tris": tris}


def tube(path, radii, sides=8, color="amber", flatten_z=1.0):
    """Tapered tube along a 3D path; open ends capped with a center point."""
    verts, tris = [], []
    n = len(path)
    for i, (p, r) in enumerate(zip(path, radii)):
        if i == 0:      tangent = _sub(path[1], path[0])
        elif i == n-1:  tangent = _sub(path[-1], path[-2])
        else:           tangent = _sub(path[i+1], path[i-1])
        tangent = _norm(tangent)
        up = (0, 0, 1) if abs(tangent[2]) < 0.9 else (0, 1, 0)
        u = _norm(_cross(tangent, up))
        v = _cross(tangent, u)
        for j in range(sides):
            th = 2 * math.pi * j / sides
            verts.append((p[0] + r * (math.cos(th) * u[0] + math.sin(th) * v[0]),
                          p[1] + r * (math.cos(th) * u[1] + math.sin(th) * v[1]),
                          p[2] + r * flatten_z * (math.cos(th) * u[2] + math.sin(th) * v[2])))
    for i in range(n - 1):
        for j in range(sides):
            a = i * sides + j; b = i * sides + (j + 1) % sides
            c = (i + 1) * sides + j; d = (i + 1) * sides + (j + 1) % sides
            tris.append((a, d, b, color)); tris.append((a, c, d, color))
    for idx, end in ((0, verts[0]), (1, verts[-1])):
        c = len(verts); verts.append((end[0], end[1], end[2]))
        base = 0 if idx == 0 else (n - 1) * sides
        for j in range(sides):
            a, b = base + j, base + (j + 1) % sides
            tris.append((c, b, a, color) if idx == 0 else (c, a, b, color))
    return {"verts": verts, "tris": tris}


def _sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _norm(a):
    l = math.sqrt(sum(t*t for t in a)) or 1.0
    return (a[0]/l, a[1]/l, a[2]/l)
def _scale(mesh, s):
    return {"verts": [(x*s[0], y*s[1], z*s[2]) for x,y,z in mesh["verts"]],
            "tris": mesh["tris"]}
def _move(mesh, dx, dy, dz):
    return {"verts": [(x+dx, y+dy, z+dz) for x,y,z in mesh["verts"]],
            "tris": mesh["tris"]}
def _mirror_z(mesh):
    return {"verts": [(x, y, -z) for x,y,z in mesh["verts"]],
            "tris": [(a, c, b, col) for a,b,c,col in mesh["tris"]]}

# --- part assembly ------------------------------------------------------------
# A part = list of sub-meshes (each carries its color via tris).
def P(*meshes): return list(meshes)

def build_parts():
    parts = {}

    # BUTT + tail ---------------------------------------------------------
    hips = ellipsoid(6, 0, 0, 46, 50, 54, lons=9, lats=8, color="amber")
    tail = tube([(0,-36,0),(-38,-52,0),(-84,-66,0),(-126,-78,0),(-158,-86,0)],
                [28,25,20,14,7], sides=7, color="amber_dark", flatten_z=0.72)
    parts["butt"] = P(hips, tail)

    # TORSO (navy hoodie + cream belly + hood lump) -----------------------
    body = ellipsoid(28, -2, 0, 54, 52, 52, lons=10, lats=8, color="navy")
    belly = ellipsoid(20, 30, 0, 38, 30, 36, lons=8, lats=5, color="cream")
    hood  = ellipsoid(58, -38, 0, 24, 16, 30, lons=7, lats=4, color="navy_dark")
    parts["torso"] = P(body, belly, hood)

    # HEAD base (shared by all eye states) ---------------------------------
    skull  = ellipsoid(42, 6, 0, 60, 56, 68, lons=10, lats=9, color="amber")
    muzzle = ellipsoid(26, 44, 0, 30, 22, 38, lons=8, lats=6, color="cream")
    nose   = ellipsoid(34, 62, 0, 13, 9, 15, lons=7, lats=4, color="dark")
    ear_l  = ellipsoid(88, -10, 54, 17, 14, 11, lons=6, lats=4, color="amber_dark")
    ear_r  = _mirror_z(ear_l)
    parts["head"] = P(skull, muzzle, nose, ear_l, ear_r)

    # EYE variants (geometry decals on the face front) --------------------
    def eyes(rx, color="dark"):
        l = ellipsoid(66, 58, 28, rx, 10, 9, lons=6, lats=4, color=color)
        return P(l, _mirror_z(l))
    parts["eyes_front"]       = eyes(10)
    parts["eyes_half_closed"] = eyes(5)
    parts["eyes_closed"]      = eyes(2, "amber_dark")
    parts["eyes_dead"]        = eyes(2, "amber_dark")

    # ARMS (navy sleeves) ---------------------------------------------------
    arm_geo = tube([(0,0,0),(34,0,0),(68,0,0)], [22,20,17], sides=7, color="navy")
    parts["left_arm"]  = P(arm_geo)
    parts["right_arm"] = P(_mirror_z(arm_geo))

    fore_geo = tube([(0,0,0),(30,0,0),(58,0,0)], [17,15,13], sides=7, color="navy")
    parts["left_forearm"]  = P(fore_geo)
    parts["right_forearm"] = P(_mirror_z(fore_geo))

    # HANDS (paws) -----------------------------------------------------------
    paw = ellipsoid(20, 0, 0, 27, 23, 25, lons=7, color="amber")
    parts["left_hand_closed"]  = P(paw)
    parts["right_hand_closed"] = P(_mirror_z(paw))
    open_paw = ellipsoid(24, 0, 0, 30, 25, 28, lons=7, color="amber")
    toe_nub  = ellipsoid(50, -2, 10, 8, 6, 6, lons=5, lats=3, color="amber")
    toe_nub2 = ellipsoid(52, -2, -8, 8, 6, 6, lons=5, lats=3, color="amber")
    toe_nub3 = ellipsoid(50, 8, 0, 8, 6, 6, lons=5, lats=3, color="amber")
    parts["left_hand_open"]  = P(open_paw, toe_nub, toe_nub2, toe_nub3)
    parts["right_hand_open"] = P(_mirror_z(open_paw), _mirror_z(toe_nub),
                                 _mirror_z(toe_nub2), _mirror_z(toe_nub3))

    # LEGS --------------------------------------------------------------------
    thigh_geo = tube([(0,0,0),(46,0,0),(88,0,0)], [24,21,17], sides=7, color="amber")
    parts["left_thigh"]  = P(thigh_geo)
    parts["right_thigh"] = P(_mirror_z(thigh_geo))

    leg_geo = tube([(0,0,0),(32,0,0),(62,0,0)], [17,14,11], sides=7, color="amber")
    parts["left_leg"]  = P(leg_geo)
    parts["right_leg"] = P(_mirror_z(leg_geo))

    foot_geo  = ellipsoid(32, -4, 0, 52, 20, 30, lons=7, color="paw")
    heel      = ellipsoid(-6, 0, 0, 18, 16, 20, lons=6, lats=4, color="paw")
    toe_l     = ellipsoid(76, 0, 12, 9, 7, 7, lons=5, lats=3, color="paw")
    toe_c     = ellipsoid(80, 0, 0, 9, 7, 7, lons=5, lats=3, color="paw")
    toe_r     = ellipsoid(76, 0, -12, 9, 7, 7, lons=5, lats=3, color="paw")
    parts["left_foot"]  = P(foot_geo, heel, toe_l, toe_c, toe_r)
    parts["right_foot"] = P(_mirror_z(foot_geo), _mirror_z(heel),
                            _mirror_z(toe_l), _mirror_z(toe_c), _mirror_z(toe_r))
    return parts


# --- C emission ---------------------------------------------------------------
def _normals(verts, tris):
    """Per-vertex normals (face-normal average), packed as signed bytes."""
    acc = [[0.0, 0.0, 0.0] for _ in verts]
    for a, b, c in tris:
        n = _cross(_sub(verts[b], verts[a]), _sub(verts[c], verts[a]))
        for i in (a, b, c):
            acc[i][0] += n[0]; acc[i][1] += n[1]; acc[i][2] += n[2]
    out = []
    for x, y, z in acc:
        nx, ny, nz = _norm((x, y, z))
        out.append((int(round(nx * 127)), int(round(ny * 127)), int(round(nz * 127))))
    return out


def emit_part_dl(name, meshes, f):
    """Emit <name>_dl_vertex arrays + <name>_dl (verts/tris) + <name> wrapper."""
    verts, tris, colors = [], [], []
    for m in meshes:
        base = len(verts)
        verts += m["verts"]
        tris += [(a + base, b + base, c + base) for a, b, c, _ in m["tris"]]
        colors += [col for *_, col in m["tris"]]
    norms = _normals(verts, tris)

    groups = [range(i, min(i + 15, len(verts))) for i in range(0, len(verts), 15)]
    for gi, g in enumerate(groups):
        f.write(f"static const Vtx otto_{name}_dl_vertex_group{gi+1}[] = {{\n")
        for i in g:
            x, y, z = (int(round(v)) for v in verts[i])
            nx, ny, nz = (v & 0xFF for v in norms[i])
            f.write("    {{{%6d,%6d,%6d}, 0, {     0,      0}, {0x%02x, 0x%02x, 0x%02x, 0x00}}},\n"
                    % (x, y, z, nx, ny, nz))
        f.write("};\n\n")

    f.write(f"const Gfx otto_{name}_dl[] = {{\n")
    cur_color = None
    for gi, g in enumerate(groups):
        lo, hi = g.start, g.stop
        f.write(f"    gsSPVertex(otto_{name}_dl_vertex_group{gi+1}, {hi - lo}, 0),\n")
        gtris = [(a - lo, b - lo, c - lo, col) for (a, b, c), col in zip(tris, colors)
                 if lo <= a < hi and lo <= b < hi and lo <= c < hi]
        i = 0
        while i < len(gtris):
            col = gtris[i][3]
            if col != cur_color:
                l1, l2 = PALETTE[col]
                f.write(f"    gsSPLightColor(LIGHT_1, 0x{l1:08x}),\n")
                f.write(f"    gsSPLightColor(LIGHT_2, 0x{l2:08x}),\n")
                cur_color = col
            if i + 1 < len(gtris) and gtris[i+1][3] == col:
                a, b, c, _ = gtris[i]; d, e, gg, _ = gtris[i+1]
                f.write(f"    gsSP2Triangles({a:2d},{b:3d},{c:3d}, 0x0,"
                        f"{d:3d},{e:3d},{gg:3d}, 0x0),\n")
                i += 2
            else:
                a, b, c, _ = gtris[i]
                f.write(f"    gsSP1Triangle({a:2d},{b:3d},{c:3d}, 0x0),\n")
                i += 1
    f.write("    gsSPEndDisplayList(),\n};\n\n")

    # wrapper: sets combine mode + a default light (first segment's color)
    l1, l2 = PALETTE[colors[0]]
    f.write(f"const Gfx otto_{name}[] = {{\n"
            f"    gsDPPipeSync(),\n"
            f"    gsDPSetCombineMode(G_CC_SHADEFADEA, G_CC_SHADEFADEA),\n"
            f"    gsSPLightColor(LIGHT_1, 0x{l1:08x}),\n"
            f"    gsSPLightColor(LIGHT_2, 0x{l2:08x}),\n"
            f"    gsSPDisplayList(otto_{name}_dl),\n"
            f"    gsSPEndDisplayList(),\n}};\n\n")


def emit_head_wrapper(state, f):
    l1, l2 = PALETTE["amber"]
    f.write(f"const Gfx otto_head_eyes_{state}[] = {{\n"
            f"    gsDPPipeSync(),\n"
            f"    gsDPSetCombineMode(G_CC_SHADEFADEA, G_CC_SHADEFADEA),\n"
            f"    gsSPDisplayList(otto_head_dl),\n"
            f"    gsSPDisplayList(otto_eyes_{state}_dl),\n"
            f"    gsSPEndDisplayList(),\n}};\n\n")


STATES = ["front", "half_closed", "closed", "dead"]


def emit_model_inc(parts):
    path = os.path.join(OUT_DIR, "model.inc.c")
    with open(path, "w") as f:
        f.write("// Otto model — generated by tools/otto_model_gen.py\n\n")
        order = ["butt", "torso", "head",
                 "eyes_front", "eyes_half_closed", "eyes_closed", "eyes_dead",
                 "left_arm", "right_arm", "left_forearm", "right_forearm",
                 "left_hand_open", "left_hand_closed",
                 "right_hand_open", "right_hand_closed",
                 "left_thigh", "right_thigh", "left_leg", "right_leg",
                 "left_foot", "right_foot"]
        for name in order:
            emit_part_dl(name, parts[name], f)
        for s in STATES:
            emit_head_wrapper(s, f)
    return path


def _head_geo(layer):
    """Geo for the face+eyes+wings branch, parameterised by render layer."""
    def dl(state):
        return f"            GEO_DISPLAY_LIST({layer}, otto_head_eyes_{state}),"
    eyes = "\n".join([dl("front"), dl("half_closed"), dl("closed"),
                      dl("front"), dl("front"), dl("front"), dl("front"), dl("dead")])
    return f"""const GeoLayout otto_geo_face_and_wings_{layer.lower()}[] = {{
   GEO_ASM(0, geo_mario_head_rotation),
   GEO_ROTATION_NODE(0x00, 0, 0, 0),
   GEO_OPEN_NODE(),
      GEO_SWITCH_CASE(0, geo_switch_mario_cap_on_off),
      GEO_OPEN_NODE(),
         GEO_SWITCH_CASE(0, geo_switch_mario_eyes),
         GEO_OPEN_NODE(),
{eyes}
         GEO_CLOSE_NODE(),
         GEO_SWITCH_CASE(0, geo_switch_mario_eyes),
         GEO_OPEN_NODE(),
{eyes}
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
      GEO_TRANSLATE_ROTATE(0, 142, -51, -126, 22, -40, -135),
      GEO_OPEN_NODE(),
         GEO_ASM(0, geo_mario_rotate_wing_cap_wings),
         GEO_ROTATION_NODE(0x00, 0, 0, 0),
         GEO_OPEN_NODE(),
            GEO_DISPLAY_LIST(LAYER_ALPHA, mario_cap_wings),
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
      GEO_TRANSLATE_ROTATE(0, 142, -51, 126, -22, 40, -135),
      GEO_OPEN_NODE(),
         GEO_ASM(1, geo_mario_rotate_wing_cap_wings),
         GEO_ROTATION_NODE(0x00, 0, 0, 0),
         GEO_OPEN_NODE(),
            GEO_DISPLAY_LIST(LAYER_ALPHA, mario_cap_wings),
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};
"""


def _hand_geo(side, layer):
    L = layer
    wings = ""
    held1 = held2 = ""
    extra = ""
    if side == "right":
        held1 = "         GEO_HELD_OBJECT(0x00, 0, 0, 0, geo_switch_mario_hand_grab_pos),\n"
        extra = f"""      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_right_hand_closed),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_right_hand_closed),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_right_hand_closed),
      GEO_OPEN_NODE(),
         GEO_DISPLAY_LIST(LAYER_ALPHA, mario_right_hand_cap_wings),
      GEO_CLOSE_NODE(),
"""
        cases = f"""      GEO_ANIMATED_PART({L}, 60, 0, 0, NULL),
      GEO_OPEN_NODE(),
         GEO_ASM(0, geo_mario_hand_foot_scaler),
         GEO_SCALE(0x00, 65536),
         GEO_OPEN_NODE(),
            GEO_DISPLAY_LIST({L}, otto_right_hand_closed_dl),
         GEO_CLOSE_NODE(),
{held1}      GEO_CLOSE_NODE(),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_right_hand_open),
      GEO_OPEN_NODE(),
{held1}      GEO_CLOSE_NODE(),
{extra}"""
    else:
        cases = f"""      GEO_ANIMATED_PART({L}, 60, 0, 0, NULL),
      GEO_OPEN_NODE(),
         GEO_ASM(1, geo_mario_hand_foot_scaler),
         GEO_SCALE(0x00, 65536),
         GEO_OPEN_NODE(),
            GEO_DISPLAY_LIST({L}, otto_left_hand_closed_dl),
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_left_hand_open),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_left_hand_closed),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_left_hand_closed),
      GEO_ANIMATED_PART({L}, 60, 0, 0, otto_left_hand_closed),
"""
    arg = 0 if side == "right" else 1
    return f"""const GeoLayout otto_geo_{side}_hand_{L.lower()}[] = {{
   GEO_SWITCH_CASE({arg}, geo_switch_mario_hand),
   GEO_OPEN_NODE(),
{cases}   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};
"""


def _body_geo(layer):
    L = layer
    fw = f"otto_geo_face_and_wings_{L.lower()}"
    lh = f"otto_geo_left_hand_{L.lower()}"
    rh = f"otto_geo_right_hand_{L.lower()}"
    return f"""const GeoLayout otto_geo_body_{L.lower()}[] = {{
   GEO_ANIMATED_PART({L}, 0, 0, 0, NULL),
   GEO_OPEN_NODE(),
      GEO_ANIMATED_PART({L}, 0, 0, 0, otto_butt),
      GEO_OPEN_NODE(),
         GEO_ASM(0, geo_move_mario_part_from_parent),
         GEO_ASM(0, geo_mario_tilt_torso),
         GEO_ROTATION_NODE(0x00, 0, 0, 0),
         GEO_OPEN_NODE(),
            GEO_ANIMATED_PART({L}, 68, 0, 0, otto_torso),
            GEO_OPEN_NODE(),
               GEO_ANIMATED_PART({L}, 87, 0, 0, NULL),
               GEO_OPEN_NODE(),
                  GEO_BRANCH(1, {fw}),
               GEO_CLOSE_NODE(),
               GEO_ANIMATED_PART({L}, 67, -10, 79, NULL),
               GEO_OPEN_NODE(),
                  GEO_ANIMATED_PART({L}, 0, 0, 0, otto_left_arm),
                  GEO_OPEN_NODE(),
                     GEO_ANIMATED_PART({L}, 65, 0, 0, otto_left_forearm),
                     GEO_OPEN_NODE(),
                        GEO_BRANCH(1, {lh}),
                     GEO_CLOSE_NODE(),
                  GEO_CLOSE_NODE(),
               GEO_CLOSE_NODE(),
               GEO_ANIMATED_PART({L}, 68, -10, -79, NULL),
               GEO_OPEN_NODE(),
                  GEO_ANIMATED_PART({L}, 0, 0, 0, otto_right_arm),
                  GEO_OPEN_NODE(),
                     GEO_ANIMATED_PART({L}, 65, 0, 0, otto_right_forearm),
                     GEO_OPEN_NODE(),
                        GEO_BRANCH(1, {rh}),
                     GEO_CLOSE_NODE(),
                  GEO_CLOSE_NODE(),
               GEO_CLOSE_NODE(),
            GEO_CLOSE_NODE(),
         GEO_CLOSE_NODE(),
         GEO_ANIMATED_PART({L}, 13, -8, 42, NULL),
         GEO_OPEN_NODE(),
            GEO_ANIMATED_PART({L}, 0, 0, 0, otto_left_thigh),
            GEO_OPEN_NODE(),
               GEO_ANIMATED_PART({L}, 89, 0, 0, otto_left_leg),
               GEO_OPEN_NODE(),
                  GEO_ANIMATED_PART({L}, 67, 0, 0, otto_left_foot),
               GEO_CLOSE_NODE(),
            GEO_CLOSE_NODE(),
         GEO_CLOSE_NODE(),
         GEO_ANIMATED_PART({L}, 13, -8, -42, NULL),
         GEO_OPEN_NODE(),
            GEO_ANIMATED_PART({L}, 0, 0, 0, otto_right_thigh),
            GEO_OPEN_NODE(),
               GEO_ANIMATED_PART({L}, 89, 0, 0, otto_right_leg),
               GEO_OPEN_NODE(),
                  GEO_ANIMATED_PART({L}, 67, 0, 0, NULL),
                  GEO_OPEN_NODE(),
                     GEO_ASM(2, geo_mario_hand_foot_scaler),
                     GEO_SCALE(0x00, 65536),
                     GEO_OPEN_NODE(),
                        GEO_DISPLAY_LIST({L}, otto_right_foot_dl),
                     GEO_CLOSE_NODE(),
                  GEO_CLOSE_NODE(),
               GEO_CLOSE_NODE(),
            GEO_CLOSE_NODE(),
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};
"""


def emit_geo_inc():
    path = os.path.join(OUT_DIR, "geo.inc.c")
    with open(path, "w") as f:
        f.write("// Otto geo layout — generated by tools/otto_model_gen.py\n")
        f.write("// Mirrors the vanilla player skeleton so mario_anims map 1:1.\n\n")
        for n in ("butt", "torso", "left_arm", "right_arm",
                  "left_forearm", "right_forearm",
                  "left_hand_open", "left_hand_closed",
                  "right_hand_open", "right_hand_closed",
                  "left_thigh", "right_thigh", "left_leg", "right_leg",
                  "left_foot"):
            f.write(f"extern const Gfx otto_{n}[];\n")
        for n in ("right_foot_dl", "left_hand_closed_dl",
                  "right_hand_closed_dl"):
            f.write(f"extern const Gfx otto_{n}[];\n")
        for s in STATES:
            f.write(f"extern const Gfx otto_head_eyes_{s}[];\n")
        f.write("\n")
        f.write(_head_geo("LAYER_OPAQUE"))
        f.write("\n")
        f.write(_head_geo("LAYER_TRANSPARENT"))
        f.write("\n")
        f.write(_hand_geo("left", "LAYER_OPAQUE"))
        f.write("\n")
        f.write(_hand_geo("right", "LAYER_OPAQUE"))
        f.write("\n")
        f.write(_body_geo("LAYER_OPAQUE"))
        f.write("\n")
        f.write(_hand_geo("left", "LAYER_TRANSPARENT"))
        f.write("\n")
        f.write(_hand_geo("right", "LAYER_TRANSPARENT"))
        f.write("\n")
        f.write(_body_geo("LAYER_TRANSPARENT"))
        f.write("\n")
        f.write("""const GeoLayout otto_geo_load_body[] = {
   GEO_SWITCH_CASE(0, geo_switch_mario_cap_effect),
   GEO_OPEN_NODE(),
      GEO_BRANCH(1, otto_geo_body_layer_opaque),
      GEO_BRANCH(1, otto_geo_body_layer_transparent), // vanish cap
      GEO_BRANCH(1, otto_geo_body_layer_opaque),      // metal cap (tint TODO)
      GEO_BRANCH(1, otto_geo_body_layer_transparent), // metal vanish
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
};

const GeoLayout otto_geo_render_body[] = {
   GEO_NODE_START(),
   GEO_OPEN_NODE(),
      GEO_RENDER_RANGE(-2048, 600),
      GEO_OPEN_NODE(),
         GEO_BRANCH(1, otto_geo_load_body),
      GEO_CLOSE_NODE(),
      GEO_RENDER_RANGE(600, 1600),
      GEO_OPEN_NODE(),
         GEO_BRANCH(1, otto_geo_load_body),
      GEO_CLOSE_NODE(),
      GEO_RENDER_RANGE(1600, 32767),
      GEO_OPEN_NODE(),
         GEO_BRANCH(1, otto_geo_load_body),
      GEO_CLOSE_NODE(),
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
};

const GeoLayout otto_geo[] = {
   GEO_SHADOW(SHADOW_CIRCLE_PLAYER, 0xB4, 100),
   GEO_OPEN_NODE(),
      GEO_SCALE(0x00, 16384),
      GEO_OPEN_NODE(),
         GEO_ASM(0, geo_mirror_mario_backface_culling),
         GEO_ASM(0, geo_mirror_mario_set_alpha),
         GEO_SWITCH_CASE(0, geo_switch_mario_stand_run),
         GEO_OPEN_NODE(),
            GEO_BRANCH(1, otto_geo_load_body),
            GEO_BRANCH(1, otto_geo_render_body),
         GEO_CLOSE_NODE(),
         GEO_ASM(1, geo_mirror_mario_backface_culling),
      GEO_CLOSE_NODE(),
   GEO_CLOSE_NODE(),
   GEO_END(),
};
""")
    return path


# --- OBJ export for preview ---------------------------------------------------
def _rot(v, ax, ay, az):
    """Rotate by az around Z, then ay around Y, then ax around X (degrees)."""
    x, y, z = v
    c, s = math.cos(math.radians(az)), math.sin(math.radians(az))
    x, y = x * c - y * s, x * s + y * c
    c, s = math.cos(math.radians(ay)), math.sin(math.radians(ay))
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(math.radians(ax)), math.sin(math.radians(ax))
    y, z = y * c - z * s, y * s + z * c
    return (x, y, z)


def _xform(mesh, off, rot=(0, 0, 0)):
    return {"verts": [tuple(_add(_rot(v, *rot), off)) for v in mesh["verts"]],
            "tris": mesh["tris"]}


def _add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def assemble_preview(parts):
    """Compose the bind pose for preview: limbs get display-only rotations so
    the pose reads naturally (+X limbs rotated to hang/splay)."""
    scene = {}
    T = (68, 0, 0); H = (87, 0, 0)
    scene["butt"] = [_xform(m, (0, 0, 0)) for m in parts["butt"]]
    scene["torso"] = [_xform(m, T) for m in parts["torso"]]
    scene["head"] = [_xform(m, _add(T, H)) for m in parts["head"]]
    scene["eyes"] = [_xform(m, _add(T, H)) for m in parts["eyes_front"]]
    for side, z, sgn in (("left", 79, -1), ("right", -79, 1)):
        sh = _add(T, (67, -10, z))
        rot = (0, sgn * 125, 0)         # swing limb axis outward/down
        scene[f"{side}_arm"] = [_xform(m, sh, rot) for m in parts[f"{side}_arm"]]
        el = _add(sh, _rot((65, 0, 0), *rot))
        scene[f"{side}_forearm"] = [_xform(m, el, rot) for m in parts[f"{side}_forearm"]]
        wr = _add(el, _rot((60, 0, 0), *rot))
        scene[f"{side}_hand"] = [_xform(m, wr, rot) for m in parts[f"{side}_hand_closed"]]
    for side, z in (("left", 42), ("right", -42)):
        hp = (13, -8, z)
        rot = (0, 0, 180)               # legs point down (-X)
        scene[f"{side}_thigh"] = [_xform(m, hp, rot) for m in parts[f"{side}_thigh"]]
        kn = _add(hp, _rot((89, 0, 0), *rot))
        scene[f"{side}_leg"] = [_xform(m, kn, rot) for m in parts[f"{side}_leg"]]
        an = _add(kn, _rot((67, 0, 0), *rot))
        scene[f"{side}_foot"] = [_xform(m, an, (0, 0, 100)) for m in parts[f"{side}_foot"]]
    return scene


def emit_obj(scene, path):
    with open(path, "w") as f:
        idx = 1
        for name, meshes in scene.items():
            for m in meshes:
                for x, y, z in m["verts"]:
                    f.write(f"v {z:.1f} {-y:.1f} {x:.1f}\n")   # obj: x=mdl left, y=mdl back, z=mdl up
                for a, b, c, col in m["tris"]:
                    f.write(f"usemtl {col}\nf {a+idx} {b+idx} {c+idx}\n")
                idx += len(m["verts"])
    return path


if __name__ == "__main__":
    parts = build_parts()
    p1 = emit_model_inc(parts)
    p2 = emit_geo_inc()
    if "--obj" in sys.argv:
        print(emit_obj(assemble_preview(parts), "/tmp/otto_assembled.obj"))
    print(f"wrote {p1}\nwrote {p2}")
