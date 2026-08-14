import csv
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET

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

printed = [o for o in features if "FDM" in getattr(o, "ManufacturingMethod", "")]
multi_solid_prints = [{"part": o.Name, "solids": len(o.Shape.Solids)} for o in printed if len(o.Shape.Solids) != 1]
check("AUD-PRINTED-SINGLE-SOLID", not multi_solid_prints, multi_solid_prints or f"{len(printed)} printed BOM parts are each one connected solid")

forbidden = []
allowed_mates = []
for a, b in itertools.combinations(features, 2):
    if not bbox_intersects(a, b):
        continue
    volume = a.Shape.common(b.Shape).Volume
    if volume <= 0.05:
        continue
    shared = sorted(cids(a) & cids(b))
    methods = (getattr(a, "ManufacturingMethod", "").lower(), getattr(b, "ManufacturingMethod", "").lower())
    press_fit = any("press-fit" in method or "thermal press" in method for method in methods)
    transmission_contact = bool(set(shared) & {"C-J1-TRANSMISSION", "C-J2-BELT"})
    hardware_prefixes = ("SCR-", "INS-", "NUT-", "SET-", "COL-")
    explicit_hardware = bool(shared) and (getattr(a, "PartID", "").startswith(hardware_prefixes) or getattr(b, "PartID", "").startswith(hardware_prefixes))
    spline_contact = bool(set(shared) & {"C-J1-SUN-HORN", "C-J4-ACTIVE", "C-J5-ACTIVE"})
    if press_fit or transmission_contact or explicit_hardware or spline_contact:
        reason = "press fit" if press_fit else ("threaded hardware engagement" if explicit_hardware else "declared tooth/spline contact")
        allowed_mates.append({"a": a.Name, "b": b.Name, "volume_mm3": round(volume, 3), "reason": reason, "connection_ids": shared})
    else:
        forbidden.append({"a": a.Name, "b": b.Name, "volume_mm3": round(volume, 3), "shared_ids_not_accepted": shared})
check("AUD-NO-OVERLAP-AS-JOINT", not forbidden, forbidden or "No structural overlap is authorized merely by a shared ConnectionID; tolerance 0.05 mm3")

bearings_695 = [o for o in features if getattr(o, "PartID", "").startswith("BR-") and ("F695" in o.Name or "F695" in o.Label)]
bearings_685 = [o for o in features if getattr(o, "PartID", "").startswith("BR-") and ("F685" in o.Name or "F685" in o.Label)]
check("AUD-INVENTORY-F695", len(bearings_695) == 6, {"installed": [o.Name for o in bearings_695], "owned": 5, "purchase_required": 1})
check("AUD-INVENTORY-F685", len(bearings_685) == 7, {"installed": [o.Name for o in bearings_685], "owned": 5, "purchase_required": 2})

m3_inserts = [o for o in features if getattr(o, "InsertThread", "") == "M3"]
m4_inserts = [o for o in features if getattr(o, "InsertThread", "") == "M4"]
check("AUD-INSERT-M3-SPEC", bool(m3_inserts) and all(abs(o.InsertOD_mm - 6.0) < 1e-6 and abs(o.InsertLength_mm - 4.0) < 1e-6 for o in m3_inserts), [f"{o.Name}:OD{o.InsertOD_mm}xL{o.InsertLength_mm}" for o in m3_inserts])
check("AUD-INSERT-M4-SPEC", len(m4_inserts) >= 4 and all(abs(o.InsertOD_mm - 5.0) < 1e-6 and 3.0 <= o.InsertLength_mm <= 8.0 for o in m4_inserts), [f"{o.Name}:OD{o.InsertOD_mm}xL{o.InsertLength_mm}" for o in m4_inserts])

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
servo_mount_screws = [o for o in screws if "SERVO" in o.Name and "HORN" not in o.Name]
alignment_errors = [f"{o.Name}:{getattr(o, 'HoleAxisAlignmentError_mm', 'missing')}" for o in servo_mount_screws if not hasattr(o, "HoleAxisAlignmentError_mm") or float(o.HoleAxisAlignmentError_mm) > 0.05]
check("AUD-SERVO-STEP-HOLE-AXIS", bool(servo_mount_screws) and not alignment_errors, alignment_errors or f"{len(servo_mount_screws)} servo fastener axes match STEP hole/slot centers within 0.05 mm")

expected_witnesses = {
    "C-BASE-01": ("BASE_PLATE", "BASE_M4X12_1"),
    "C-J1-SERVO": ("J1_SERVO", "J1_SERVO_M2_1", "J1_SERVO_1", "BASE_PLATE"),
    "C-J1-SUN-HORN": ("J1_STOCK_HORN", "J1_HORN_M2_1", "V8_R_J1_SunGear"),
    "C-J1-TRANSMISSION": ("V8_R_J1_SunGear", "V8_R_J1_Planet1", "V8_R_J1_RingGear", "V8_R_J1_CarrierUpper"),
    "C-J1-RINGCASE": ("V8_R_J1_RingGear", "J1_CASE_M3X20_1", "J1_CASE_1"),
    "C-J1-OUTPUT-CLAMP": ("V8_R_J1_Turntable", "J1_OUTPUT_CLAMP_M3", "J1_OUTPUT_CLAMP"),
    "C-J2-SERVO": ("J2_SERVO", "J2_SERVO_M4_1_1", "J2_SERVO_1_1", "V8_R_J1_Turntable"),
    "C-J2-HORN-COUPLER": ("J2_SERVO_HORN", "J2_HORN_SHAFT_COUPLER", "J2_INPUT_SHAFT"),
    "C-J2-INPUT-SUPPORT": ("J2_INPUT_BEARING_BRIDGE", "F685_J2_INPUT_A", "F685_J2_INPUT_B", "J2_INPUT_SHAFT", "J2_BRIDGE_M3_1"),
    "C-J2-BELT": ("J2_DRIVER_16T", "J2_BELT_135_3GT_90", "UPPER_ARM_R"),
    "C-J2-OUTPUT-BEARINGS": ("F695_J2_L", "F695_J2_R", "J2_OUTPUT_SHAFT", "UPPER_ARM_L", "UPPER_ARM_R"),
    "C-J2-RETENTION": ("J2_OUTPUT_SHAFT", "J2_SHAFT_CLAMP_M3_L", "J2_SHAFT_CLAMP_L"),
    "C-UA-CROSS": ("UPPER_ARM_L", "UPPER_ARM_R", "UPPER_ARM_SPACER_1", "UA_SPACER_M3_1_L", "UA_SPACER_1_L"),
    "C-J3-SERVO": ("J3_SERVO", "J3_SERVO_M4_1_1", "J3_SERVO_1_1", "UPPER_ARM_R"),
    "C-J3-ACTIVE": ("J3_SERVO_HORN", "J3_HORN_M3_1", "J3_HORN_1", "FOREARM_L"),
    "C-J3-PASSIVE": ("F695_J3", "J3_PASSIVE_STUB", "J3_COLLAR", "FOREARM_R"),
    "C-J4-SERVO": ("J4_SERVO", "J4_SERVO_M2_1_1", "J4_SERVO_1_1", "FOREARM_L"),
    "C-J4-ACTIVE": ("J4_SERVO_HORN", "J4_HORN_M3_1", "J4_HORN_1", "WRIST_PITCH_R"),
    "C-J4-PASSIVE": ("F695_J4", "J4_PASSIVE_STUB", "J4_COLLAR", "WRIST_PITCH_L"),
    "C-J5-ACTIVE": ("J5_SERVO", "J5_STOCK_HORN", "J5_HORN_SHAFT_ADAPTER", "J5_HORN_M2_1", "J5_OUTPUT_SHAFT"),
    "C-J5-SERVO": ("J5_SERVO", "J5_SERVO_M2_1", "J5_SERVO_1", "WRIST_PITCH_R"),
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

integral_hosts = {
    "J1": ("BASE_PLATE", "J1IntegratedMount"),
    "J2": ("V8_R_J1_Turntable", "J2IntegratedMount"),
    "J3": ("UPPER_ARM_R", "J3IntegratedMount"),
    "J4": ("FOREARM_L", "J4IntegratedMount"),
    "J5": ("WRIST_PITCH_R", "J5IntegratedMount"),
}
integral_errors = []
for joint, (host_name, prop_name) in integral_hosts.items():
    host = doc.getObject(host_name)
    legacy = doc.getObject(f"{joint}_SERVO_MOUNT")
    if host is None or legacy is not None or not hasattr(host, prop_name) or len(host.Shape.Solids) != 1:
        integral_errors.append({"joint": joint, "host": host_name, "legacy_mount": bool(legacy), "solids": len(host.Shape.Solids) if host else None})
check("AUD-INTEGRAL-SERVO-MOUNTS", not integral_errors, integral_errors or "J1-J5 cradle features are fused into one-solid structural hosts; no separate mount BOM items")

servo_mount_intersections = []
for joint, (host_name, _) in integral_hosts.items():
    servo = doc.getObject(f"{joint}_SERVO")
    host = doc.getObject(host_name)
    if servo and host:
        common = float(servo.Shape.common(host.Shape).Volume)
        if common > 0.05:
            servo_mount_intersections.append({"joint": joint, "common_volume_mm3": round(common, 4)})
check("AUD-SERVO-HOST-NO-VOLUME-OVERLAP", not servo_mount_intersections, servo_mount_intersections or "All purchased servo cases have zero common volume with their printed hosts; seating is by ear faces")

horn_names = ("J1_STOCK_HORN", "J2_SERVO_HORN", "J3_SERVO_HORN", "J4_SERVO_HORN", "J5_STOCK_HORN")
missing_horn_sources = []
for name in horn_names:
    horn = doc.getObject(name)
    source = getattr(horn, "GeometrySource", "") if horn else ""
    if not source or source in ("MISSING_FROM_USER_DATA", "MEASUREMENT_REQUIRED"):
        missing_horn_sources.append(name)
check(
    "AUD-EXACT-SERVO-HORN-GEOMETRY",
    not missing_horn_sources,
    missing_horn_sources or "All five servo horns trace to supplied STEP geometry",
)

servo_names = ("J1_SERVO", "J2_SERVO", "J3_SERVO", "J4_SERVO", "J5_SERVO")
servo_source_errors = []
servo_modified_errors = []
for name in servo_names:
    servo = doc.getObject(name)
    source = getattr(servo, "GeometrySource", "") if servo else ""
    expected_volume = float(getattr(servo, "SourceShapeVolume_mm3", 0.0)) if servo else 0.0
    if not source or not source.lower().endswith((".step", ".stp")):
        servo_source_errors.append(f"{name}:{source or 'missing'}")
    if servo is None or expected_volume <= 0.0 or abs(float(servo.Shape.Volume) - expected_volume) > 0.01:
        actual = float(servo.Shape.Volume) if servo else 0.0
        servo_modified_errors.append(f"{name}:actual={actual:.3f},source={expected_volume:.3f}")
check("AUD-EXACT-SERVO-BODY-GEOMETRY", not servo_source_errors, servo_source_errors or "All five servo bodies trace to supplied STEP files")
check("AUD-PURCHASED-SERVO-UNMODIFIED", not servo_modified_errors, servo_modified_errors or "Placed servo B-rep volumes equal source volumes within 0.01 mm3")

mass_by_body = {}
weighted_com_by_body = {}
for obj in features:
    mass = float(obj.CalculatedMass_g)
    mass_by_body[obj.BodyID] = mass_by_body.get(obj.BodyID, 0.0) + mass
    if hasattr(obj.Shape, "CenterOfMass"):
        center = obj.Shape.CenterOfMass
    else:
        solid_volume = sum(solid.Volume for solid in obj.Shape.Solids)
        center = App.Vector()
        for solid in obj.Shape.Solids:
            center = center.add(solid.CenterOfMass.multiply(solid.Volume / solid_volume))
    current = weighted_com_by_body.get(obj.BodyID, [0.0, 0.0, 0.0])
    weighted_com_by_body[obj.BodyID] = [current[0] + mass * center.x, current[1] + mass * center.y, current[2] + mass * center.z]
total_mass = sum(v for k, v in mass_by_body.items() if k != "B-1_FIXTURE")
com_by_body = {
    body: [round(component / mass_by_body[body], 6) for component in weighted]
    for body, weighted in weighted_com_by_body.items()
}

# Conservative point-mass pitch-axis check for the required horizontal
# payload, maximum acceleration and emergency-stop deceleration cases.
pitch_cases = []
payload_kg = float(doc.getObject("ENGINEERING_METADATA").Payload_g) / 1000.0
tip_x_m = float(doc.getObject("ENGINEERING_METADATA").Reach_mm) / 1000.0
alpha_max = float(doc.getObject("ENGINEERING_METADATA").MaxAccel_deg_s2) * 3.141592653589793 / 180.0
alpha_estop = float(doc.getObject("ENGINEERING_METADATA").EStopDecel_deg_s2) * 3.141592653589793 / 180.0
for joint, axis_x_m, bodies, stall in (
    ("J2", 0.0, ("B2_UPPER_ARM", "B3_FOREARM", "B4_WRIST_PITCH", "B5_TOOL"), 0.922 * 2.0 * 0.90),
    ("J3", 0.115, ("B3_FOREARM", "B4_WRIST_PITCH", "B5_TOOL"), 0.922),
    ("J4", 0.230, ("B4_WRIST_PITCH", "B5_TOOL"), 0.177),
):
    gravity = sum((mass_by_body[b] / 1000.0) * 9.80665 * (com_by_body[b][0] / 1000.0 - axis_x_m) for b in bodies)
    gravity += payload_kg * 9.80665 * (tip_x_m - axis_x_m)
    inertia = sum((mass_by_body[b] / 1000.0) * (com_by_body[b][0] / 1000.0 - axis_x_m) ** 2 for b in bodies)
    inertia += payload_kg * (tip_x_m - axis_x_m) ** 2
    demands = {
        "static": gravity,
        "max_accel_120_deg_s2": gravity + inertia * alpha_max,
        "emergency_stop_600_deg_s2": gravity + inertia * alpha_estop,
    }
    pitch_cases.append({
        "joint": joint,
        "stall_Nm": round(stall, 6),
        "load_cases": {
            name: {"demand_Nm": round(demand, 6), "sf": round(stall / demand, 4)}
            for name, demand in demands.items()
        },
    })
check(
    "AUD-PITCH-LOAD-CASES-SF",
    all(case_data["sf"] >= 1.5 for joint_data in pitch_cases for case_data in joint_data["load_cases"].values()),
    pitch_cases,
)
meta = doc.getObject("ENGINEERING_METADATA")
belt = doc.getObject("J2_BELT_135_3GT_90")
belt_evidence = {
    "part": getattr(belt, "PartID", None),
    "ratio": float(getattr(meta, "J2Ratio", 0.0)),
    "efficiency": float(getattr(meta, "J2BeltEfficiency", 0.0)),
    "pitch_mm": float(getattr(belt, "Pitch_mm", 0.0)) if belt else 0.0,
    "width_mm": float(getattr(belt, "Width_mm", 0.0)) if belt else 0.0,
    "length_mm": float(getattr(belt, "PitchLength_mm", 0.0)) if belt else 0.0,
    "wrap_deg": float(getattr(belt, "SmallPulleyWrap_deg", 0.0)) if belt else 0.0,
    "engaged_teeth": float(getattr(belt, "EngagedTeeth", 0.0)) if belt else 0.0,
}
check("AUD-J2-PHYSICAL-2TO1-BELT", belt is not None and belt_evidence["ratio"] == 2.0 and belt_evidence["pitch_mm"] == 3.0 and belt_evidence["width_mm"] == 9.0 and belt_evidence["length_mm"] == 135.0 and belt_evidence["engaged_teeth"] >= 6.0, belt_evidence)
xml_path = OUT / "robot_arm_v8.xml"
mujoco_match = False
mujoco_evidence = {"file": str(xml_path), "error": "missing"}
if xml_path.exists():
    try:
        root = ET.parse(xml_path).getroot()
        motor = root.find("./actuator/motor[@name='J2_MG996R_16T_32T_3GT']")
        ratio = root.find("./custom/numeric[@name='J2_servo_to_joint_ratio']")
        efficiency = root.find("./custom/numeric[@name='J2_belt_efficiency']")
        transmission = root.find("./custom/text[@name='J2_transmission_id']")
        mujoco_match = motor is not None and abs(float(motor.get("gear")) - 1.6596) < 1e-6 and ratio is not None and ratio.get("data") == "2.0" and efficiency is not None and efficiency.get("data") == "0.90" and transmission is not None and transmission.get("data") == "P-J2-BELT"
        mujoco_evidence = {"motor": motor.get("name") if motor is not None else None, "gear_Nm": float(motor.get("gear")) if motor is not None else None, "ratio": ratio.get("data") if ratio is not None else None, "efficiency": efficiency.get("data") if efficiency is not None else None, "transmission_id": transmission.get("data") if transmission is not None else None}
    except Exception as exc:
        mujoco_evidence = {"file": str(xml_path), "error": str(exc)}
check("AUD-MUJOCO-TRANSMISSION-MATCH", mujoco_match, mujoco_evidence)
check("AUD-BELT-CAPACITY-PHYSICAL-COUPON", False, "3GT printed-tooth coupon and MISUMI capacity confirmation are required before manufacture approval")
check("AUD-PHYSICAL-VALIDATION", False, "Pending insert pull-out, bearing press-fit, 30 s hold, and 600 deg/s2 emergency-stop tests")
check("AUD-MOTION-SWEEP-CURRENT", False, "MuJoCo sweep must be rerun after exact-servo geometry and J5 axis relocation; local mujoco module unavailable")

passed = all(c["status"] == "PASS" for c in checks)
report = {
    "design": "ROBOT_ARM_V8_MANUFACTURABLE",
    "status": "PASS_DIGITAL_CAD_AUDIT" if passed else "FAIL_NOT_COMPLETE",
    "checks": checks,
    "feature_count": len(features),
    "total_arm_mass_g": round(total_mass, 3),
    "mass_by_body_g": {k: round(v, 3) for k, v in mass_by_body.items()},
    "center_of_mass_by_body_mm": com_by_body,
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
