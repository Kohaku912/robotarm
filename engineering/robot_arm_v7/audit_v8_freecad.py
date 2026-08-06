import csv
import itertools
import json
from pathlib import Path

import FreeCAD as App


doc = App.ActiveDocument
if doc is None or doc.Name != "ROBOT_ARM_V8_MANUFACTURABLE":
    raise RuntimeError("Open ROBOT_ARM_V8_MANUFACTURABLE before audit")

OUT = Path("C:/Users/kohak/programs/robotarm/engineering/robot_arm_v7")
features = [o for o in doc.Objects if o.TypeId == "PartDesign::Feature" and o.Shape.Volume > 0]


def cids(obj):
    return {x for x in getattr(obj, "ConnectionIDs", "").split(";") if x}


def bbox_intersects(a, b):
    aa, bb = a.Shape.BoundBox, b.Shape.BoundBox
    return not (
        aa.XMax < bb.XMin or bb.XMax < aa.XMin
        or aa.YMax < bb.YMin or bb.YMax < aa.YMin
        or aa.ZMax < bb.ZMin or bb.ZMax < aa.ZMin
    )


checks = []


def check(check_id, passed, evidence):
    checks.append({"id": check_id, "status": "PASS" if passed else "FAIL", "evidence": evidence})


missing_metadata = []
invalid_shapes = []
unconnected = []
for obj in features:
    for field in ("PartID", "BodyID", "MaterialSpec", "ManufacturingMethod", "CalculatedMass_g", "ConnectionIDs"):
        if not hasattr(obj, field) or getattr(obj, field) in (None, ""):
            missing_metadata.append(f"{obj.Name}:{field}")
    if not obj.Shape.isValid():
        invalid_shapes.append(obj.Name)
    if not cids(obj):
        unconnected.append(obj.Name)
check("AUD-MATERIAL-METADATA", not missing_metadata, missing_metadata or f"{len(features)} physical features covered")
check("AUD-SHAPE-VALIDITY", not invalid_shapes, invalid_shapes or f"{len(features)} valid B-reps")
check("AUD-UNCONNECTED", not unconnected, unconnected or "No physical feature lacks a ConnectionID")

forbidden = []
allowed_mates = []
for a, b in itertools.combinations(features, 2):
    if not bbox_intersects(a, b):
        continue
    volume = a.Shape.common(b.Shape).Volume
    if volume <= 0.05:
        continue
    shared = sorted(cids(a) & cids(b))
    if shared:
        allowed_mates.append({"a": a.Name, "b": b.Name, "volume_mm3": round(volume, 3), "connection_ids": shared})
    else:
        forbidden.append({"a": a.Name, "b": b.Name, "volume_mm3": round(volume, 3)})
check("AUD-FORBIDDEN-OVERLAP", not forbidden, forbidden or "0 overlaps without a shared physical ConnectionID; tolerance 0.05 mm3")

bearings_695 = [o for o in features if getattr(o, "PartID", "").startswith("BR-") and ("F695" in o.Name or "F695" in o.Label)]
bearings_685 = [o for o in features if getattr(o, "PartID", "").startswith("BR-") and ("F685" in o.Name or "F685" in o.Label)]
check("AUD-INVENTORY-F695", len(bearings_695) == 5, [o.Name for o in bearings_695])
check("AUD-INVENTORY-F685", len(bearings_685) == 5, [o.Name for o in bearings_685])

m3_inserts = [o for o in features if getattr(o, "InsertThread", "") == "M3"]
m4_inserts = [o for o in features if getattr(o, "InsertThread", "") == "M4"]
check("AUD-INSERT-M3-SPEC", bool(m3_inserts) and all(abs(o.InsertOD_mm - 6.0) < 1e-6 and abs(o.InsertLength_mm - 4.0) < 1e-6 for o in m3_inserts), [f"{o.Name}:OD{o.InsertOD_mm}xL{o.InsertLength_mm}" for o in m3_inserts])
check("AUD-INSERT-M4-SPEC", len(m4_inserts) == 4 and all(abs(o.InsertOD_mm - 5.0) < 1e-6 and 3.0 <= o.InsertLength_mm <= 8.0 for o in m4_inserts), [f"{o.Name}:OD{o.InsertOD_mm}xL{o.InsertLength_mm}" for o in m4_inserts])

screws = [o for o in features if getattr(o, "PartID", "").startswith("SCR-")]
fastener_errors = []
access_errors = []
for obj in screws:
    if not all(hasattr(obj, f) for f in ("FastenerSize", "FastenerLength_mm", "ThreadEngagement_mm")):
        fastener_errors.append(f"{obj.Name}:properties")
        continue
    size, length = obj.FastenerSize, float(obj.FastenerLength_mm)
    if size == "M3" and not 5 <= length <= 20:
        fastener_errors.append(f"{obj.Name}:M3x{length}")
    if size == "M4" and not 5 <= length <= 12:
        fastener_errors.append(f"{obj.Name}:M4x{length}")
    if size in ("M3", "M4") and float(obj.ThreadEngagement_mm) < 4.0:
        fastener_errors.append(f"{obj.Name}:engagement={obj.ThreadEngagement_mm}")
    if not all(hasattr(obj, f) for f in ("ToolAccessDirection", "ToolClearance_mm", "ToolAccessStage")):
        access_errors.append(f"{obj.Name}:properties")
    elif float(obj.ToolClearance_mm) < 8.0:
        access_errors.append(f"{obj.Name}:clearance={obj.ToolClearance_mm}")
check("AUD-FASTENER-LENGTH-ENGAGEMENT", not fastener_errors, fastener_errors or f"{len(screws)} screws within inventory/purchase ranges")
check("AUD-TOOL-ACCESS", not access_errors, access_errors or f"{len(screws)} screws define direction, >=8 mm clearance, and assembly stage")

expected_witnesses = {
    "C-BASE-01": ("BASE_PLATE", "BASE_M4X12_1"),
    "C-J1-SERVO": ("J1_SERVO", "J1_SERVO_M3_1"),
    "C-J1-SUN-HORN": ("J1_STOCK_HORN", "J1_HORN_M2_1", "V8_R_J1_SunGear"),
    "C-J1-TRANSMISSION": ("V8_R_J1_SunGear", "V8_R_J1_Planet1", "V8_R_J1_RingGear", "V8_R_J1_CarrierUpper"),
    "C-J1-RINGCASE": ("V8_R_J1_RingGear", "J1_CASE_M3X20_1", "J1_CASE_1"),
    "C-J1-OUTPUT-CLAMP": ("V8_R_J1_Turntable", "J1_OUTPUT_CLAMP_M3", "J1_OUTPUT_CLAMP"),
    "C-J2-SERVO": ("J2_SERVO", "J2_SERVO_M3_1_1", "J2_SERVO_NUT_1_1"),
    "C-J2-ACTIVE": ("J2_SERVO_HORN", "J2_HORN_M3_1", "J2_HORN_1", "UPPER_ARM_R"),
    "C-J2-PASSIVE": ("F695_J2", "J2_PASSIVE_STUB", "J2_COLLAR", "UPPER_ARM_L"),
    "C-J3-SERVO": ("J3_SERVO", "J3_SERVO_M3_1_1", "J3_SERVO_NUT_1_1"),
    "C-J3-ACTIVE": ("J3_SERVO_HORN", "J3_HORN_M3_1", "J3_HORN_1", "FOREARM_L"),
    "C-J3-PASSIVE": ("F695_J3", "J3_PASSIVE_STUB", "J3_COLLAR", "FOREARM_R"),
    "C-J4-SERVO": ("J4_SERVO", "J4_SERVO_M3_1_1", "J4_SERVO_NUT_1_1"),
    "C-J4-ACTIVE": ("J4_SERVO_HORN", "J4_HORN_M3_1", "J4_HORN_1", "WRIST_PITCH_R"),
    "C-J4-PASSIVE": ("F695_J4", "J4_PASSIVE_STUB", "J4_COLLAR", "WRIST_PITCH_L"),
    "C-J5-ACTIVE": ("J5_SERVO", "J5_STOCK_HORN", "J5_HORN_SHAFT_ADAPTER", "J5_HORN_M2_1", "J5_OUTPUT_SHAFT"),
    "C-J5-BRG": ("F685_J5_A", "F685_J5_B", "J5_OUTPUT_SHAFT", "J5_BEARING_HOUSING"),
    "C-J5-RETENTION": ("J5_OUTER_COLLAR", "J5_OUTPUT_SHAFT"),
    "C-J5-TOOL": ("GRIPPER_CRADLE", "J5_TOOL_CLAMP_M3", "J5_TOOL_CLAMP", "J5_OUTPUT_SHAFT"),
}
witness_errors = []
for cid, names in expected_witnesses.items():
    for name in names:
        obj = doc.getObject(name)
        if obj is None or cid not in cids(obj):
            witness_errors.append(f"{cid}:{name}")
check("AUD-PHYSICAL-CONNECTION-GRAPH", not witness_errors, witness_errors or f"{len(expected_witnesses)} connection paths have physical witnesses")

magic_joint_objects = [o.Name for o in doc.Objects if "Joint" in o.TypeId or o.TypeId.startswith("Assembly")]
check("AUD-NO-MAGIC-FIXED-JOINTS", not magic_joint_objects, magic_joint_objects or "No FreeCAD constraint is credited as hardware")

mass_by_body = {}
for obj in features:
    mass_by_body[obj.BodyID] = mass_by_body.get(obj.BodyID, 0.0) + float(obj.CalculatedMass_g)
total_mass = sum(v for k, v in mass_by_body.items() if k != "B-1_FIXTURE")

passed = all(c["status"] == "PASS" for c in checks)
report = {
    "design": "ROBOT_ARM_V8_MANUFACTURABLE",
    "status": "PASS_DIGITAL_CAD_AUDIT" if passed else "FAIL_NOT_COMPLETE",
    "checks": checks,
    "feature_count": len(features),
    "total_arm_mass_g": round(total_mass, 3),
    "mass_by_body_g": {k: round(v, 3) for k, v in mass_by_body.items()},
    "allowed_mating_intersections": allowed_mates,
    "forbidden_intersections": forbidden,
}
(OUT / "V8_cad_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

lines = [
    "# V8 automated CAD audit",
    "",
    f"Overall: **{report['status']}**",
    "",
    f"Physical features: {len(features)}; arm mass excluding fixture inserts: {total_mass:.2f} g.",
    "",
    "| Check ID | Status | Evidence |",
    "|---|---|---|",
]
for item in checks:
    evidence = item["evidence"] if isinstance(item["evidence"], str) else json.dumps(item["evidence"], ensure_ascii=False)
    lines.append(f"| {item['id']} | {item['status']} | {evidence.replace('|', '/')} |")
(OUT / "V8_cad_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

with (OUT / "V8_BOM.csv").open("w", newline="", encoding="utf-8-sig") as stream:
    writer = csv.writer(stream)
    writer.writerow(["PartID", "ObjectName", "Label", "BodyID", "Qty", "Material", "ManufacturingMethod", "Mass_g", "ConnectionIDs"])
    for obj in sorted(features, key=lambda o: (o.PartID, o.Name)):
        writer.writerow([obj.PartID, obj.Name, obj.Label, obj.BodyID, 1, obj.MaterialSpec, obj.ManufacturingMethod, f"{obj.CalculatedMass_g:.3f}", obj.ConnectionIDs])

meta = doc.getObject("ENGINEERING_METADATA")
meta.DesignStatus = "DIGITAL_AUDIT_PASS_PHYSICAL_TESTS_PENDING" if passed else "IN_PROGRESS_NOT_COMPLETE"
doc.recompute()
doc.save()
