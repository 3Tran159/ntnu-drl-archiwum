import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104/SEALED_SHARP_MATCHED_OUTER/plot_mesh.npz"
HINGE = np.array([.952, .02128173276777])
SPAN = .02
ANGLES = (-2, 0, 2)
RADIUS = .25


def outline():
    with np.load(SOURCE) as data:
        points = data["xy"]
        edges = np.concatenate((data["main"], data["flap"]))
    links = {}
    for a, b in edges:
        links.setdefault(int(a), []).append(int(b))
        links.setdefault(int(b), []).append(int(a))
    if any(len(v) != 2 for v in links.values()):
        raise ValueError("Sealed profile wall edges do not form a closed contour")
    first = min(links, key=lambda i: points[i, 0])
    nodes = [first]
    prev = None
    while True:
        a, b = links[nodes[-1]]
        follow = b if a == prev else a
        if follow == first:
            break
        if follow in nodes:
            raise ValueError("Unexpected secondary edge loop")
        prev = nodes[-1]
        nodes.append(follow)
    if len(nodes) != len(links):
        raise ValueError("Missing foil contour vertices")
    return points[nodes] - HINGE


def clip(poly, aft):
    result = []
    for a,b in zip(poly, np.roll(poly,-1,axis=0)):
        inside_a = a[0] >= 0 if aft else a[0] <= 0
        inside_b = b[0] >= 0 if aft else b[0] <= 0
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(a - a[0] / (b[0]-a[0]) * (b-a))
    return np.array(result)


def rotate(poly, degrees):
    angle = math.radians(-degrees)
    c, s = math.cos(angle), math.sin(angle)
    return poly @ np.array([[c,s],[-s,c]])


def circle_angles(poly, radius):
    hits = []
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        v = b-a
        aa = float(v@v)
        bb = float(2*(a@v))
        cc = float(a@a-radius*radius)
        disc = bb*bb-4*aa*cc
        if aa == 0 or disc < 0:
            continue
        for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
            if 0 <= t < 1:
                x,z = a + t*v
                hits.append(math.atan2(z,x) % (2*math.pi))
    return sorted(hits)


def intersection(a,b):
    return max(0.0,min(a[1],b[1])-max(a[0],b[0]))


def main():
    body = outline()
    aft = clip(body, True)
    fore = clip(body, False)
    r_min = float(np.max(np.linalg.norm(aft,axis=1)))
    if not r_min < RADIUS < float(-min(body[:,0])):
        raise ValueError("Candidate rotor circle does not surround the flap or crosses the nose")
    stationary_block = circle_angles(body,RADIUS)
    if len(stationary_block)!=2 or not stationary_block[0] < math.pi < stationary_block[1]:
        raise ValueError("Unexpected foil crossings of rotor circle")
    cut = np.unique(np.round([v for v in aft if abs(v[0])<1e-12],12),axis=0)
    if len(cut)!=2:
        raise ValueError("Expected two points on original planar hinge cut")
    # The circular collar and socket use exactly the same radius. For each tested angle,
    # any point of the moving aft section entering the fore half lies inside the socket.
    entered = [clip(rotate(aft, a), False) for a in ANGLES]
    joint_r = max(float(np.max(np.linalg.norm(part, axis=1))) for part in entered) + .0001
    # Verify a continuous shared arc inside the stationary material near the upstream axis.
    # On this arc the collar and the socket have identical coordinates by construction.
    arc_intersections = circle_angles(fore,joint_r)
    if len(arc_intersections) not in (0, 2, 4):
        raise ValueError("Unexpected number of collar/forebody intersections")
    def inside(pt, poly):
        x,z = pt
        hits = 0
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if (a[1]>z) != (b[1]>z):
                if x < a[0]+(z-a[1])*(b[0]-a[0])/(b[1]-a[1]):
                    hits += 1
        return bool(hits % 2)
    seal_angles = np.linspace(math.pi-.4, math.pi+.4, 401)
    contact = all(inside(joint_r*np.array([math.cos(a),math.sin(a)]),fore) for a in seal_angles)
    if not contact:
        raise ValueError("Circular collar does not have the required shared arc")
    rows = []
    stationary_fluid = 2*math.pi-(stationary_block[1]-stationary_block[0])
    for angle, entered_part in zip(ANGLES, entered):
        shift = math.radians(-angle)
        rotor_block = [a+shift for a in stationary_block]
        common_block = intersection(stationary_block,rotor_block)
        missing = (stationary_block[1]-stationary_block[0])-common_block
        strip = RADIUS*missing
        seam = rotate(np.array(cut),angle)[:,0]
        rows.append(dict(angle_deg=angle, direct_cut_gap_mm=1000*max(0.0,float(max(seam))),
                         direct_cut_overlap_mm=1000*max(0.0,float(-min(seam))),
                         zero_clearance_collar_contact=contact and float(max(np.linalg.norm(entered_part,axis=1)))<joint_r,
                         unpaired_arc_on_each_side_mm=1000*strip,
                         unpaired_area_on_each_side_m2=strip*SPAN,
                         common_open_area_pct=100*(1-missing/stationary_fluid),
                         interface_pass=strip<1e-6))
    answer=dict(status="HOLD_SLIDING_INTERFACE", stage="geometric_precheck_no_vof",
                source=str(SOURCE), foil_vertices=len(body), span_m=SPAN,
                hinge_x_m=float(HINGE[0]), hinge_z_m=float(HINGE[1]),
                rotor_interface_radius_m=RADIUS, minimum_radius_to_enclose_flap_m=r_min,
                joint_collar_radius_m=joint_r, contact_arc_verified_m=joint_r*.8,
                stationary_fluid_interface_area_m2=RADIUS*stationary_fluid*SPAN,
                max_allowed_unpaired_arc_m=1e-6, tests=rows,
                native_star_solver_steps=0, gpu_test_started=False,
                result_scope="Geometric screen for concentric rigid rotation of a body-fitted local rotor zone; no claim about STAR face intersections")
    (HERE/"RESULT.json").write_text(json.dumps(answer,indent=2)+"\n",encoding="utf8")
    print(json.dumps(answer,indent=2))


if __name__ == "__main__":
    main()
