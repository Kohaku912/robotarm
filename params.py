"""Compact 6-DOF arm parameters (mm). Replaces V5_2-style tall gear base / outer cradles."""

# --- Build volume ---
PRINT_MAX = 180.0
PRINT_SAFE = 170.0
WALL = 2.6
CLEAR = 0.30
PLA_DENSITY = 1.24e-3  # g/mm^3

# Target home envelope (assembly)
ENVELOPE_MAX = (280.0, 120.0, 160.0)

# --- Payload / kinematics ---
PAYLOAD_G = 100.0
TARGET_REACH_MM = 300.0  # slightly shorter for compact + 2x MG996R

L_UPPER = 110.0
L_FOREARM = 95.0
L_WRIST = 55.0

# Low base stack (no tall gear pit)
BASE_PLATE = 6.0
BASE_SERVO_WELL = 40.0  # MG996R mostly inside
TURNTABLE_Z = 48.0  # top of rotating deck
SHOULDER_PIVOT_Z = 58.0  # J2 axis height above base floor
SHOULDER_OFFSET = 22.0  # J1 axis to J2 axis horizontal

UPPER_SEG_A = 55.0
UPPER_SEG_B = 55.0
FORE_SEG_A = 48.0
FORE_SEG_B = 47.0

# --- Plates (servos INSIDE) ---
PLATE_T = 5.0
# Inner clear width ≈ servo body_w + 2*bearing_w + clearance
YOKE_INNER = 32.0  # for MG996R inside (~19.7 + bearings)
LINK_INNER = 26.0  # for MG90S inside
YOKE_HEIGHT = 55.0  # short shoulder U
LINK_HEIGHT = 28.0
LINK_FLANGE = 4.0
LINK_WEB = 3.0

BASE_OD = 110.0
BASE_THICK = BASE_PLATE
BASE_MOUNT_HOLE_PCD = 90.0
BASE_MOUNT_HOLES = 4

# --- Servos ---
MG996R = {
    "body_l": 40.7,
    "body_w": 19.7,
    "body_h": 36.0,
    "body_h_total": 42.9,
    "tab_l": 54.5,
    "tab_w": 19.7,
    "tab_t": 2.5,
    "tab_z_from_bottom": 27.5,
    "tab_hole_along": 49.5,
    "tab_hole_across": 10.0,
    "tab_hole_d": 3.2,
    "spline_d": 5.9,
    "spline_h": 3.8,
    "horn_circle_d": 20.0,
    "cable_clear_w": 8.0,
    "cable_clear_h": 4.0,
    "torque_kgcm": 10.0,
}

MG90S = {
    "body_l": 22.8,
    "body_w": 12.2,
    "body_h": 22.5,
    "body_h_total": 28.5,
    "tab_l": 32.5,
    "tab_w": 12.2,
    "tab_t": 2.0,
    "tab_z_from_bottom": 16.0,
    "tab_hole_along": 28.0,
    "tab_hole_across": 0.0,
    "tab_hole_d": 2.2,
    "spline_d": 4.8,
    "spline_h": 3.0,
    "horn_circle_d": 16.0,
    "cable_clear_w": 6.0,
    "cable_clear_h": 3.5,
    "torque_kgcm": 2.2,
}

SERVO_POCKET_EXTRA = 0.35

F695ZZ = {
    "id": 5.0,
    "od": 13.0,
    "width": 4.0,
    "flange_od": 15.0,
    "flange_t": 1.0,
    "seat_od": 13.15,
    "flange_seat": 15.2,
}

F685ZZ = {
    "id": 5.0,
    "od": 11.0,
    "width": 5.0,
    "flange_od": 12.5,
    "flange_t": 1.0,
    "seat_od": 11.15,
    "flange_seat": 12.7,
}

SHAFT_D = 5.0
SHAFT_FIT = 4.95
SHAFT_CLEAR = 5.15
STOP_ANGLE_DEG = 90.0
NO_GLUE = True

M3 = {
    "thread_d": 3.0,
    "clear_d": 3.3,
    "head_d": 6.0,
    "head_h": 2.0,
    "insert_od": 6.0,
    "insert_hole": 5.9,
    "insert_depth": 5.5,
    "lengths": (5, 6, 8, 10, 12, 14, 16, 18, 20),
}

M4 = {
    "thread_d": 4.0,
    "clear_d": 4.3,
    "head_d": 7.0,
    "head_h": 2.0,
    "insert_od": 5.0,
    "insert_hole": 4.9,
    "insert_depth": 5.5,
    "lengths": (5, 6, 8, 10, 12),
}

DOWEL_D = 4.0
SPLIT_BOLT_SPACING = 14.0

GRIPPER_OPEN = 35.0
FINGER_LEN = 35.0
FINGER_THICK = 5.0
FINGER_WIDTH = 10.0
GRIPPER_BODY_L = 42.0
GRIPPER_BODY_W = 32.0
GRIPPER_BODY_H = 24.0

CAM_BOARD_L = 60.0
CAM_BOARD_W = 8.0
CAM_BOARD_T = 1.2
CAM_LENS_D = 6.0
CAM_SLOT_CLEAR = 0.3

CABLE_HOLE_D = 7.0

# Legacy aliases used by older modules
LINK_WIDTH = LINK_INNER + 2 * PLATE_T
BASE_HEIGHT = TURNTABLE_Z

BEARING_ALLOC = {
    "J1": ("F695ZZ", 2),
    "J2": ("F695ZZ", 2),
    "J3": ("F695ZZ", 1),
    "J4": ("F685ZZ", 2),
    "J5": ("F685ZZ", 2),
    "J6": ("F685ZZ", 1),
}

SERVO_ALLOC = {
    "J1": "MG996R",
    "J2": "MG996R",
    "J3": "MG90S",
    "J4": "MG90S",
    "J5": "MG90S",
    "J6": "MG90S",
    "gripper": "MG90S",
    "camera_tilt": "MG90S",
}

JOINT_LIMITS = {
    "j1": (-1.57, 1.57),
    "j2": (-1.20, 1.20),
    "j3": (-1.40, 1.40),
    "j4": (-1.57, 1.57),
    "j5": (-1.57, 1.57),
    "j6": (-1.57, 1.57),
    "gripper": (0.0, 0.7),
    "camera_tilt": (-0.8, 0.8),
}
