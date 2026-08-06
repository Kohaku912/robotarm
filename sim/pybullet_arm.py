"""
PyBullet GUI — operate the completed arm with servo sliders.

  py -3.11 -m pip install pybullet
  py -3.11 sim/pybullet_arm.py
"""

from __future__ import annotations

import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URDF = os.path.join(ROOT, "urdf", "robot_arm.urdf")
MESH_DIR = os.path.join(ROOT, "urdf", "meshes")

JOINT_ORDER = ["j1", "j2", "j3", "j4", "j5", "j6", "gripper", "camera_tilt"]


def check_assets():
    if not os.path.isfile(URDF):
        return False, f"Missing URDF: {URDF}\nRun generate_arm.py in FreeCAD first."
    if not os.path.isdir(MESH_DIR) or not os.listdir(MESH_DIR):
        return False, f"Missing meshes in {MESH_DIR}"
    return True, "ok"


def main(gui: bool = True):
    ok, msg = check_assets()
    if not ok:
        print(msg)
        raise SystemExit(1)

    try:
        import pybullet as p
        import pybullet_data
    except ImportError as e:
        print("Install with: py -3.11 -m pip install pybullet")
        raise SystemExit(1) from e

    cid = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    # Load URDF with cwd = urdf folder so relative mesh paths resolve
    urdf_dir = os.path.dirname(URDF)
    prev = os.getcwd()
    os.chdir(urdf_dir)
    try:
        p.setGravity(0, 0, -9.81)
        p.setRealTimeSimulation(0)
        p.loadURDF("plane.urdf")
        robot = p.loadURDF(
            os.path.basename(URDF),
            basePosition=[0, 0, 0],
            useFixedBase=True,
            flags=p.URDF_USE_SELF_COLLISION_EXCLUDE_PARENT,
        )
    finally:
        os.chdir(prev)

    name_to_idx = {}
    for i in range(p.getNumJoints(robot)):
        info = p.getJointInfo(robot, i)
        jname = info[1].decode("utf-8")
        name_to_idx[jname] = i
        p.resetJointState(robot, i, 0.0)
        p.setJointMotorControl2(robot, i, p.POSITION_CONTROL, 0.0, force=12.0)

    print("Joints:", sorted(name_to_idx.keys()))
    if len(name_to_idx) < 6:
        print("ERROR: expected >=6 joints")
        p.disconnect()
        raise SystemExit(2)

    sliders = {}
    if gui:
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        for jn in JOINT_ORDER:
            if jn not in name_to_idx:
                continue
            info = p.getJointInfo(robot, name_to_idx[jn])
            lo, hi = float(info[8]), float(info[9])
            if lo >= hi:
                lo, hi = -1.57, 1.57
            sliders[jn] = p.addUserDebugParameter(jn, lo, hi, 0.0)
        tip_id = p.addUserDebugText("tip", [0, 0, 0.5], [0, 0, 0], 1.2)
    else:
        tip_id = -1

    print("PyBullet GUI ready — move sliders to command servos (gravity on).")
    t0 = time.time()
    try:
        while p.isConnected():
            if gui:
                for jn, sid in sliders.items():
                    target = p.readUserDebugParameter(sid)
                    force = 25.0 if jn in ("j1", "j2") else 10.0
                    p.setJointMotorControl2(
                        robot,
                        name_to_idx[jn],
                        p.POSITION_CONTROL,
                        targetPosition=target,
                        force=force,
                        maxVelocity=2.5,
                    )
                # tip debug from last link
                last = name_to_idx.get("camera_tilt") or name_to_idx.get("gripper")
                if last is not None:
                    ls = p.getLinkState(robot, last)
                    xyz = ls[0]
                    n_c = len(p.getContactPoints(bodyA=robot))
                    txt = f"tip=({xyz[0]:.2f},{xyz[1]:.2f},{xyz[2]:.2f}) contacts={n_c}"
                    p.addUserDebugText(txt, [xyz[0], xyz[1], xyz[2] + 0.05], [0.1, 0.1, 0.1], 1.1, lifeTime=0.2)
            else:
                t = time.time() - t0
                for jn in ("j1", "j2", "j3"):
                    if jn in name_to_idx:
                        p.setJointMotorControl2(
                            robot,
                            name_to_idx[jn],
                            p.POSITION_CONTROL,
                            0.5 * math.sin(t * (0.5 + 0.1 * JOINT_ORDER.index(jn))),
                            force=20.0,
                        )
                if t > 3:
                    print("direct-mode demo OK")
                    break
            p.stepSimulation()
            time.sleep(1.0 / 240.0)
    except KeyboardInterrupt:
        pass
    p.disconnect()


if __name__ == "__main__":
    main(gui="--direct" not in sys.argv)
