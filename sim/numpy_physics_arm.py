"""
Lightweight physics fallback (no PyBullet): serial-chain arm with gravity + PD servo tracking.

  py -3.11 sim/numpy_physics_arm.py

Uses URDF joint limits from params.py. Visualizes with matplotlib if available.
"""

from __future__ import annotations

import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import params as P

# Link lengths (m) and masses (kg) — approximate printed PLA
LINKS = [
    ("j1", 0.0, 0.12, (0, 0, 1)),          # yaw about Z at base
    ("j2", P.SHOULDER_OFFSET / 1000, 0.08, (0, 1, 0)),
    ("j3", P.L_UPPER / 1000, 0.06, (0, 1, 0)),
    ("j4", P.L_FOREARM / 1000, 0.04, (0, 1, 0)),
    ("j5", 0.04, 0.03, (1, 0, 0)),
    ("j6", 0.03, 0.02, (0, 0, 1)),
    ("gripper", 0.02, 0.04, (0, 0, 1)),
    ("camera_tilt", 0.0, 0.015, (0, 1, 0)),
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    import numpy as np

    n = len(LINKS)
    q = np.zeros(n)
    qd = np.zeros(n)
    q_des = np.zeros(n)
    dt = 1.0 / 120.0
    g = 9.81
    kp, kd = 40.0, 4.0

    print("numpy physics arm — sinusoidal servo commands under gravity")
    print("joints:", [L[0] for L in LINKS])

    use_mpl = "--no-plot" not in sys.argv
    if use_mpl:
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

            plt.ion()
            fig = plt.figure()
            ax = fig.add_subplot(111, projection="3d")
        except Exception:
            use_mpl = False
            print("matplotlib not available; running headless")

    t0 = time.time()
    steps = 600 if "--no-plot" in sys.argv else 2400
    for step in range(steps):
        t = time.time() - t0
        # servo targets
        for i, (name, _, _, _) in enumerate(LINKS):
            lo, hi = P.JOINT_LIMITS.get(name, (-1.57, 1.57))
            q_des[i] = clamp(0.5 * math.sin(t * (0.6 + 0.05 * i)), lo, hi)

        # crude gravity torque: each distal mass * g * horizontal lever about pitch axes
        tau_g = np.zeros(n)
        # accumulate CoM positions with FK
        pos = np.array([0.0, 0.0, P.BASE_HEIGHT / 1000.0])
        R = np.eye(3)
        positions = [pos.copy()]
        for i, (name, length, mass, axis) in enumerate(LINKS):
            a = np.array(axis, dtype=float)
            a = a / np.linalg.norm(a)
            # Rodriguez rotation
            c, s = math.cos(q[i]), math.sin(q[i])
            K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
            Ri = np.eye(3) + s * K + (1 - c) * (K @ K)
            R = R @ Ri
            # link extends mostly along local X after previous joints
            local = np.array([length, 0.0, 0.0])
            mid = pos + R @ (local * 0.5)
            # gravity torque about joint axis (world)
            r = mid - positions[-1]
            fg = np.array([0.0, 0.0, -mass * g])
            tau_vec = np.cross(r, fg)
            axis_w = R @ a
            tau_g[i] = float(np.dot(tau_vec, axis_w))
            pos = pos + R @ local
            positions.append(pos.copy())

        # PD servo motor torques (position-controlled servos)
        tau = kp * (q_des - q) - kd * qd + 0.15 * tau_g
        # integrate (simple inertia)
        inertia = np.array([0.02, 0.03, 0.02, 0.01, 0.008, 0.006, 0.005, 0.004])
        qdd = tau / inertia
        qd = qd + qdd * dt
        q = q + qd * dt
        for i, (name, _, _, _) in enumerate(LINKS):
            lo, hi = P.JOINT_LIMITS.get(name, (-1.57, 1.57))
            if q[i] < lo or q[i] > hi:
                q[i] = clamp(q[i], lo, hi)
                qd[i] = 0.0

        if use_mpl and step % 4 == 0:
            ax.cla()
            xs, ys, zs = zip(*positions)
            ax.plot(xs, ys, zs, "-o", color="#226")
            ax.set_xlim(-0.4, 0.4)
            ax.set_ylim(-0.4, 0.4)
            ax.set_zlim(0, 0.5)
            ax.set_title(f"t={t:.1f}s  tip=({positions[-1][0]:.2f},{positions[-1][1]:.2f},{positions[-1][2]:.2f})")
            plt.pause(0.001)

        if "--no-plot" in sys.argv:
            time.sleep(0)  # spin

    tip = positions[-1]
    print(f"done. final tip xyz_m=({tip[0]:.3f}, {tip[1]:.3f}, {tip[2]:.3f}) q={np.round(q,2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
