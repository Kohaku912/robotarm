# V8 automated CAD audit

Overall: **PASS_DIGITAL_CAD_AUDIT**

Physical features: 137; arm mass excluding fixture inserts: 455.47 g.

| Check ID | Status | Evidence |
|---|---|---|
| AUD-MATERIAL-METADATA | PASS | 137 physical features covered |
| AUD-SHAPE-VALIDITY | PASS | 137 valid B-reps |
| AUD-UNCONNECTED | PASS | No physical feature lacks a ConnectionID |
| AUD-FORBIDDEN-OVERLAP | PASS | 0 overlaps without a shared physical ConnectionID; tolerance 0.05 mm3 |
| AUD-INVENTORY-F695 | PASS | ["F695_J1_1", "F695_J1_2", "F695_J2", "F695_J3", "F695_J4"] |
| AUD-INVENTORY-F685 | PASS | ["J1_PLANET_BRG_1", "J1_PLANET_BRG_2", "J1_PLANET_BRG_3", "F685_J5_A", "F685_J5_B"] |
| AUD-INSERT-M3-SPEC | PASS | ["J1_SERVO_1:OD6.0xL4.0", "J1_SERVO_2:OD6.0xL4.0", "J1_CASE_1:OD6.0xL4.0", "J1_CASE_2:OD6.0xL4.0", "J1_CASE_3:OD6.0xL4.0", "J1_CASE_4:OD6.0xL4.0", "J1_CASE_5:OD6.0xL4.0", "J1_CASE_6:OD6.0xL4.0", "J1_OUTPUT_CLAMP:OD6.0xL4.0", "J5_HOUSING_INS_1_1:OD6.0xL4.0", "J5_HOUSING_INS_1_2:OD6.0xL4.0", "J5_HOUSING_INS_2_1:OD6.0xL4.0", "J5_HOUSING_INS_2_2:OD6.0xL4.0", "J5_TOOL_CLAMP:OD6.0xL4.0", "J2_HORN_1:OD6.0xL4.0", "J2_HORN_2:OD6.0xL4.0", "J3_HORN_1:OD6.0xL4.0", "J3_HORN_2:OD6.0xL4.0", "J4_HORN_1:OD6.0xL4.0", "J4_HORN_2:OD6.0xL4.0"] |
| AUD-INSERT-M4-SPEC | PASS | ["BASE_M4_1:OD5.0xL6.0", "BASE_M4_2:OD5.0xL6.0", "BASE_M4_3:OD5.0xL6.0", "BASE_M4_4:OD5.0xL6.0"] |
| AUD-FASTENER-LENGTH-ENGAGEMENT | PASS | 36 screws within inventory/purchase ranges |
| AUD-TOOL-ACCESS | PASS | 36 screws define direction, >=8 mm clearance, and assembly stage |
| AUD-PHYSICAL-CONNECTION-GRAPH | PASS | 19 connection paths have physical witnesses |
| AUD-NO-MAGIC-FIXED-JOINTS | PASS | No FreeCAD constraint is credited as hardware |
