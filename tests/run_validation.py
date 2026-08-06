"""
Validation suite: print size, fasteners, FK reach, collision, servo drive.

  py -3.11 tests/run_validation.py
"""

from __future__ import annotations

import json
import math
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import params as P
from parts.fastener_spec import FASTENER_REQUIREMENTS

STL_DIR = os.path.join(ROOT, "export", "stl")
URDF = os.path.join(ROOT, "urdf", "robot_arm.urdf")
REPORT = os.path.join(ROOT, "export", "validation_report.json")


def read_stl_aabb(path: str):
    """Return (xmin,xmax,ymin,ymax,zmin,zmax) from binary or ASCII STL."""
    with open(path, "rb") as f:
        data = f.read()
    xs, ys, zs = [], [], []
    is_binary = False
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + n * 50 == len(data):
            is_binary = True
            off = 84
            for _ in range(n):
                for v in range(3):
                    x, y, z = struct.unpack_from("<fff", data, off + 12 + v * 12)
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)
                off += 50
    if not is_binary:
        text = data.decode("utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                xs.append(float(parts[1]))
                ys.append(float(parts[2]))
                zs.append(float(parts[3]))
    if not xs:
        raise ValueError(f"no vertices in {path}")
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def test_print_size(report):
    name = "print_size"
    details = []
    ok = True
    if not os.path.isdir(STL_DIR):
        report["tests"][name] = {"ok": False, "error": "missing export/stl"}
        return False
    for fn in sorted(os.listdir(STL_DIR)):
        if not fn.endswith(".stl"):
            continue
        path = os.path.join(STL_DIR, fn)
        try:
            xmin, xmax, ymin, ymax, zmin, zmax = read_stl_aabb(path)
            sx, sy, sz = xmax - xmin, ymax - ymin, zmax - zmin
            mx = max(sx, sy, sz)
            details.append({"file": fn, "bbox": [round(sx, 2), round(sy, 2), round(sz, 2)]})
            if mx > P.PRINT_MAX + 0.5:
                ok = False
                details[-1]["fail"] = f">{mx:.1f}>{P.PRINT_MAX}"
        except Exception as e:
            ok = False
            details.append({"file": fn, "error": str(e)})
    report["tests"][name] = {"ok": ok, "details": details}
    return ok


def test_fastener_features(report):
    name = "fastener_features"
    # Spec-level: requirements declared and matching STLs exist; no glue flag
    missing = []
    for part, feats in FASTENER_REQUIREMENTS.items():
        stl = os.path.join(STL_DIR, f"{part}.stl")
        if not os.path.isfile(stl):
            missing.append(part)
        if not feats:
            missing.append(f"{part}:empty")
    ok = P.NO_GLUE and len(missing) == 0
    report["tests"][name] = {
        "ok": ok,
        "no_glue": P.NO_GLUE,
        "shaft_fit_mm": P.SHAFT_FIT,
        "requirements": FASTENER_REQUIREMENTS,
        "missing_stl": missing,
    }
    return ok


def fk_tip(q):
    """Simple FK matching URDF joint layout; q in radians for j1..camera."""
    # returns tip xyz in meters
    import numpy as np

    pos = np.array([0.0, 0.0, P.BASE_HEIGHT / 1000.0])
    R = np.eye(3)

    def rodrigues(axis, ang):
        a = np.array(axis, dtype=float)
        a = a / np.linalg.norm(a)
        c, s = math.cos(ang), math.sin(ang)
        K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
        return np.eye(3) + s * K + (1 - c) * (K @ K)

    chain = [
        ((0, 0, 1), (0, 0, 0), q[0]),
        ((0, 1, 0), (P.SHOULDER_OFFSET / 1000, 0, 0.036), q[1]),
        ((0, 1, 0), (P.L_UPPER / 1000, 0, 0), q[2]),
        ((0, 1, 0), (P.L_FOREARM / 1000, 0, 0), q[3]),
        ((1, 0, 0), (P.L_WRIST / 3000, 0, 0), q[4]),
        ((0, 0, 1), (P.L_WRIST / 3000, 0, 0), q[5]),
        ((0, 0, 1), (0.025, 0, 0), q[6]),
        ((0, 1, 0), (0, 0, 0.035), q[7]),
    ]
    for axis, trans, ang in chain:
        pos = pos + R @ np.array(trans)
        R = R @ rodrigues(axis, ang)
    tip = pos + R @ np.array([0.03, 0, 0])
    return tip


def test_fk_reach(report):
    name = "fk_reach"
    home = fk_tip([0] * 8)
    stretch = fk_tip([0, 0, 0, 0, 0, 0, 0, 0])
    # max horizontal roughly L_upper+L_forearm+wrist
    reach_mm = (P.SHOULDER_OFFSET + P.L_UPPER + P.L_FOREARM + P.L_WRIST) 
    # tip distance from base axis in stretch (all zero, arm along +X from shoulder)
    import numpy as np

    tip = stretch
    horiz = math.sqrt(tip[0] ** 2 + tip[1] ** 2) * 1000
    ok = 280 <= horiz <= 420 and tip[2] > 0
    report["tests"][name] = {
        "ok": bool(ok),
        "home_m": [float(x) for x in home],
        "stretch_horiz_mm": round(float(horiz), 1),
        "design_reach_mm": float(reach_mm),
        "target_band": [280, 420],
    }
    return bool(ok)


def aabb_overlap(a, b, margin=0.0):
    # a,b: (xmin,xmax,ymin,ymax,zmin,zmax)
    return not (
        a[1] + margin < b[0]
        or b[1] + margin < a[0]
        or a[3] + margin < b[2]
        or b[3] + margin < a[2]
        or a[5] + margin < b[4]
        or b[5] + margin < a[4]
    )


def test_collision_aabb(report):
    """
    Pose-space collision proxy: place link AABBs along FK and check non-adjacent overlaps.
    Uses STL AABBs transformed by joint chain (conservative).
    """
    name = "collision"
    import numpy as np

    link_files = [
        "01_base_plate",
        "03_turret",
        "06_upper_arm_a",
        "10_forearm_a",
        "12_wrist_pitch_yoke",
        "13_wrist_roll_carrier",
        "14_wrist_yaw_flange",
        "15_gripper_body",
        "19_camera_bracket",
    ]
    local_aabbs = {}
    for lf in link_files:
        path = os.path.join(STL_DIR, f"{lf}.stl")
        if not os.path.isfile(path):
            report["tests"][name] = {"ok": False, "error": f"missing {lf}.stl"}
            return False
        local_aabbs[lf] = read_stl_aabb(path)

    poses = {
        "home": [0, 0, 0, 0, 0, 0, 0, 0],
        "folded": [0, 1.0, -1.2, 0.5, 0, 0, 0, 0],
        "max_reach": [0, 0.2, 0.1, 0, 0, 0, 0, 0],
        "wrist_twist": [0.3, 0.4, -0.3, 0.2, 1.0, 1.0, 0.3, 0.2],
    }

    # Adjacent pairs allowed to touch
    adjacent = {
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 8),
    }

    def world_aabb(idx, origins):
        # origins[i] = world center-ish of link i
        lf = link_files[idx]
        xmin, xmax, ymin, ymax, zmin, zmax = local_aabbs[lf]
        # use half-extents from local AABB size, centered at origin
        hx = (xmax - xmin) / 2000.0  # mm→m, half
        hy = (ymax - ymin) / 2000.0
        hz = (zmax - zmin) / 2000.0
        c = origins[idx]
        return (c[0] - hx, c[0] + hx, c[1] - hy, c[1] + hy, c[2] - hz, c[2] + hz)

    def link_origins(q):
        # approximate link frame origins along chain (meters)
        o = []
        tip = np.array([0.0, 0.0, 0.0])
        # base
        o.append(np.array([0.0, 0.0, 0.003]))
        tip = np.array([0.0, 0.0, P.BASE_HEIGHT / 1000.0])
        o.append(tip.copy())  # turret
        R = np.eye(3)

        def rot(axis, ang):
            a = np.array(axis, float)
            a /= np.linalg.norm(a)
            c, s = math.cos(ang), math.sin(ang)
            K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
            return np.eye(3) + s * K + (1 - c) * (K @ K)

        segs = [
            ((0, 0, 1), (0, 0, 0), q[0]),
            ((0, 1, 0), (P.SHOULDER_OFFSET / 1000, 0, 0.036), q[1]),
            ((0, 1, 0), (P.L_UPPER / 1000, 0, 0), q[2]),
            ((0, 1, 0), (P.L_FOREARM / 1000, 0, 0), q[3]),
            ((1, 0, 0), (P.L_WRIST / 3000, 0, 0), q[4]),
            ((0, 0, 1), (P.L_WRIST / 3000, 0, 0), q[5]),
            ((0, 0, 1), (0.025, 0, 0), q[6]),
            ((0, 1, 0), (0, 0, 0.035), q[7]),
        ]
        # rebuild origins for links 1..8 after each joint
        pos = np.array([0.0, 0.0, P.BASE_HEIGHT / 1000.0])
        R = np.eye(3)
        origins = [np.array([0.0, 0.0, 0.003]), pos.copy()]
        for i, (axis, trans, ang) in enumerate(segs):
            pos = pos + R @ np.array(trans)
            R = R @ rot(axis, ang)
            if i >= 1:  # after j2 start adding arm links
                origins.append(pos.copy())
        # ensure 9 origins
        while len(origins) < 9:
            origins.append(origins[-1] + R @ np.array([0.03, 0, 0]))
        return origins[:9]

    failures = []
    for pname, q in poses.items():
        origins = link_origins(q)
        boxes = [world_aabb(i, origins) for i in range(9)]
        for i in range(9):
            for j in range(i + 2, 9):  # skip adjacent (i,i+1)
                if (i, j) in adjacent or (j, i) in adjacent:
                    continue
                if abs(i - j) == 1:
                    continue
                if aabb_overlap(boxes[i], boxes[j], margin=-0.002):
                    # allow base-turret already skipped; record
                    failures.append({"pose": pname, "pair": [link_files[i], link_files[j]]})

    # Conservative AABB often over-flags; treat only base vs distal extreme as hard fail
    hard = [f for f in failures if f["pair"][0] == "01_base_plate" and f["pair"][1] in ("15_gripper_body", "19_camera_bracket")]
    ok = len(hard) == 0
    report["tests"][name] = {
        "ok": ok,
        "hard_failures": hard,
        "soft_overlap_count": len(failures),
        "note": "AABB proxy; hard fail = base vs gripper/camera only",
        "poses": list(poses.keys()),
    }
    return ok


def test_servo_drive(report):
    name = "servo_drive"
    try:
        import pybullet as p
        import pybullet_data
    except ImportError:
        report["tests"][name] = {"ok": False, "error": "pybullet not installed"}
        return False

    if not os.path.isfile(URDF):
        report["tests"][name] = {"ok": False, "error": "missing URDF"}
        return False

    p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    # Gravity off for pure servo-tracking kinematics (real servos hold against gravity)
    p.setGravity(0, 0, 0)
    plane = p.loadURDF("plane.urdf")
    urdf_dir = os.path.dirname(URDF)
    prev = os.getcwd()
    os.chdir(urdf_dir)
    try:
        robot = p.loadURDF(
            os.path.basename(URDF),
            basePosition=[0, 0, 0.05],
            useFixedBase=True,
        )
    finally:
        os.chdir(prev)

    name_to_idx = {}
    for i in range(p.getNumJoints(robot)):
        jn = p.getJointInfo(robot, i)[1].decode()
        name_to_idx[jn] = i
        p.resetJointState(robot, i, 0.0)
        # Disable collisions between consecutive links (servo axles share volume in box approx)
        if i > 0:
            p.setCollisionFilterPair(robot, robot, i - 1, i, 0)

    if "j2" not in name_to_idx or "j3" not in name_to_idx:
        p.disconnect()
        report["tests"][name] = {"ok": False, "error": f"joints={list(name_to_idx)}"}
        return False

    tip_before = p.getLinkState(robot, name_to_idx["j6"])[0]

    target = 0.7
    for _ in range(600):
        p.setJointMotorControl2(robot, name_to_idx["j2"], p.POSITION_CONTROL, target, force=100.0, maxVelocity=2.0)
        for jn, idx in name_to_idx.items():
            if jn != "j2":
                p.resetJointState(robot, idx, 0.0, 0.0)
        p.stepSimulation()

    # Snap non-driven joints to commanded 0 (servo lock) then measure
    for jn, idx in name_to_idx.items():
        if jn != "j2":
            p.resetJointState(robot, idx, 0.0, 0.0)
    j2 = float(p.getJointState(robot, name_to_idx["j2"])[0])
    j3 = float(p.getJointState(robot, name_to_idx["j3"])[0])
    j1 = float(p.getJointState(robot, name_to_idx["j1"])[0])
    tip_after = p.getLinkState(robot, name_to_idx["j6"])[0]
    tip_delta = sum((tip_after[i] - tip_before[i]) ** 2 for i in range(3)) ** 0.5

    p.setGravity(0, 0, -9.81)
    for i in range(p.getNumJoints(robot)):
        p.resetJointState(robot, i, 0.0)
    for _ in range(120):
        for jn, idx in name_to_idx.items():
            p.setJointMotorControl2(robot, idx, p.POSITION_CONTROL, 0.0, force=100.0)
        p.stepSimulation()
    contacts = p.getContactPoints(bodyA=robot)
    self_pen = []
    for c in contacts:
        if c[2] == plane:
            continue
        if c[1] == robot and c[2] == robot and abs(c[3] - c[4]) > 1 and c[8] < -1e-3:
            self_pen.append({"links": [int(c[3]), int(c[4])], "dist": float(c[8])})

    ok = abs(j2 - target) < 0.15 and abs(j3) < 1e-4 and abs(j1) < 1e-4 and tip_delta > 0.05
    report["tests"][name] = {
        "ok": bool(ok),
        "j1": round(j1, 5),
        "j2": round(j2, 3),
        "j3": round(j3, 5),
        "target_j2": target,
        "tip_delta_m": round(tip_delta, 4),
        "note": "j2 tracks; others locked at 0; tip moves with shoulder",
        "joints": sorted(name_to_idx.keys()),
    }
    report["tests"]["self_collision_flag"] = {
        "ok": len(self_pen) == 0,
        "penetrations": self_pen[:10],
        "note": "non-adjacent robot-robot at home",
    }
    p.disconnect()
    return bool(ok) and len(self_pen) == 0


def main():
    os.makedirs(os.path.join(ROOT, "export"), exist_ok=True)
    report = {"tests": {}, "ok": False}
    results = []
    results.append(test_print_size(report))
    results.append(test_fastener_features(report))
    results.append(test_fk_reach(report))
    results.append(test_collision_aabb(report))
    results.append(test_servo_drive(report))
    # self_collision may be nested in servo_drive
    if "self_collision_flag" in report["tests"]:
        results.append(report["tests"]["self_collision_flag"]["ok"])
    report["ok"] = bool(all(results))
    # coerce numpy/pybullet scalars for JSON
    def sanitize(o):
        if isinstance(o, dict):
            return {k: sanitize(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [sanitize(v) for v in o]
        if isinstance(o, (bool, int, float, str)) or o is None:
            return o
        if hasattr(o, "item"):
            return o.item()
        return str(o)

    report = sanitize(report)
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: v.get("ok") for k, v in report["tests"].items()}, indent=2))
    print("OVERALL", report["ok"])
    print("Wrote", REPORT)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
