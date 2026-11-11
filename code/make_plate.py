import json, math, os

OUT_DIR = r"D:\deepseek\CreoAuto\plans"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 890.0, 890.0
R = 445.0
BOTTOM_FLAT = 412.0
LEFT_FLAT = 239.0
RIGHT_FLAT = LEFT_FLAT + BOTTOM_FLAT
CHAMFER_L = 51.0
CHAMFER_R = 57.0
THICK = 2.0
NDIV = 40
Y_SIDE = 445.0          # side stays vertical down to this height, then curves in


def circle_center(p1, p2, r):
    """Center of the circle with radius r passing through p1 and p2 (two solutions)."""
    (x1, y1), (x2, y2) = p1, p2
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    h = math.sqrt(max(r * r - (d / 2.0) ** 2, 0.0))
    ux, uy = -dy / d, dx / d
    return (mx + h * ux, my + h * uy), (mx - h * ux, my - h * uy)


def arc_points(center, r, p_start, p_end, n=NDIV):
    cx, cy = center
    a0 = math.atan2(p_start[1] - cy, p_start[0] - cx)
    a1 = math.atan2(p_end[1] - cy, p_end[0] - cx)
    # shortest sweep
    while a1 - a0 > math.pi:
        a1 -= 2 * math.pi
    while a1 - a0 < -math.pi:
        a1 += 2 * math.pi
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append([cx + r * math.cos(a), cy + r * math.sin(a)])
    pts[0] = list(p_start)
    pts[-1] = list(p_end)
    return pts


pL1, pL2 = (0.0, Y_SIDE), (LEFT_FLAT, 0.0)
cands = circle_center(pL1, pL2, R)
# pick the center that lies inside the part (larger x)
c_left = max(cands, key=lambda c: c[0])
pR1, pR2 = (RIGHT_FLAT, 0.0), (W, Y_SIDE)
cands_r = circle_center(pR1, pR2, R)
c_right = min(cands_r, key=lambda c: c[0])   # mirrored, inside means smaller x than outside

left_arc = arc_points(c_left, R, pL1, pL2)
right_arc = arc_points(c_right, R, pR1, pR2)

y_top_side = H - CHAMFER_L

plan = {
    "model_name": "plate_890",
    "model_type": "part",
    "operations": [
        {
            "op": "sketch",
            "label": "profile",
            "plane": "XY",
            "endpoint_policy": "weld",
            "snap_endpoints": True,
            "closure_tolerance_mm": 0.02,
            "max_endpoint_move_mm": 0.05,
            "entities": [
                {"type": "line", "name": "l_chamfer_left", "start": [0.0, H - CHAMFER_L], "end": [CHAMFER_L, H]},
                {"type": "line", "name": "l_top", "start": [CHAMFER_L, H], "end": [W - CHAMFER_R, H]},
                {"type": "line", "name": "l_chamfer_right", "start": [W - CHAMFER_R, H], "end": [W, H - CHAMFER_R]},
                {"type": "line", "name": "l_right", "start": [W, H - CHAMFER_R], "end": [W, Y_SIDE]},
                {"type": "line", "name": "l_bottom", "start": [RIGHT_FLAT, 0.0], "end": [LEFT_FLAT, 0.0]},
                {"type": "line", "name": "l_left", "start": [0.0, Y_SIDE], "end": [0.0, H - CHAMFER_L]},
                {"type": "polyline", "name": "a_left", "points": left_arc, "closed": False},
                {"type": "polyline", "name": "a_right", "points": right_arc, "closed": False},
                {"type": "circle", "name": "hole_left", "center": [388.0, 833.0], "radius": 25.5},
                {"type": "circle", "name": "hole_right", "center": [833.0, 833.0], "radius": 25.5},
            ],
        },
        {"op": "extrude", "label": "plate", "sketch": "profile", "depth": THICK},
        {"op": "save"},
    ],
}

path = os.path.join(OUT_DIR, "plate_890.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(plan, fh, ensure_ascii=False, indent=2)

print("left  center:", [round(v, 3) for v in c_left])
print("right center:", [round(v, 3) for v in c_right])
print("left arc endpoints:", left_arc[0], left_arc[-1])
print("right arc endpoints:", right_arc[0], right_arc[-1])
print("written:", path)
