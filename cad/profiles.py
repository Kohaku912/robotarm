"""2D sketch profile definitions (point loops) used for Pad and SVG export."""

from __future__ import annotations

from typing import Dict, List, Tuple

import params as P

Point2 = Tuple[float, float]


def rect(cx: float, cy: float, w: float, h: float) -> List[Point2]:
    return [
        (cx - w / 2, cy - h / 2),
        (cx + w / 2, cy - h / 2),
        (cx + w / 2, cy + h / 2),
        (cx - w / 2, cy + h / 2),
    ]


def base_plate_profile() -> List[Point2]:
    # approximated as outer square for SVG; actual part uses cylinder
    r = P.BASE_OD / 2
    n = 32
    import math

    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def u_yoke_side_profile(servo: dict, cheek_h: float, arm_l: float) -> List[Point2]:
    """Side view of U-cheek (XZ): length along X, height Z."""
    return rect(arm_l / 2, cheek_h / 2, arm_l, cheek_h)


def ibeam_side_profile(length: float, height: float) -> List[Point2]:
    return rect(length / 2, 0, length, height)


def servo_pocket_xy(servo: dict, extra: float = None) -> List[Point2]:
    e = P.SERVO_POCKET_EXTRA if extra is None else extra
    return rect(0, 0, servo["body_l"] + 2 * e, servo["body_w"] + 2 * e)


def horn_plate_profile(d: float) -> List[Point2]:
    return rect(0, 0, d + 8, d + 8)


def gripper_body_profile() -> List[Point2]:
    return rect(0, 0, P.GRIPPER_BODY_L, P.GRIPPER_BODY_W)


def camera_board_slot_profile() -> List[Point2]:
    return rect(0, 0, P.CAM_BOARD_L + 2 * P.CAM_SLOT_CLEAR, P.CAM_BOARD_W + 2 * P.CAM_SLOT_CLEAR)


PROFILES: Dict[str, List[Point2]] = {}


def all_profiles() -> Dict[str, List[Point2]]:
    return {
        "base_plate": base_plate_profile(),
        "j2_u_cheek": u_yoke_side_profile(P.MG996R, 55.0, 52.0),
        "upper_ibeam": ibeam_side_profile(P.UPPER_SEG_A, P.LINK_HEIGHT),
        "fore_ibeam": ibeam_side_profile(P.FORE_SEG_A, P.LINK_HEIGHT - 2),
        "mg996r_pocket": servo_pocket_xy(P.MG996R),
        "mg90s_pocket": servo_pocket_xy(P.MG90S),
        "horn_plate_large": horn_plate_profile(P.MG996R["horn_circle_d"]),
        "horn_plate_small": horn_plate_profile(P.MG90S["horn_circle_d"]),
        "gripper_body": gripper_body_profile(),
        "camera_slot": camera_board_slot_profile(),
    }
