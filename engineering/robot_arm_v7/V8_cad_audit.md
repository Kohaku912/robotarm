# V8 automated CAD audit

Overall: **FAIL_NOT_COMPLETE**

Physical features: 157; arm mass excluding fixture inserts: 558.57 g.

| Check ID | Status | Evidence |
|---|---|---|
| AUD-MATERIAL-METADATA | PASS | 157 physical features covered |
| AUD-SHAPE-VALIDITY | PASS | 157 valid B-reps |
| AUD-UNCONNECTED | PASS | No physical feature lacks a ConnectionID |
| AUD-PRINTED-SINGLE-SOLID | PASS | 25 printed BOM parts are each one connected solid |
| AUD-NO-OVERLAP-AS-JOINT | PASS | No structural overlap is authorized merely by a shared ConnectionID; tolerance 0.05 mm3 |
| AUD-INVENTORY-F695 | PASS | {"installed": ["F695_J1_1", "F695_J1_2", "F695_J2_L", "F695_J2_R", "F695_J3", "F695_J4"], "owned": 5, "purchase_required": 1} |
| AUD-INVENTORY-F685 | PASS | {"installed": ["J1_PLANET_BRG_1", "J1_PLANET_BRG_2", "J1_PLANET_BRG_3", "F685_J5_A", "F685_J5_B", "F685_J2_INPUT_A", "F685_J2_INPUT_B"], "owned": 5, "purchase_required": 2} |
| AUD-INSERT-M3-SPEC | PASS | ["J1_CASE_1:OD6.0xL4.0", "J1_CASE_2:OD6.0xL4.0", "J1_CASE_3:OD6.0xL4.0", "J1_CASE_4:OD6.0xL4.0", "J1_CASE_5:OD6.0xL4.0", "J1_CASE_6:OD6.0xL4.0", "J1_OUTPUT_CLAMP:OD6.0xL4.0", "J2_SHAFT_CLAMP_L:OD6.0xL4.0", "J2_SHAFT_CLAMP_R:OD6.0xL4.0", "UA_SPACER_1_L:OD6.0xL4.0", "UA_SPACER_1_R:OD6.0xL4.0", "UA_SPACER_2_L:OD6.0xL4.0", "UA_SPACER_2_R:OD6.0xL4.0", "J5_HOUSING_INS_1_1:OD6.0xL4.0", "J5_HOUSING_INS_1_2:OD6.0xL4.0", "J5_HOUSING_INS_2_1:OD6.0xL4.0", "J5_HOUSING_INS_2_2:OD6.0xL4.0", "J5_TOOL_CLAMP:OD6.0xL4.0", "J2_BRIDGE_INS_1:OD6.0xL4.0", "J2_BRIDGE_INS_2:OD6.0xL4.0", "J2_BRIDGE_INS_3:OD6.0xL4.0", "J2_BRIDGE_INS_4:OD6.0xL4.0", "J4_HORN_1:OD6.0xL4.0", "J4_HORN_2:OD6.0xL4.0"] |
| AUD-INSERT-M4-SPEC | PASS | ["BASE_M4_1:OD5.0xL6.0", "BASE_M4_2:OD5.0xL6.0", "BASE_M4_3:OD5.0xL6.0", "BASE_M4_4:OD5.0xL6.0", "J2_SERVO_1_1:OD5.0xL4.0", "J2_SERVO_1_2:OD5.0xL4.0", "J2_SERVO_2_1:OD5.0xL4.0", "J2_SERVO_2_2:OD5.0xL4.0", "J3_SERVO_1_1:OD5.0xL4.0", "J3_SERVO_1_2:OD5.0xL4.0", "J3_SERVO_2_1:OD5.0xL4.0", "J3_SERVO_2_2:OD5.0xL4.0"] |
| AUD-FASTENER-LENGTH-ENGAGEMENT | PASS | 49 screws within inventory/purchase ranges |
| AUD-TOOL-ACCESS | PASS | 49 screws define direction, >=8 mm clearance, and assembly stage |
| AUD-SERVO-STEP-HOLE-AXIS | PASS | 14 servo fastener axes match STEP hole/slot centers within 0.05 mm |
| AUD-PHYSICAL-CONNECTION-GRAPH | FAIL | ["C-J2-HORN-COUPLER:J2_SERVO_HORN", "C-J2-HORN-COUPLER:J2_HORN_SHAFT_COUPLER", "C-J3-ACTIVE:J3_SERVO_HORN", "C-J3-ACTIVE:J3_HORN_M3_1", "C-J3-ACTIVE:J3_HORN_1"] |
| AUD-NO-MAGIC-FIXED-JOINTS | PASS | No FreeCAD constraint is credited as hardware |
| AUD-INTEGRAL-SERVO-MOUNTS | PASS | J1-J5 cradle features are fused into one-solid structural hosts; no separate mount BOM items |
| AUD-SERVO-HOST-NO-VOLUME-OVERLAP | PASS | All purchased servo cases have zero common volume with their printed hosts; seating is by ear faces |
| AUD-EXACT-SERVO-HORN-GEOMETRY | FAIL | ["J2_SERVO_HORN", "J3_SERVO_HORN"] |
| AUD-EXACT-SERVO-BODY-GEOMETRY | PASS | All five servo bodies trace to supplied STEP files |
| AUD-PURCHASED-SERVO-UNMODIFIED | PASS | Placed servo B-rep volumes equal source volumes within 0.01 mm3 |
| AUD-PITCH-LOAD-CASES-SF | PASS | [{"joint": "J2", "stall_Nm": 1.6596, "load_cases": {"static": {"demand_Nm": 0.517907, "sf": 3.2044}, "max_accel_120_deg_s2": {"demand_Nm": 0.544641, "sf": 3.0471}, "emergency_stop_600_deg_s2": {"demand_Nm": 0.65158, "sf": 2.547}}}, {"joint": "J3", "stall_Nm": 0.922, "load_cases": {"static": {"demand_Nm": 0.247761, "sf": 3.7213}, "max_accel_120_deg_s2": {"demand_Nm": 0.256204, "sf": 3.5987}, "emergency_stop_600_deg_s2": {"demand_Nm": 0.289976, "sf": 3.1796}}}, {"joint": "J4", "stall_Nm": 0.177, "load_cases": {"static": {"demand_Nm": 0.068699, "sf": 2.5765}, "max_accel_120_deg_s2": {"demand_Nm": 0.069538, "sf": 2.5454}, "emergency_stop_600_deg_s2": {"demand_Nm": 0.072896, "sf": 2.4281}}}] |
| AUD-J2-PHYSICAL-2TO1-BELT | PASS | {"part": "BELT-J2-135-3GT-90", "ratio": 2.0, "efficiency": 0.9, "pitch_mm": 3.0, "width_mm": 9.0, "length_mm": 135.0, "wrap_deg": 151.0323, "engaged_teeth": 6.7125} |
| AUD-MUJOCO-TRANSMISSION-MATCH | PASS | {"motor": "J2_MG996R_16T_32T_3GT", "gear_Nm": 1.6596, "ratio": "2.0", "efficiency": "0.90", "transmission_id": "P-J2-BELT"} |
| AUD-BELT-CAPACITY-PHYSICAL-COUPON | FAIL | 3GT printed-tooth coupon and MISUMI capacity confirmation are required before manufacture approval |
| AUD-PHYSICAL-VALIDATION | FAIL | Pending insert pull-out, bearing press-fit, 30 s hold, and 600 deg/s2 emergency-stop tests |
| AUD-MOTION-SWEEP-CURRENT | FAIL | MuJoCo sweep must be rerun after exact-servo geometry and J5 axis relocation; local mujoco module unavailable |
