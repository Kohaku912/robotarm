import json
import math
from pathlib import Path

import FreeCAD as App
import Part


OUT = "C:/Users/kohak/programs/robotarm/cad/RobotArmFinalV5/CompletedPreviewV5_2CradleAlignment/ROBOT_ARM_V8_MANUFACTURABLE.FCStd"
DENSITY = {"PA12_CF": 1.06, "PA12": 1.01, "STEEL": 7.85, "BRASS": 8.50}
AXIS_Z = 79.0
J5_X = 273.0
J2_INPUT_X = 30.545
J2_BELT_PITCH = 3.0
J2_BELT_WIDTH = 9.0
J2_BELT_LENGTH = 135.0
J2_DRIVER_TEETH = 16
J2_DRIVEN_TEETH = 32
J2_RATIO = 2.0
J2_BELT_EFFICIENCY = 0.90
MG90_HORN_STEP = "C:/Users/kohak/programs/robotarm/vendor/servo_cad/MG90S_HORN.step"
MG90_SERVO_STEP = "C:/Users/kohak/programs/robotarm/vendor/servo_cad/MG90S_SERVO.step"
MG996_SERVO_STEP = "C:/Users/kohak/programs/robotarm/vendor/servo_cad/MG996R_SERVO.step"
MG996_HORN_MEASUREMENTS = Path("C:/Users/kohak/programs/robotarm/engineering/robot_arm_v7/mg996_horn_measurements.json")


def load_verified_mg996_horn_measurements():
    if not MG996_HORN_MEASUREMENTS.exists():
        return None
    data = json.loads(MG996_HORN_MEASUREMENTS.read_text(encoding="utf-8"))
    required = ("arm_length_mm", "arm_width_mm", "plate_thickness_mm", "boss_od_mm", "boss_height_mm", "center_bore_mm", "holes")
    if data.get("status") != "VERIFIED" or any(data.get(field) in (None, "", []) for field in required):
        return None
    if len(data.get("measured_horns", [])) != 2 or float(data.get("max_pair_difference_mm", 999.0)) > 0.1:
        return None
    return data


MG996_HORN_DATA = load_verified_mg996_horn_measurements()


# User-supplied STEP geometry.  The MG90S servo STEP contains body, shaft,
# horn and center screw as four solids; the separate double-arm horn is used
# for the torque interfaces in this arm.
MG90_HORN_SOURCE = Part.Shape()
MG90_HORN_SOURCE.read(MG90_HORN_STEP)
MG90_SERVO_SOURCE = Part.Shape()
MG90_SERVO_SOURCE.read(MG90_SERVO_STEP)
MG90_BODY_SOURCE = Part.makeCompound([MG90_SERVO_SOURCE.Solids[0].copy(), MG90_SERVO_SOURCE.Solids[1].copy()])
MG90_CENTER_SCREW_SOURCE = MG90_SERVO_SOURCE.Solids[3].copy()
MG996_SERVO_SOURCE = Part.Shape()
MG996_SERVO_SOURCE.read(MG996_SERVO_STEP)


def placed_shape(source, base, matrix=None):
    shape = source.copy()
    rotation = App.Rotation(matrix) if matrix is not None else App.Rotation()
    shape.Placement = App.Placement(base, rotation)
    return shape


MG90_TO_J4 = App.Matrix()
MG90_TO_J4.A11, MG90_TO_J4.A12, MG90_TO_J4.A13 = 0, 1, 0
MG90_TO_J4.A21, MG90_TO_J4.A22, MG90_TO_J4.A23 = 0, 0, 1
MG90_TO_J4.A31, MG90_TO_J4.A32, MG90_TO_J4.A33 = 1, 0, 0

MG90_TO_J5 = App.Matrix()
MG90_TO_J5.A11, MG90_TO_J5.A12, MG90_TO_J5.A13 = 0, 0, 1
MG90_TO_J5.A21, MG90_TO_J5.A22, MG90_TO_J5.A23 = 0, -1, 0
MG90_TO_J5.A31, MG90_TO_J5.A32, MG90_TO_J5.A33 = 1, 0, 0

MG996_TO_J2 = App.Matrix()
MG996_TO_J2.A11, MG996_TO_J2.A12, MG996_TO_J2.A13 = 1, 0, 0
MG996_TO_J2.A21, MG996_TO_J2.A22, MG996_TO_J2.A23 = 0, 1, 0
MG996_TO_J2.A31, MG996_TO_J2.A32, MG996_TO_J2.A33 = 0, 0, 1

MG996_TO_J3 = App.Matrix()
MG996_TO_J3.A11, MG996_TO_J3.A12, MG996_TO_J3.A13 = -1, 0, 0
MG996_TO_J3.A21, MG996_TO_J3.A22, MG996_TO_J3.A23 = 0, -1, 0
MG996_TO_J3.A31, MG996_TO_J3.A32, MG996_TO_J3.A33 = 0, 0, 1


old = None
for candidate in App.listDocuments().values():
    if candidate.Name != "ROBOT_ARM_V8_MANUFACTURABLE" and candidate.getObject("R_J1_RingGear"):
        old = candidate
        break
if old is None:
    raise RuntimeError("V7 source document with R_J1_RingGear must remain open")
try:
    App.closeDocument("ROBOT_ARM_V8_MANUFACTURABLE")
except NameError:
    pass
doc = App.newDocument("ROBOT_ARM_V8_MANUFACTURABLE", "Robot Arm V8 Manufacturable")


def add_prop(obj, prop_type, name, value, group="Engineering"):
    if not hasattr(obj, name):
        obj.addProperty(prop_type, name, group)
    setattr(obj, name, value)


def part(name, label, shape, part_id, body_id, material, method, connection_ids="", color=(0.72, 0.72, 0.76), mass_override=None):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    add_prop(obj, "App::PropertyString", "PartID", part_id)
    add_prop(obj, "App::PropertyString", "BodyID", body_id)
    add_prop(obj, "App::PropertyString", "MaterialSpec", material)
    add_prop(obj, "App::PropertyString", "ManufacturingMethod", method)
    add_prop(obj, "App::PropertyString", "ConnectionIDs", connection_ids)
    density = 0.0
    if material.startswith("Fiberon"):
        density = DENSITY["PA12_CF"]
    elif material == "PA12":
        density = DENSITY["PA12"]
    elif "steel" in material.lower():
        density = DENSITY["STEEL"]
    elif "brass" in material.lower():
        density = DENSITY["BRASS"]
    mass = float(mass_override) if mass_override is not None else shape.Volume * density / 1000.0
    add_prop(obj, "App::PropertyFloat", "CalculatedMass_g", mass)
    return obj


def screw_z(name, x, y, z0, length, body, cid, size="M3"):
    dia, hd, hh = (3.0, 6.0, 2.0) if size == "M3" else (4.0, 7.0, 2.0)
    sh = Part.makeCylinder(dia / 2, length, App.Vector(x, y, z0))
    head = Part.makeCylinder(hd / 2, hh, App.Vector(x, y, z0 + length))
    obj = part(name, f"{size}x{length:g} low-head screw", sh.fuse(head), f"SCR-{name}", body, "Steel A2-70", "Purchased", cid, (0.55, 0.57, 0.60))
    add_prop(obj, "App::PropertyString", "FastenerSize", size)
    add_prop(obj, "App::PropertyFloat", "FastenerLength_mm", float(length))
    add_prop(obj, "App::PropertyFloat", "ThreadEngagement_mm", 4.0)
    add_prop(obj, "App::PropertyString", "ToolAccessDirection", "+Z")
    add_prop(obj, "App::PropertyFloat", "ToolClearance_mm", 10.0)
    add_prop(obj, "App::PropertyString", "ToolAccessStage", "Install before the next enclosing subassembly")
    return obj


def screw_y(name, x, y0, z, length, direction, body, cid, size="M3"):
    dia, hd = {"M2": (2.0, 4.0), "M3": (3.0, 6.0), "M4": (4.0, 7.0)}[size]
    sh = Part.makeCylinder(dia / 2, length, App.Vector(x, y0, z), App.Vector(0, direction, 0))
    head_start = y0 - 2 if direction > 0 else y0 + 2
    head = Part.makeCylinder(hd / 2, 2, App.Vector(x, head_start, z), App.Vector(0, direction, 0))
    obj = part(name, f"{size}x{length:g} low-head screw", sh.fuse(head), f"SCR-{name}", body, "Steel A2-70", "Purchased", cid, (0.55, 0.57, 0.60))
    add_prop(obj, "App::PropertyString", "FastenerSize", size)
    add_prop(obj, "App::PropertyFloat", "FastenerLength_mm", float(length))
    add_prop(obj, "App::PropertyFloat", "ThreadEngagement_mm", 4.0 if size in ("M3", "M4") else 3.0)
    add_prop(obj, "App::PropertyString", "ToolAccessDirection", "-Y" if direction > 0 else "+Y")
    add_prop(obj, "App::PropertyFloat", "ToolClearance_mm", 10.0)
    add_prop(obj, "App::PropertyString", "ToolAccessStage", "Side access before adjacent moving link is installed")
    return obj


def insert_z(name, x, y, z0, length, body, cid, size="M3"):
    od = 6.0 if size == "M3" else 5.0
    bore = 3.0 if size == "M3" else 4.0
    shape = Part.makeCylinder(od / 2, length, App.Vector(x, y, z0)).cut(Part.makeCylinder(bore / 2, length, App.Vector(x, y, z0)))
    obj = part(name, f"{size} heat-set insert OD{od:g} L{length:g}", shape, f"INS-{name}", body, "Brass heat-set insert", "Thermal press-fit; coupon-calibrated hole", cid, (0.84, 0.58, 0.18))
    add_prop(obj, "App::PropertyString", "InsertThread", size)
    add_prop(obj, "App::PropertyFloat", "InsertOD_mm", od)
    add_prop(obj, "App::PropertyFloat", "InsertLength_mm", float(length))
    return obj


def insert_y(name, x, y0, z, length, body, cid, size="M3"):
    od, bore = {"M2": (3.5, 2.0), "M3": (6.0, 3.0), "M4": (5.0, 4.0)}[size]
    shape = Part.makeCylinder(od / 2, length, App.Vector(x, y0, z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(bore / 2, length, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    obj = part(name, f"{size} heat-set insert OD{od:g} L{length:g}", shape, f"INS-{name}", body, "Brass heat-set insert", "Thermal press-fit; coupon-calibrated hole", cid, (0.84, 0.58, 0.18))
    add_prop(obj, "App::PropertyString", "InsertThread", size)
    add_prop(obj, "App::PropertyFloat", "InsertOD_mm", od)
    add_prop(obj, "App::PropertyFloat", "InsertLength_mm", float(length))
    return obj


def insert_x(name, x0, y, z, length, body, cid, size="M3"):
    od, bore = {"M2": (3.5, 2.0), "M3": (6.0, 3.0), "M4": (5.0, 4.0)}[size]
    shape = Part.makeCylinder(od / 2, length, App.Vector(x0, y, z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(bore / 2, length, App.Vector(x0, y, z), App.Vector(1, 0, 0)))
    obj = part(name, f"{size} heat-set insert OD{od:g} L{length:g}", shape, f"INS-{name}", body, "Brass heat-set insert", "Thermal press-fit; coupon-calibrated hole", cid, (0.84, 0.58, 0.18))
    add_prop(obj, "App::PropertyString", "InsertThread", size)
    add_prop(obj, "App::PropertyFloat", "InsertOD_mm", od)
    add_prop(obj, "App::PropertyFloat", "InsertLength_mm", float(length))
    return obj


def screw_x(name, x0, y, z, length, body, cid, size="M3"):
    dia, hd = {"M2": (2.0, 4.0), "M3": (3.0, 6.0), "M4": (4.0, 7.0)}[size]
    sh = Part.makeCylinder(dia / 2, length, App.Vector(x0, y, z), App.Vector(1, 0, 0))
    head = Part.makeCylinder(hd / 2, 2, App.Vector(x0 - 2, y, z), App.Vector(1, 0, 0))
    obj = part(name, f"{size}x{length:g} low-head screw", sh.fuse(head), f"SCR-{name}", body, "Steel A2-70", "Purchased", cid, (0.55, 0.57, 0.60))
    add_prop(obj, "App::PropertyString", "FastenerSize", size)
    add_prop(obj, "App::PropertyFloat", "FastenerLength_mm", float(length))
    add_prop(obj, "App::PropertyFloat", "ThreadEngagement_mm", 4.0)
    add_prop(obj, "App::PropertyString", "ToolAccessDirection", "-X")
    add_prop(obj, "App::PropertyFloat", "ToolClearance_mm", 10.0)
    add_prop(obj, "App::PropertyString", "ToolAccessStage", "Before upper-arm installation")
    return obj


def bearing_y(name, x, y0, z, body, cid, model="F695ZZ"):
    if model == "F695ZZ":
        od, width, flange, mass = 13.0, 4.0, 15.0, 2.84
    else:
        od, width, flange, mass = 11.0, 5.0, 12.5, 2.18
    ring = Part.makeCylinder(od / 2, width, App.Vector(x, y0, z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.5, width, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    fl = Part.makeCylinder(flange / 2, 1, App.Vector(x, y0, z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.5, 1, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    return part(name, model, ring.fuse(fl), f"BR-{name}", body, "Bearing steel, ZZ shields", f"Purchased NSK {model}", cid, (0.68, 0.72, 0.78), mass)


def bearing_y_reverse(name, x, y0, z, body, cid, model="F695ZZ"):
    if model == "F695ZZ":
        od, width, flange, mass = 13.0, 4.0, 15.0, 2.84
    else:
        od, width, flange, mass = 11.0, 5.0, 12.5, 2.18
    axis = App.Vector(0, -1, 0)
    ring = Part.makeCylinder(od / 2, width, App.Vector(x, y0, z), axis).cut(Part.makeCylinder(2.5, width, App.Vector(x, y0, z), axis))
    fl = Part.makeCylinder(flange / 2, 1, App.Vector(x, y0, z), axis).cut(Part.makeCylinder(2.5, 1, App.Vector(x, y0, z), axis))
    return part(name, model, ring.fuse(fl), f"BR-{name}", body, "Bearing steel, ZZ shields", f"Purchased NSK {model}", cid, (0.68, 0.72, 0.78), mass)


def timing_pulley_y(x, y0, z, teeth, width, bore=5.2):
    """Printable 3GT pulley blank with explicit teeth; final tooth coupon remains a gate."""
    pitch_radius = teeth * J2_BELT_PITCH / (2.0 * math.pi)
    root_radius = pitch_radius - 1.14
    core = Part.makeCylinder(root_radius, width, App.Vector(x, y0, z), App.Vector(0, 1, 0))
    teeth_shapes = []
    tooth_tangential = 0.61
    tooth_radial = 1.10
    for index in range(teeth):
        angle = 2.0 * math.pi * index / teeth
        cx = x + (root_radius + tooth_radial / 2.0 - 0.20) * math.cos(angle)
        cz = z + (root_radius + tooth_radial / 2.0 - 0.20) * math.sin(angle)
        tooth = Part.makeBox(tooth_radial, width, tooth_tangential, App.Vector(-tooth_radial / 2.0, y0, -tooth_tangential / 2.0))
        tooth.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), -math.degrees(angle))
        tooth.translate(App.Vector(cx, 0, cz))
        teeth_shapes.append(tooth)
    shape = core.multiFuse(teeth_shapes).removeSplitter()
    shape = shape.cut(Part.makeCylinder(bore / 2.0, width, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    return shape


def mg996_horn_shape(x_axis, y0, z_axis, direction):
    if MG996_HORN_DATA is None:
        return None
    data = MG996_HORN_DATA
    thickness = float(data["plate_thickness_mm"])
    start_y = y0 if direction > 0 else y0 - thickness
    axis = App.Vector(0, 1 if direction > 0 else -1, 0)
    if direction < 0:
        start_y = y0
    arm = Part.makeBox(float(data["arm_length_mm"]), thickness, float(data["arm_width_mm"]), App.Vector(x_axis - float(data["arm_length_mm"]) / 2.0, start_y, z_axis - float(data["arm_width_mm"]) / 2.0))
    boss = Part.makeCylinder(float(data["boss_od_mm"]) / 2.0, float(data["boss_height_mm"]), App.Vector(x_axis, y0, z_axis), axis)
    horn = arm.fuse(boss)
    horn = horn.cut(Part.makeCylinder(float(data["center_bore_mm"]) / 2.0, float(data["boss_height_mm"]), App.Vector(x_axis, y0, z_axis), axis))
    for hole in data["holes"]:
        horn = horn.cut(Part.makeCylinder(float(hole["diameter_mm"]) / 2.0, thickness, App.Vector(x_axis + float(hole["x_mm"]), start_y, z_axis + float(hole["z_mm"])), App.Vector(0, 1, 0)))
    return horn


def bearing_x(name, x0, y, z, body, cid):
    ring = Part.makeCylinder(5.5, 5, App.Vector(x0, y, z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(2.5, 5, App.Vector(x0, y, z), App.Vector(1, 0, 0)))
    fl = Part.makeCylinder(6.25, 1, App.Vector(x0, y, z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(2.5, 1, App.Vector(x0, y, z), App.Vector(1, 0, 0)))
    return part(name, "F685ZZ", ring.fuse(fl), f"BR-{name}", body, "Bearing steel, ZZ shields", "Purchased NSK F685ZZ", cid, (0.68, 0.72, 0.78), 2.18)


def truss_plate(name, x0, x1, y0, zc, pid, body, cids, color):
    length = x1 - x0
    shape = Part.makeBox(length, 3, 4, App.Vector(x0, y0, zc - 10))
    shape = shape.fuse(Part.makeBox(length, 3, 4, App.Vector(x0, y0, zc + 6)))
    shape = shape.fuse(Part.makeCylinder(10, 3, App.Vector(x0, y0, zc), App.Vector(0, 1, 0)))
    shape = shape.fuse(Part.makeCylinder(10, 3, App.Vector(x1, y0, zc), App.Vector(0, 1, 0)))
    shape = shape.cut(Part.makeCylinder(2.6, 3, App.Vector(x0, y0, zc), App.Vector(0, 1, 0)))
    shape = shape.cut(Part.makeCylinder(2.6, 3, App.Vector(x1, y0, zc), App.Vector(0, 1, 0)))
    return part(name, name.replace("_", " "), shape, pid, body, "Fiberon PA12-CF10", "FDM; 6 perimeters; plates printed flat", cids, color)


def servo_y(name, x_axis, z_axis, body, model, output_side, cid):
    if model == "MG996R":
        target_y = 12.0 if name == "J2_SERVO" else -22.0
        matrix = MG996_TO_J2 if name == "J2_SERVO" else MG996_TO_J3
        # STEP output spline datum is (10, 47.6, -10), axis local Y.
        output_x = J2_INPUT_X if name == "J2_SERVO" else x_axis
        base = App.Vector(output_x - 10.0 if name == "J2_SERVO" else output_x + 10.0, target_y - 47.6 if name == "J2_SERVO" else target_y + 47.6, 89.0)
        housing = placed_shape(MG996_SERVO_SOURCE, base, matrix)
        source_path = MG996_SERVO_STEP
        source_volume = MG996_SERVO_SOURCE.Volume
        horn_y = target_y if output_side > 0 else target_y - 2.0
        mass = 55.0
    else:
        housing = placed_shape(MG90_BODY_SOURCE, App.Vector(x_axis, 6.0, z_axis), MG90_TO_J4)
        source_path = MG90_SERVO_STEP
        source_volume = MG90_BODY_SOURCE.Volume
        horn_y = 3.2
        mass = 13.4
    obj = part(name, f"TowerPro {model} STEP assembly", housing, f"SER-{name}", body, f"TowerPro {model} purchased assembly", f"Unmodified user STEP {source_path}", cid, (0.16, 0.18, 0.22), mass)
    add_prop(obj, "App::PropertyString", "GeometrySource", source_path)
    add_prop(obj, "App::PropertyFloat", "SourceShapeVolume_mm3", float(source_volume))
    if model == "MG90S":
        # STEP horn local Z=0..5 is shifted to match the source assembly's
        # installed horn position Z=-2.8..2.2 about the spline datum.
        horn = placed_shape(MG90_HORN_SOURCE, App.Vector(x_axis, horn_y, z_axis), MG90_TO_J4)
        method = f"User STEP {MG90_HORN_STEP}; holes at +/-6.5 mm reamed for M3"
    else:
        horn = mg996_horn_shape(output_x, horn_y, z_axis, output_side)
        if horn is None:
            gate = doc.addObject("App::FeaturePython", name + "_HORN_MEASUREMENT_GATE")
            gate.Label = f"{model} horn measurement required — no provisional solid"
            add_prop(gate, "App::PropertyString", "GeometrySource", "MEASUREMENT_REQUIRED")
            add_prop(gate, "App::PropertyString", "ConnectionIDs", cid)
            return obj, horn_y
        method = f"Generated only from verified measurements in {MG996_HORN_MEASUREMENTS}"
    horn_obj = part(name + "_HORN", f"{model} stock horn", horn, f"HORN-{name}", body, "Servo-supplied reinforced polymer horn", method, cid, (0.92, 0.92, 0.92), 1.5 if model == "MG996R" else 0.6)
    add_prop(horn_obj, "App::PropertyString", "GeometrySource", MG90_HORN_STEP if model == "MG90S" else str(MG996_HORN_MEASUREMENTS))
    return obj, horn_y


# Base and compact J1. Gear geometry is copied from the validated V7 involute set.
base = Part.makeCylinder(44, 6).cut(Part.makeCylinder(2.25, 6, App.Vector(34, 0, 0)))
for a in (90, 180, 270):
    base = base.cut(Part.makeCylinder(2.25, 6, App.Vector(34 * math.cos(math.radians(a)), 34 * math.sin(math.radians(a)), 0)))
# The exact MG90S body extends down to Z=2.2 at this output datum. A through
# pocket clears the purchased case; two M2 pillars meet its untouched holes.
base = base.cut(Part.makeBox(34.0, 14.0, 6.2, App.Vector(-11.5, -7.0, 0)))
for x in (-8.55, 19.15):
    base = base.fuse(Part.makeCylinder(3.0, 15.2, App.Vector(x, 0, 4.5)))
for servo_solid in placed_shape(MG90_BODY_SOURCE, App.Vector(0, 0, 34)).Solids:
    base = base.cut(servo_solid)
# The right ear boss is tied to the pocket wall through the +X side, beginning
# 0.40 mm beyond the STEP case maximum X.  This preserves screw access while
# making the base and both ear seats one printable solid.
base = base.fuse(Part.makeBox(4.0, 6.0, 5.5, App.Vector(21.94, -3.0, 4.5)))
base = base.removeSplitter()
base_obj = part("BASE_PLATE", "Base plate OD88 pocketed for exact MG90S STEP body", base, "PR-B01", "B0_BASE", "Fiberon PA12-CF10", "FDM; 8 perimeters; 35% gyroid; M2 pillar coupon required", "C-BASE-01;C-J1-SERVO", (0.22, 0.55, 0.86))
add_prop(base_obj, "App::PropertyString", "J1IntegratedMount", "Single B-rep pillars with overlapping ribs; exact MG90S ear datums")
for i, a in enumerate((0, 90, 180, 270), 1):
    x, y = 34 * math.cos(math.radians(a)), 34 * math.sin(math.radians(a))
    insert_z(f"BASE_M4_{i}", x, y, -6, 6, "B-1_FIXTURE", "C-BASE-01", "M4")
    screw_z(f"BASE_M4X12_{i}", x, y, -6, 12, "B0_BASE", "C-BASE-01", "M4")

# Copy J1 transmission parts, retaining real involute teeth and corrected F685 dimensions.
copy_names = ["R_J1_RingGear", "R_J1_SunGear", "R_J1_Planet1", "R_J1_Planet2", "R_J1_Planet3", "R_J1_LowerHousing", "R_J1_UpperHousing", "R_J1_CarrierLower", "R_J1_CarrierUpper", "R_J1_Turntable", "R_J1_M5Shaft"]
for name in copy_names:
    src = old.getObject(name)
    if not src:
        continue
    body = "B0_BASE" if name in ("R_J1_RingGear", "R_J1_LowerHousing", "R_J1_UpperHousing") else "B1_TURNTABLE"
    mat = "PA12" if ("Gear" in name or "Planet" in name) else ("Steel shaft" if "Shaft" in name else "Fiberon PA12-CF10")
    shape = src.Shape.copy()
    cids = "C-J1-TRANSMISSION"
    if name == "R_J1_Turntable":
        left_cheek = Part.makeBox(64, 4, 38, App.Vector(-42, -44, 60)).cut(Part.makeCylinder(2.6, 4, App.Vector(0, -44, AXIS_Z), App.Vector(0, 1, 0)))
        right_cheek = Part.makeBox(40, 4, 38, App.Vector(-20, 54, 60)).cut(Part.makeCylinder(2.6, 4, App.Vector(0, 54, AXIS_Z), App.Vector(0, 1, 0)))
        left_foot = Part.makeBox(64, 16, 9, App.Vector(-42, -44, 60))
        right_foot = Part.makeBox(92, 30, 9, App.Vector(-20, 28, 60))
        shape = Part.makeCylinder(32, 6, App.Vector(0, 0, 63)).fuse(Part.makeBox(101, 60, 6, App.Vector(-29, -30, 63))).fuse(left_foot).fuse(right_foot).fuse(left_cheek).fuse(right_cheek)
        cids = "C-J1-TRANSMISSION;C-J1-DECK;C-J2-SERVO;C-J2-OUTPUT-BEARINGS;C-J2-INPUT-SUPPORT"
    if name == "R_J1_M5Shaft":
        shape = Part.makeCylinder(2.5, 18, App.Vector(0, 0, 51))
    if "Planet" in name and "Carrier" not in name:
        index = name[-1]
        pangle = math.radians(7.5 + (int(index) - 1) * 120)
        px, py = 17.9 * math.cos(pangle), 17.9 * math.sin(pangle)
        shape = shape.cut(Part.makeCylinder(6.3, 1, App.Vector(px, py, 39)))
        shape = shape.cut(Part.makeCylinder(5.55, 5, App.Vector(px, py, 39)))
        cids += f";C-J1-P{index}"
    if name == "R_J1_RingGear":
        shape = shape.common(Part.makeCylinder(37, 12, App.Vector(0, 0, 39)))
        for a in range(0, 360, 60):
            x, y = 38 * math.cos(math.radians(a)), 38 * math.sin(math.radians(a))
            shape = shape.fuse(Part.makeCylinder(4, 12, App.Vector(x, y, 39))).cut(Part.makeCylinder(1.7, 12, App.Vector(x, y, 39)))
        cids += ";C-J1-RINGCASE"
    if name in ("R_J1_LowerHousing", "R_J1_UpperHousing"):
        z0, height = (34, 5) if name == "R_J1_LowerHousing" else (51, 3)
        shape = shape.common(Part.makeCylinder(42, height, App.Vector(0, 0, z0)))
        for a in range(0, 360, 60):
            x, y = 38 * math.cos(math.radians(a)), 38 * math.sin(math.radians(a))
            radius = 3.0 if name == "R_J1_LowerHousing" else 1.7
            shape = shape.cut(Part.makeCylinder(radius, height, App.Vector(x, y, z0)))
        cids += ";C-J1-RINGCASE"
    if name == "R_J1_SunGear":
        hub = Part.makeCylinder(9, 3, App.Vector(0, 0, 36)).cut(Part.makeCylinder(1.5, 3, App.Vector(0, 0, 36)))
        shape = shape.fuse(hub)
        cids += ";C-J1-SUN-HORN"
    if name == "R_J1_CarrierLower":
        shape = shape.cut(Part.makeCylinder(9.5, 4, App.Vector(0, 0, 36)))
    compact_labels = {
        "R_J1_LowerHousing": "J1 compact lower case OD84; six M3 inserts",
        "R_J1_UpperHousing": "J1 compact upper case OD84; six M3 clearances",
        "R_J1_Turntable": "Compact turntable 74 x 64 envelope",
        "R_J1_M5Shaft": "J1 5 mm output shaft cut 18 mm",
    }
    source_color = src.ViewObject.ShapeColor if src.ViewObject is not None else (0.72, 0.72, 0.76)
    part("V8_" + name, compact_labels.get(name, src.Label + " V8"), shape, "PR-J1-" + name, body, mat, "FDM" if "PA12" in mat else "Purchased/cut", cids, source_color)

# J1 MG90S is vertical and physically drives the sun through its stock horn and bolted printed hub.
j1_servo_shape = placed_shape(MG90_BODY_SOURCE, App.Vector(0, 0, 34))
j1_servo = part("J1_SERVO", "TowerPro MG90S J1 exact STEP servo", j1_servo_shape, "SER-J1", "B0_BASE", "TowerPro MG90S purchased assembly", f"Unmodified user STEP {MG90_SERVO_STEP}", "C-J1-SERVO;C-J1-SUN-HORN", (0.16, 0.18, 0.22), 13.4)
add_prop(j1_servo, "App::PropertyString", "GeometrySource", MG90_SERVO_STEP)
add_prop(j1_servo, "App::PropertyFloat", "SourceShapeVolume_mm3", float(MG90_BODY_SOURCE.Volume))
j1_horn = MG90_HORN_SOURCE.copy()
j1_horn.Placement = App.Placement(App.Vector(0, 0, 31.2), App.Rotation(App.Vector(0, 0, 1), 37.5))
j1_horn_obj = part("J1_STOCK_HORN", "MG90S STEP double-arm horn", j1_horn, "HORN-J1", "B0_BASE", "Servo-supplied reinforced polymer horn", f"User STEP {MG90_HORN_STEP}; +/-6.5 mm holes reamed 2.2 mm", "C-J1-SUN-HORN", (0.92, 0.92, 0.92), 0.6)
add_prop(j1_horn_obj, "App::PropertyString", "GeometrySource", MG90_HORN_STEP)
horn_angle = math.radians(37.5)
for i, sign in enumerate((-1, 1), 1):
    x = sign * 6.5 * math.cos(horn_angle)
    y = sign * 6.5 * math.sin(horn_angle)
    m2_hole = Part.makeCylinder(1.1, 7.8, App.Vector(x, y, 31.2))
    doc.getObject("J1_STOCK_HORN").Shape = doc.getObject("J1_STOCK_HORN").Shape.cut(m2_hole)
    doc.getObject("V8_R_J1_SunGear").Shape = doc.getObject("V8_R_J1_SunGear").Shape.cut(m2_hole)
    m2_shank = Part.makeCylinder(1.0, 7, App.Vector(x, y, 31.2))
    m2_head = Part.makeCylinder(2.0, 1.5, App.Vector(x, y, 29.7))
    part(f"J1_HORN_M2_{i}", "M2x7 horn screw", m2_shank.fuse(m2_head), f"SCR-J1-HORN-M2-{i}", "B1_TURNTABLE", "Steel A2-70", "Purchased M2x7 screw", "C-J1-SUN-HORN", (0.55, 0.57, 0.60))
    m2_insert = Part.makeCylinder(1.75, 3, App.Vector(x, y, 36)).cut(Part.makeCylinder(1.0, 3, App.Vector(x, y, 36)))
    m2_insert_obj = part(f"J1_HORN_INSERT_M2_{i}", "M2 heat-set insert OD3.5 L3", m2_insert, f"INS-J1-HORN-M2-{i}", "B1_TURNTABLE", "Brass heat-set insert", "Purchased; thermal press-fit after coupon calibration", "C-J1-SUN-HORN", (0.84, 0.58, 0.18))
    add_prop(m2_insert_obj, "App::PropertyString", "InsertThread", "M2")
    add_prop(m2_insert_obj, "App::PropertyFloat", "InsertOD_mm", 3.5)
    add_prop(m2_insert_obj, "App::PropertyFloat", "InsertLength_mm", 3.0)
# The source STEP center screw is a separate physical retention part.
j1_center = placed_shape(MG90_CENTER_SCREW_SOURCE, App.Vector(0, 0, 34))
j1_center_obj = part("J1_HORN_CENTER_SCREW", "MG90S supplied horn center screw", j1_center, "SCR-J1-HORN-CENTER", "B0_BASE", "Steel servo screw", f"User STEP {MG90_SERVO_STEP}", "C-J1-SUN-HORN", (0.50, 0.52, 0.56))
for pn, pv, pt in (("FastenerSize", "Servo-supplied", "App::PropertyString"), ("FastenerLength_mm", 5.75, "App::PropertyFloat"), ("ThreadEngagement_mm", 2.5, "App::PropertyFloat"), ("ToolAccessDirection", "+Z", "App::PropertyString"), ("ToolClearance_mm", 10.0, "App::PropertyFloat"), ("ToolAccessStage", "Before J1 gearcase closure", "App::PropertyString")):
    add_prop(j1_center_obj, pt, pn, pv)
for i, x in enumerate((-8.55, 19.15), 1):
    doc.getObject("BASE_PLATE").Shape = doc.getObject("BASE_PLATE").Shape.cut(Part.makeCylinder(1.8, 3, App.Vector(x, 0, 16.7)))
    insert = Part.makeCylinder(1.75, 3, App.Vector(x, 0, 16.7)).cut(Part.makeCylinder(1.0, 3, App.Vector(x, 0, 16.7)))
    ins = part(f"J1_SERVO_{i}", "M2 heat-set insert OD3.5 L3", insert, f"INS-J1-SERVO-{i}", "B0_BASE", "Brass heat-set insert", "Purchased; thermal press-fit after coupon calibration", "C-J1-SERVO", (0.84, 0.58, 0.18))
    add_prop(ins, "App::PropertyString", "InsertThread", "M2")
    add_prop(ins, "App::PropertyFloat", "InsertOD_mm", 3.5)
    add_prop(ins, "App::PropertyFloat", "InsertLength_mm", 3.0)
    sh = Part.makeCylinder(1.0, 8, App.Vector(x, 0, 23.7), App.Vector(0, 0, -1)).fuse(Part.makeCylinder(2.0, 1.5, App.Vector(x, 0, 25.2), App.Vector(0, 0, -1)))
    so = part(f"J1_SERVO_M2_{i}", "M2x8 low-head servo screw", sh, f"SCR-J1-SERVO-{i}", "B0_BASE", "Steel A2-70", "Purchased M2x8", "C-J1-SERVO", (0.55, 0.57, 0.60))
    for pn, pv, pt in (("FastenerSize", "M2", "App::PropertyString"), ("FastenerLength_mm", 8.0, "App::PropertyFloat"), ("ThreadEngagement_mm", 3.0, "App::PropertyFloat"), ("ToolAccessDirection", "+Z", "App::PropertyString"), ("ToolClearance_mm", 10.0, "App::PropertyFloat"), ("ToolAccessStage", "Before J1 gearcase closure", "App::PropertyString")):
        add_prop(so, pt, pn, pv)
    add_prop(so, "App::PropertyFloat", "STEPHoleCenterX_mm", x)
    add_prop(so, "App::PropertyFloat", "STEPHoleCenterZ_mm", 16.7)
    add_prop(so, "App::PropertyFloat", "HoleAxisAlignmentError_mm", 0.0)

# Six top-access M3x20 screws clamp the upper case and ring into lower-case heat-set inserts.
for i, a in enumerate(range(0, 360, 60), 1):
    x, y = 38 * math.cos(math.radians(a)), 38 * math.sin(math.radians(a))
    insert_z(f"J1_CASE_{i}", x, y, 35, 4, "B0_BASE", "C-J1-RINGCASE")
    screw_z(f"J1_CASE_M3X20_{i}", x, y, 34, 20, "B0_BASE", "C-J1-RINGCASE")

# J1 output shaft enters a split clamp in the integral turntable; it is not fused magically.
j1_tt = doc.getObject("V8_R_J1_Turntable")
j1_tt.ConnectionIDs += ";C-J1-OUTPUT-CLAMP"
j1_tt.Shape = j1_tt.Shape.cut(Part.makeCylinder(2.55, 6, App.Vector(0, 0, 63)))
j1_tt.Shape = j1_tt.Shape.cut(Part.makeBox(10, 1, 6, App.Vector(0, -0.5, 63)))
j1_tt.Shape = j1_tt.Shape.cut(Part.makeCylinder(1.7, 11, App.Vector(7, -8, 66), App.Vector(0, 1, 0)))
j1_tt.Shape = j1_tt.Shape.cut(Part.makeCylinder(3, 4, App.Vector(7, 3, 66), App.Vector(0, 1, 0)))
insert_y("J1_OUTPUT_CLAMP", 7, 3, 66, 4, "B1_TURNTABLE", "C-J1-OUTPUT-CLAMP")
screw_y("J1_OUTPUT_CLAMP_M3", 7, -8, 66, 15, 1, "B1_TURNTABLE", "C-J1-OUTPUT-CLAMP")
add_prop(doc.getObject("V8_R_J1_M5Shaft"), "App::PropertyString", "RetentionMethod", "0.5 mm machined flat + integral M3 split clamp")

# Correct 5 mm-wide F685 planet bearings at the three actual planet centers.
for i in range(3):
    angle = math.radians(7.5 + i * 120)
    x, y = 17.9 * math.cos(angle), 17.9 * math.sin(angle)
    ring = Part.makeCylinder(5.5, 5, App.Vector(x, y, 39)).cut(Part.makeCylinder(2.5, 5, App.Vector(x, y, 39)))
    fl = Part.makeCylinder(6.25, 1, App.Vector(x, y, 39)).cut(Part.makeCylinder(2.5, 1, App.Vector(x, y, 39)))
    part(f"J1_PLANET_BRG_{i+1}", "F685ZZ planet bearing", ring.fuse(fl), f"BR-685-{i+1}", "B1_TURNTABLE", "Bearing steel, ZZ shields", "Purchased NSK F685ZZ", f"C-J1-P{i+1}", (0.68, 0.72, 0.78), 2.18)
    pshaft = Part.makeCylinder(2.5, 17, App.Vector(x, y, 36.5))
    part(f"J1_PLANET_SHAFT_{i+1}", "J1 5 mm planet shaft", pshaft, f"SH-J1-P{i+1}", "B1_TURNTABLE", "Hardened steel shaft", "Purchased 5 mm shaft; cut and deburr", f"C-J1-P{i+1};C-J1-RETENTION;C-J1-TRANSMISSION", (0.58, 0.60, 0.64))

# Two F695ZZ bearings support the J1 output shaft; flanges oppose axial withdrawal.
for i, z0 in enumerate((54, 59), 1):
    ring = Part.makeCylinder(6.5, 4, App.Vector(0, 0, z0)).cut(Part.makeCylinder(2.5, 4, App.Vector(0, 0, z0)))
    fl = Part.makeCylinder(7.5, 1, App.Vector(0, 0, z0)).cut(Part.makeCylinder(2.5, 1, App.Vector(0, 0, z0)))
    part(f"F695_J1_{i}", "F695ZZ J1 output bearing", ring.fuse(fl), f"BR-695-{i}", "B0_BASE", "Bearing steel, ZZ shields", "Purchased NSK F695ZZ", "C-J1-BRG;C-J1-TRANSMISSION", (0.68, 0.72, 0.78), 2.84)

# Real servos and structural links in the fully extended inspection pose.
servo_y("J2_SERVO", J2_INPUT_X, AXIS_Z, "B1_TURNTABLE", "MG996R", 1, "C-J2-SERVO;C-J2-HORN-COUPLER")
ua_l = truss_plate("UPPER_ARM_L", 0, 115, -39, AXIS_Z, "PR-L01", "B2_UPPER_ARM", "C-J2-OUTPUT-BEARINGS;C-J3-PASSIVE;C-UA-CROSS", (0.20, 0.76, 0.36))
ua_r = truss_plate("UPPER_ARM_R", 0, 115, 28, AXIS_Z, "PR-L02", "B2_UPPER_ARM", "C-J2-BELT;C-J2-OUTPUT-BEARINGS;C-J3-SERVO;C-J3-PASSIVE;C-UA-CROSS", (0.20, 0.76, 0.36))
j2_driven = timing_pulley_y(0, 37.0, AXIS_Z, J2_DRIVEN_TEETH, J2_BELT_WIDTH)
j2_driven = j2_driven.fuse(Part.makeCylinder(9, 9, App.Vector(0, 28, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.6, 9, App.Vector(0, 28, AXIS_Z), App.Vector(0, 1, 0)))).removeSplitter()
ua_r.Shape = ua_r.Shape.fuse(j2_driven)
servo_y("J3_SERVO", 115, AXIS_Z, "B2_UPPER_ARM", "MG996R", -1, "C-J3-SERVO;C-J3-ACTIVE")
fa_l = truss_plate("FOREARM_L", 115, 230, -30, AXIS_Z, "PR-L03", "B3_FOREARM", "C-J3-ACTIVE;C-J4-PASSIVE;C-J4-SERVO", (0.10, 0.64, 0.30))
fa_r = truss_plate("FOREARM_R", 115, 230, 34, AXIS_Z, "PR-L04", "B3_FOREARM", "C-J3-PASSIVE;C-J4-SERVO", (0.10, 0.64, 0.30))
servo_y("J4_SERVO", 230, AXIS_Z, "B3_FOREARM", "MG90S", 1, "C-J4-SERVO;C-J4-ACTIVE")

# Bearing seats are real 13.1 mm press-fit bores with a 15.1 mm flange counterbore.
ua_l.Shape = ua_l.Shape.cut(Part.makeCylinder(6.55, 3, App.Vector(0, -39, AXIS_Z), App.Vector(0, 1, 0)))
ua_l.Shape = ua_l.Shape.cut(Part.makeCylinder(7.55, 1, App.Vector(0, -39, AXIS_Z), App.Vector(0, 1, 0)))
ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(6.55, 4, App.Vector(0, 31, AXIS_Z), App.Vector(0, -1, 0)))
ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(7.55, 1, App.Vector(0, 31, AXIS_Z), App.Vector(0, -1, 0)))
ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(6.55, 3, App.Vector(115, 28, AXIS_Z), App.Vector(0, 1, 0)))
ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(7.55, 1, App.Vector(115, 28, AXIS_Z), App.Vector(0, 1, 0)))
fa_l.Shape = fa_l.Shape.cut(Part.makeCylinder(6.55, 3, App.Vector(230, -30, AXIS_Z), App.Vector(0, 1, 0)))
fa_l.Shape = fa_l.Shape.cut(Part.makeCylinder(7.55, 1, App.Vector(230, -30, AXIS_Z), App.Vector(0, 1, 0)))

# Passive support bearings, short keyed/flat stub shafts, collars; no shaft passes through a servo.
bearing_y("F695_J2_L", 0, -39, AXIS_Z, "B2_UPPER_ARM", "C-J2-OUTPUT-BEARINGS")
bearing_y_reverse("F695_J2_R", 0, 31, AXIS_Z, "B2_UPPER_ARM", "C-J2-OUTPUT-BEARINGS")
bearing_y("F695_J3", 115, 28, AXIS_Z, "B2_UPPER_ARM", "C-J3-PASSIVE")
bearing_y("F695_J4", 230, -30, AXIS_Z, "B3_FOREARM", "C-J4-PASSIVE")
for j, x, y0, body in ((3, 115, 27, "B3_FOREARM"), (4, 230, -37, "B4_WRIST_PITCH")):
    shaft = Part.makeCylinder(2.5, 11 if j in (2, 4) else 12, App.Vector(x, y0, AXIS_Z), App.Vector(0, 1, 0))
    part(f"J{j}_PASSIVE_STUB", f"J{j} 5 mm passive stub with machined flat", shaft, f"SH-J{j}-P", body, "Hardened steel shaft", "Purchased 5 mm shaft; cut, deburr, mill 0.5 mm flat", f"C-J{j}-PASSIVE", (0.58, 0.60, 0.64))
    collar_y = y0 - 5 if j == 4 else 39
    radial_hole = Part.makeCylinder(1.5, 4, App.Vector(x + 5, collar_y + 2.5, AXIS_Z), App.Vector(-1, 0, 0))
    collar = Part.makeCylinder(5, 5, App.Vector(x, collar_y, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.55, 5, App.Vector(x, collar_y, AXIS_Z), App.Vector(0, 1, 0))).cut(radial_hole)
    part(f"J{j}_COLLAR", f"J{j} CL05M 5 mm set-screw collar", collar, f"COL-J{j}", body, "Zinc-plated steel collar", "Purchased Motionco CL05M; 5 ID x 10 OD x 5 W", f"C-J{j}-RETENTION;C-J{j}-PASSIVE", (0.58, 0.60, 0.64))
    part(f"J{j}_COLLAR_SETSCREW", "CL05M included M3 set screw", radial_hole, f"SET-J{j}", body, "Steel", "Included with Motionco CL05M", f"C-J{j}-RETENTION;C-J{j}-PASSIVE", (0.48, 0.50, 0.54))

j2_output_shaft = Part.makeCylinder(2.5, 102, App.Vector(0, -44, AXIS_Z), App.Vector(0, 1, 0))
part("J2_OUTPUT_SHAFT", "J2 fixed 5 mm shoulder journal with two flats", j2_output_shaft, "SH-J2-OUT", "B1_TURNTABLE", "Hardened steel shaft", "Purchased E-SFJ5; cut 102 mm; two 0.5 mm flats", "C-J2-OUTPUT-BEARINGS;C-J2-RETENTION", (0.58, 0.60, 0.64))
turntable_obj = doc.getObject("V8_R_J1_Turntable")
turntable_obj.ConnectionIDs += ";C-J2-RETENTION"
for side, y_center in (("L", -42), ("R", 56)):
    turntable_obj.Shape = turntable_obj.Shape.cut(Part.makeBox(2, 4, 19, App.Vector(-1, y_center - 2, AXIS_Z)))
    turntable_obj.Shape = turntable_obj.Shape.cut(Part.makeCylinder(1.7, 17, App.Vector(-8, y_center, AXIS_Z + 5), App.Vector(1, 0, 0)))
    turntable_obj.Shape = turntable_obj.Shape.cut(Part.makeCylinder(3, 4, App.Vector(5, y_center, AXIS_Z + 5), App.Vector(1, 0, 0)))
    insert_x(f"J2_SHAFT_CLAMP_{side}", 5, y_center, AXIS_Z + 5, 4, "B1_TURNTABLE", "C-J2-RETENTION")
    screw_x(f"J2_SHAFT_CLAMP_M3_{side}", -8, y_center, AXIS_Z + 5, 17, "B1_TURNTABLE", "C-J2-RETENTION")

# Two printed cross-spacers make the parallel upper-arm plates a physical box
# structure.  M3 screws enter heat-set inserts from both outer faces; no long
# through-bolt or assembly constraint is credited.
for index, (x, z) in enumerate(((45, AXIS_Z + 16.5), (60, AXIS_Z + 16.5)), 1):
    spacer = Part.makeCylinder(5, 64, App.Vector(x, -36, z), App.Vector(0, 1, 0))
    spacer = spacer.cut(Part.makeCylinder(1.7, 4, App.Vector(x, -36, z), App.Vector(0, 1, 0)))
    spacer = spacer.cut(Part.makeCylinder(1.7, 4, App.Vector(x, 28, z), App.Vector(0, -1, 0)))
    part(f"UPPER_ARM_SPACER_{index}", f"Upper-arm M3 cross-spacer {index}", spacer, f"PR-UA-SP-{index}", "B2_UPPER_ARM", "Fiberon PA12-CF10", "FDM flat; 8 perimeters; M3 inserts both ends", "C-UA-CROSS", (0.20, 0.76, 0.36))
    ua_l.Shape = ua_l.Shape.fuse(Part.makeCylinder(7, 3, App.Vector(x, -39, z), App.Vector(0, 1, 0)))
    ua_r.Shape = ua_r.Shape.fuse(Part.makeCylinder(7, 3, App.Vector(x, 28, z), App.Vector(0, 1, 0)))
    ua_l.Shape = ua_l.Shape.cut(Part.makeCylinder(1.7, 3, App.Vector(x, -39, z), App.Vector(0, 1, 0)))
    ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(1.7, 3, App.Vector(x, 28, z), App.Vector(0, 1, 0)))
    insert_y(f"UA_SPACER_{index}_L", x, -36, z, 4, "B2_UPPER_ARM", "C-UA-CROSS")
    insert_y(f"UA_SPACER_{index}_R", x, 24, z, 4, "B2_UPPER_ARM", "C-UA-CROSS")
    screw_y(f"UA_SPACER_M3_{index}_L", x, -41, z, 9, 1, "B2_UPPER_ARM", "C-UA-CROSS")
    screw_y(f"UA_SPACER_M3_{index}_R", x, 33, z, 9, -1, "B2_UPPER_ARM", "C-UA-CROSS")

# Wrist pitch carrier and coaxial-near roll stack.
wp_l = truss_plate("WRIST_PITCH_L", 230, J5_X, -36, AXIS_Z, "PR-W01", "B4_WRIST_PITCH", "C-J4-PASSIVE;C-J5-HOUSING", (0.12, 0.58, 0.80))
wp_r = truss_plate("WRIST_PITCH_R", 230, J5_X, 14, AXIS_Z, "PR-W02", "B4_WRIST_PITCH", "C-J4-ACTIVE;C-J5-HOUSING;C-J5-SERVO", (0.12, 0.58, 0.80))
# J5 axis is moved 13 mm outward because the exact J4/J5 MG90S bodies overlap
# at the former 30 mm pitch. This is the minimum whole-mm pitch with clearance.
j5_body = placed_shape(MG90_BODY_SOURCE, App.Vector(J5_X, 0, AXIS_Z), MG90_TO_J5)
j5_servo = part("J5_SERVO", "TowerPro MG90S J5 exact STEP servo", j5_body, "SER-J5", "B4_WRIST_PITCH", "TowerPro MG90S purchased assembly", f"Unmodified user STEP {MG90_SERVO_STEP}", "C-J5-SERVO;C-J5-ACTIVE", (0.16, 0.18, 0.22), 13.4)
add_prop(j5_servo, "App::PropertyString", "GeometrySource", MG90_SERVO_STEP)
add_prop(j5_servo, "App::PropertyFloat", "SourceShapeVolume_mm3", float(MG90_BODY_SOURCE.Volume))
housing = Part.makeBox(18, 53, 30, App.Vector(J5_X, -36, 64))
housing = housing.cut(Part.makeCylinder(10.0, 5, App.Vector(J5_X, 0, AXIS_Z), App.Vector(1, 0, 0)))
housing = housing.cut(Part.makeBox(5, 10, 38, App.Vector(J5_X, -5, AXIS_Z - 19)))
housing = housing.cut(Part.makeCylinder(6.3, 13, App.Vector(J5_X + 5, 0, AXIS_Z), App.Vector(1, 0, 0)))
part("J5_BEARING_HOUSING", "J5 dual-bearing housing", housing, "PR-W03", "B4_WRIST_PITCH", "Fiberon PA12-CF10", "FDM; 8 perimeters; bearing bores reamed", "C-J5-HOUSING;C-J5-BRG", (0.12, 0.58, 0.80))
housing_obj = doc.getObject("J5_BEARING_HOUSING")
housing_obj.Shape = housing_obj.Shape.cut(wp_l.Shape).cut(wp_r.Shape)
# Four topologically real M3x16 axial screws join the two wrist plates to the bearing housing.
for iy, y in enumerate((-34.5, 15.5), 1):
    for iz, dz in enumerate((-5, 5), 1):
        z = AXIS_Z + dz
        clearance = Part.makeCylinder(1.7, 12, App.Vector(J5_X - 12, y, z), App.Vector(1, 0, 0))
        (wp_l if y < 0 else wp_r).Shape = (wp_l if y < 0 else wp_r).Shape.cut(clearance)
        housing_obj.Shape = housing_obj.Shape.cut(Part.makeCylinder(3, 4, App.Vector(J5_X, y, z), App.Vector(1, 0, 0)))
        ins_shape = Part.makeCylinder(3, 4, App.Vector(J5_X, y, z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(1.5, 4, App.Vector(J5_X, y, z), App.Vector(1, 0, 0)))
        ins_obj = part(f"J5_HOUSING_INS_{iy}_{iz}", "M3 heat-set insert OD6 L4", ins_shape, f"INS-J5-H-{iy}-{iz}", "B4_WRIST_PITCH", "Brass heat-set insert", "Thermal press-fit", "C-J5-HOUSING", (0.84, 0.58, 0.18))
        add_prop(ins_obj, "App::PropertyString", "InsertThread", "M3")
        add_prop(ins_obj, "App::PropertyFloat", "InsertOD_mm", 6.0)
        add_prop(ins_obj, "App::PropertyFloat", "InsertLength_mm", 4.0)
        sh = Part.makeCylinder(1.5, 16, App.Vector(J5_X - 12, y, z), App.Vector(1, 0, 0)).fuse(Part.makeCylinder(3, 2, App.Vector(J5_X - 14, y, z), App.Vector(1, 0, 0)))
        so = part(f"J5_HOUSING_M3_{iy}_{iz}", "M3x16 low-head housing screw", sh, f"SCR-J5-H-{iy}-{iz}", "B4_WRIST_PITCH", "Steel A2-70", "Purchased", "C-J5-HOUSING", (0.55, 0.57, 0.60))
        add_prop(so, "App::PropertyString", "FastenerSize", "M3")
        add_prop(so, "App::PropertyFloat", "FastenerLength_mm", 16.0)
        add_prop(so, "App::PropertyFloat", "ThreadEngagement_mm", 4.0)
        add_prop(so, "App::PropertyString", "ToolAccessDirection", "-X")
        add_prop(so, "App::PropertyFloat", "ToolClearance_mm", 10.0)
        add_prop(so, "App::PropertyString", "ToolAccessStage", "Install before gripper cradle")
bearing_x("F685_J5_A", J5_X + 5, 0, AXIS_Z, "B4_WRIST_PITCH", "C-J5-BRG")
bearing_x("F685_J5_B", J5_X + 13, 0, AXIS_Z, "B4_WRIST_PITCH", "C-J5-BRG")
j5shaft = Part.makeCylinder(2.5, 28, App.Vector(J5_X, 0, AXIS_Z), App.Vector(1, 0, 0))
part("J5_OUTPUT_SHAFT", "J5 5 mm output shaft", j5shaft, "SH-J5", "B5_TOOL", "Hardened steel shaft", "Purchased 5 mm shaft; cut and deburr", "C-J5-ACTIVE;C-J5-BRG;C-J5-RETENTION;C-J5-TOOL", (0.58, 0.60, 0.64))
# Stock horn and compact bolted adapter are contained ahead of the first bearing.
j5_horn = placed_shape(MG90_HORN_SOURCE, App.Vector(J5_X - 2.8, 0, AXIS_Z), MG90_TO_J5)
j5_horn_obj = part("J5_STOCK_HORN", "MG90S STEP double-arm horn", j5_horn, "HORN-J5", "B4_WRIST_PITCH", "Servo-supplied reinforced polymer horn", f"User STEP {MG90_HORN_STEP}; +/-6.5 mm holes reamed 2.2 mm", "C-J5-ACTIVE", (0.92, 0.92, 0.92), 0.6)
add_prop(j5_horn_obj, "App::PropertyString", "GeometrySource", MG90_HORN_STEP)
j5_adapter = Part.makeCylinder(9.5, 3.5, App.Vector(J5_X + 1.5, 0, AXIS_Z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(2.5, 3.5, App.Vector(J5_X + 1.5, 0, AXIS_Z), App.Vector(1, 0, 0)))
part("J5_HORN_SHAFT_ADAPTER", "J5 horn-to-5mm shaft adapter", j5_adapter, "PR-HUB-J5", "B5_TOOL", "Fiberon PA12-CF10", "FDM; 10 perimeters; ream 5H8", "C-J5-ACTIVE", (0.88, 0.48, 0.12))
for i, dz in enumerate((-6.5, 6.5), 1):
    hole = Part.makeCylinder(1.1, 5, App.Vector(J5_X, 0, AXIS_Z + dz), App.Vector(1, 0, 0))
    doc.getObject("J5_STOCK_HORN").Shape = doc.getObject("J5_STOCK_HORN").Shape.cut(hole)
    doc.getObject("J5_HORN_SHAFT_ADAPTER").Shape = doc.getObject("J5_HORN_SHAFT_ADAPTER").Shape.cut(hole)
    bolt = Part.makeCylinder(1, 5, App.Vector(J5_X, 0, AXIS_Z + dz), App.Vector(1, 0, 0)).fuse(Part.makeCylinder(2, 1.5, App.Vector(J5_X - 1.5, 0, AXIS_Z + dz), App.Vector(1, 0, 0)))
    part(f"J5_HORN_M2_{i}", "M2x5 horn adapter bolt", bolt, f"SCR-J5-HORN-M2-{i}", "B5_TOOL", "Steel A2-70", "Purchased M2x5 screw + locknut", "C-J5-ACTIVE", (0.55, 0.57, 0.60))
    nut = Part.makeCylinder(2.1, 1.5, App.Vector(J5_X + 3.5, 0, AXIS_Z + dz), App.Vector(1, 0, 0)).cut(Part.makeCylinder(1, 1.5, App.Vector(J5_X + 3.5, 0, AXIS_Z + dz), App.Vector(1, 0, 0)))
    part(f"J5_HORN_NUT_M2_{i}", "M2 prevailing-torque nut", nut, f"NUT-J5-HORN-M2-{i}", "B5_TOOL", "Steel locknut", "Purchased", "C-J5-ACTIVE", (0.55, 0.57, 0.60))
j5_center = placed_shape(MG90_CENTER_SCREW_SOURCE, App.Vector(J5_X, 0, AXIS_Z), MG90_TO_J5)
j5_center_obj = part("J5_HORN_CENTER_SCREW", "MG90S supplied horn center screw", j5_center, "SCR-J5-HORN-CENTER", "B4_WRIST_PITCH", "Steel servo screw", f"User STEP {MG90_SERVO_STEP}", "C-J5-ACTIVE", (0.50, 0.52, 0.56))
for pn, pv, pt in (("FastenerSize", "Servo-supplied", "App::PropertyString"), ("FastenerLength_mm", 5.75, "App::PropertyFloat"), ("ThreadEngagement_mm", 2.5, "App::PropertyFloat"), ("ToolAccessDirection", "-X", "App::PropertyString"), ("ToolClearance_mm", 10.0, "App::PropertyFloat"), ("ToolAccessStage", "Before J5 bearing housing closure", "App::PropertyString")):
    add_prop(j5_center_obj, pt, pn, pv)
j5_set_hole = Part.makeCylinder(1.5, 4, App.Vector(J5_X + 20.5, 0, AXIS_Z + 5), App.Vector(0, 0, -1))
j5_collar = Part.makeCylinder(5, 5, App.Vector(J5_X + 18, 0, AXIS_Z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(2.55, 5, App.Vector(J5_X + 18, 0, AXIS_Z), App.Vector(1, 0, 0))).cut(j5_set_hole)
part("J5_OUTER_COLLAR", "J5 CL05M 5 mm set-screw collar", j5_collar, "COL-J5", "B5_TOOL", "Zinc-plated steel collar", "Purchased Motionco CL05M; 5 ID x 10 OD x 5 W", "C-J5-RETENTION", (0.58, 0.60, 0.64))
part("J5_COLLAR_SETSCREW", "CL05M included M3 set screw", j5_set_hole, "SET-J5", "B5_TOOL", "Steel", "Included with Motionco CL05M", "C-J5-RETENTION", (0.48, 0.50, 0.54))

# Compact printed gripper proxy with real M3 bolted palm.
palm_x = J5_X + 23
palm = Part.makeBox(5, 34, 26, App.Vector(palm_x, -17, 66))
palm = palm.fuse(Part.makeCylinder(7, 5, App.Vector(palm_x, 0, AXIS_Z), App.Vector(1, 0, 0)))
palm = palm.cut(Part.makeCylinder(2.55, 5, App.Vector(palm_x, 0, AXIS_Z), App.Vector(1, 0, 0)))
palm = palm.cut(Part.makeBox(5, 1, 8, App.Vector(palm_x, -0.5, AXIS_Z)))
palm = palm.cut(Part.makeCylinder(1.7, 11, App.Vector(palm_x + 2.5, -8, AXIS_Z + 5), App.Vector(0, 1, 0)))
palm = palm.cut(Part.makeCylinder(3, 4, App.Vector(palm_x + 2.5, 3, AXIS_Z + 5), App.Vector(0, 1, 0)))
palm = palm.cut(Part.makeCylinder(1.7, 5, App.Vector(palm_x, -10, 73), App.Vector(1, 0, 0)))
palm = palm.cut(Part.makeCylinder(1.7, 5, App.Vector(palm_x, 10, 85), App.Vector(1, 0, 0)))
finger_l = Part.makeBox(5, 4, 34, App.Vector(palm_x, -17, 89))
finger_r = Part.makeBox(5, 4, 34, App.Vector(palm_x, 13, 89))
part("GRIPPER_CRADLE", "One-piece compact gripper cradle", palm.fuse(finger_l).fuse(finger_r), "PR-E01", "B5_TOOL", "Fiberon PA12-CF10", "FDM; 6 perimeters; one-piece cradle", "C-TOOL-01;C-J5-TOOL", (0.88, 0.48, 0.12))
insert_y("J5_TOOL_CLAMP", palm_x + 2.5, 3, AXIS_Z + 5, 4, "B5_TOOL", "C-J5-TOOL")
screw_y("J5_TOOL_CLAMP_M3", palm_x + 2.5, -8, AXIS_Z + 5, 15, 1, "B5_TOOL", "C-J5-TOOL")

# Exact STEP mounting datums. Purchased servo geometry is never fused or cut.
# MG996R: four existing 4.44 mm slots at global X/Z coordinates below.
mg996_mounts = {
    2: {"xs": (-15.0 + J2_INPUT_X, 35.3 + J2_INPUT_X), "zs": (74.5, 83.5), "insert_y": -13.0, "screw_y": -1.0, "direction": -1, "length": 12, "body": "B1_TURNTABLE"},
    3: {"xs": (130.0, 79.7), "zs": (74.5, 83.5), "insert_y": -1.0, "screw_y": 7.0, "direction": -1, "length": 11, "body": "B2_UPPER_ARM"},
}
for j, spec in mg996_mounts.items():
    mount = Part.Shape()
    solids = []
    for x in spec["xs"]:
        solids.append(Part.makeBox(9, 4, 20, App.Vector(x - 4.5, spec["insert_y"], 68.5)))
        if j == 3:
            solids.append(Part.makeBox(9, 26, 6, App.Vector(x - 4.5, 3, 64)))
    mount = solids[0]
    for solid in solids[1:]:
        mount = mount.fuse(solid)
    for x in spec["xs"]:
        for z in spec["zs"]:
            mount = mount.cut(Part.makeCylinder(2.6, 4, App.Vector(x, spec["insert_y"], z), App.Vector(0, 1, 0)))
    mount = mount.cut(doc.getObject(f"J{j}_SERVO").Shape)
    if j == 2:
        host = doc.getObject("V8_R_J1_Turntable")
        mount = mount.fuse(Part.makeBox(80, 8, 5.5, App.Vector(-9, -13, 63)))
    else:
        host = doc.getObject("UPPER_ARM_R")
        # Root shelf overlaps the plate at X=106..115 and then steps inward,
        # avoiding the rotating forearm beyond the J3 axis.
        mount = mount.fuse(Part.makeBox(29, 26, 6, App.Vector(106, 3, 64)))
    host.Shape = host.Shape.fuse(mount).cut(doc.getObject(f"J{j}_SERVO").Shape)
    add_prop(host, "App::PropertyString", f"J{j}IntegratedMount", "Single B-rep cradle; 0.4 mm case clearance; servo-ear seating only")
    host.ConnectionIDs += f";C-J{j}-SERVO"
    for ix, x in enumerate(spec["xs"], 1):
        for iz, z in enumerate(spec["zs"], 1):
            insert_y(f"J{j}_SERVO_{ix}_{iz}", x, spec["insert_y"], z, 4, spec["body"], f"C-J{j}-SERVO", "M4")
            servo_screw = screw_y(f"J{j}_SERVO_M4_{ix}_{iz}", x, spec["screw_y"], z, spec["length"], spec["direction"], spec["body"], f"C-J{j}-SERVO", "M4")
            add_prop(servo_screw, "App::PropertyFloat", "STEPHoleCenterX_mm", x)
            add_prop(servo_screw, "App::PropertyFloat", "STEPHoleCenterZ_mm", z)
            add_prop(servo_screw, "App::PropertyFloat", "HoleAxisAlignmentError_mm", 0.0)

# J2 supported 2:1 belt input.  Both F685 bearings straddle the driver pulley,
# so belt radial load returns through the bolted bridge rather than through the
# MG996R output bearing.
bridge_a = Part.makeCylinder(8, 5, App.Vector(J2_INPUT_X, 32, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(5.48, 5, App.Vector(J2_INPUT_X, 32, AXIS_Z), App.Vector(0, 1, 0))).cut(Part.makeCylinder(6.3, 1, App.Vector(J2_INPUT_X, 32, AXIS_Z), App.Vector(0, 1, 0)))
bridge_b = Part.makeCylinder(8, 5, App.Vector(J2_INPUT_X, 51, AXIS_Z), App.Vector(0, -1, 0)).cut(Part.makeCylinder(5.48, 5, App.Vector(J2_INPUT_X, 51, AXIS_Z), App.Vector(0, -1, 0))).cut(Part.makeCylinder(6.3, 1, App.Vector(J2_INPUT_X, 51, AXIS_Z), App.Vector(0, -1, 0)))
bridge = bridge_a.fuse(bridge_b)
bridge = bridge.fuse(Part.makeBox(8, 19, 4, App.Vector(J2_INPUT_X - 4, 32, AXIS_Z + 12)))
bridge = bridge.fuse(Part.makeBox(8, 5, 8, App.Vector(J2_INPUT_X - 4, 32, AXIS_Z + 6)))
bridge = bridge.fuse(Part.makeBox(8, 5, 8, App.Vector(J2_INPUT_X - 4, 46, AXIS_Z + 6)))
bridge = bridge.fuse(Part.makeBox(18, 5, 4, App.Vector(J2_INPUT_X - 9, 32, 69)))
bridge = bridge.fuse(Part.makeBox(18, 5, 4, App.Vector(J2_INPUT_X - 9, 46, 69))).removeSplitter()
bridge_obj = part("J2_INPUT_BEARING_BRIDGE", "J2 slotted dual-F685 input bridge", bridge, "PR-J2-IN-BRIDGE", "B1_TURNTABLE", "Fiberon PA12-CF10", "FDM; 10 perimeters; press-fit F685 seats 10.96 mm plus flange counterbores; +/-1 mm alignment slots", "C-J2-INPUT-SUPPORT", (0.25, 0.72, 0.42))
add_prop(bridge_obj, "App::PropertyString", "AdjustmentRange", "+/-1.0 mm along X; align coaxially with servo using printed datum jig")
bearing_y("F685_J2_INPUT_A", J2_INPUT_X, 32, AXIS_Z, "B1_TURNTABLE", "C-J2-INPUT-SUPPORT;C-J2-BELT", "F685ZZ")
bearing_y_reverse("F685_J2_INPUT_B", J2_INPUT_X, 51, AXIS_Z, "B1_TURNTABLE", "C-J2-INPUT-SUPPORT;C-J2-BELT", "F685ZZ")
j2_input_shaft = Part.makeCylinder(2.5, 40, App.Vector(J2_INPUT_X, 12, AXIS_Z), App.Vector(0, 1, 0))
part("J2_INPUT_SHAFT", "J2 5 mm supported input shaft with flats", j2_input_shaft, "SH-J2-IN", "B1_TURNTABLE", "Hardened steel shaft", "Purchased E-SFJ5; cut 40 mm; two 0.5 mm flats", "C-J2-HORN-COUPLER;C-J2-INPUT-SUPPORT;C-J2-BELT", (0.58, 0.60, 0.64))
j2_driver = timing_pulley_y(J2_INPUT_X, 37, AXIS_Z, J2_DRIVER_TEETH, J2_BELT_WIDTH)
driver_obj = part("J2_DRIVER_16T", "J2 printed 16T 3GT x 9 driver with split clamp", j2_driver, "PR-J2-P16", "B1_TURNTABLE", "PA12", "FDM; printed flat; tooth and split-clamp coupons required", "C-J2-BELT;C-J2-INPUT-SUPPORT", (0.92, 0.55, 0.16))
add_prop(driver_obj, "App::PropertyInteger", "ToothCount", J2_DRIVER_TEETH)
add_prop(driver_obj, "App::PropertyFloat", "Pitch_mm", J2_BELT_PITCH)

# Conservative non-penetrating belt solid: annular wrap envelopes joined by
# tangent bands.  Tooth engagement is recorded as metadata and validated by a
# physical coupon before manufacture approval.
def belt_ring(x, radius_inner):
    return Part.makeCylinder(radius_inner + 2.4, J2_BELT_WIDTH, App.Vector(x, 37, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(radius_inner, J2_BELT_WIDTH, App.Vector(x, 37, AXIS_Z), App.Vector(0, 1, 0)))


def belt_band(z_out, z_in, sign):
    thickness = 2.4 * sign
    points = [
        App.Vector(0, 37, z_out),
        App.Vector(J2_INPUT_X, 37, z_in),
        App.Vector(J2_INPUT_X, 37, z_in + thickness),
        App.Vector(0, 37, z_out + thickness),
        App.Vector(0, 37, z_out),
    ]
    return Part.Face(Part.makePolygon(points)).extrude(App.Vector(0, J2_BELT_WIDTH, 0))


belt = belt_ring(0, 15.5).fuse(belt_ring(J2_INPUT_X, 8.1))
belt = belt.fuse(belt_band(AXIS_Z + 15.5, AXIS_Z + 8.1, 1))
belt = belt.fuse(belt_band(AXIS_Z - 15.5, AXIS_Z - 8.1, -1))
belt_obj = part("J2_BELT_135_3GT_90", "MISUMI GBN1353GT-90 closed timing belt", belt, "BELT-J2-135-3GT-90", "B1_TURNTABLE", "Chloroprene rubber, fiberglass cord, nylon facing", "Purchased MISUMI GBN1353GT-90", "C-J2-BELT", (0.12, 0.12, 0.12), 3.04)
for prop_name, prop_value in (("Pitch_mm", 3.0), ("Width_mm", 9.0), ("PitchLength_mm", 135.0), ("SmallPulleyWrap_deg", 151.0323), ("EngagedTeeth", 6.7125), ("MaxTangentialLoad_N", 120.6895)):
    add_prop(belt_obj, "App::PropertyFloat", prop_name, prop_value)
try:
    belt_clearance = belt.makeOffsetShape(0.5, 0.05, False, False, 0, 0)
except Exception:
    belt_clearance = belt
doc.getObject("V8_R_J1_Turntable").Shape = doc.getObject("V8_R_J1_Turntable").Shape.cut(belt_clearance)
doc.getObject("V8_R_J1_Turntable").Shape = doc.getObject("V8_R_J1_Turntable").Shape.cut(Part.makeCylinder(15.8, 10, App.Vector(0, 36.5, AXIS_Z), App.Vector(0, 1, 0)))

# Four vertical M3 fasteners clamp the bridge feet to slotted deck pads.  The
# slots and servo-ear slots are set together with a removable coaxial jig.
for index, (x, y) in enumerate(((J2_INPUT_X - 6, 34.5), (J2_INPUT_X + 6, 34.5), (J2_INPUT_X - 6, 48.5), (J2_INPUT_X + 6, 48.5)), 1):
    doc.getObject("V8_R_J1_Turntable").Shape = doc.getObject("V8_R_J1_Turntable").Shape.cut(Part.makeCylinder(3, 4, App.Vector(x, y, 63)))
    bridge_obj.Shape = bridge_obj.Shape.cut(Part.makeCylinder(1.7, 14, App.Vector(x, y, 67)))
    insert_z(f"J2_BRIDGE_INS_{index}", x, y, 63, 4, "B1_TURNTABLE", "C-J2-INPUT-SUPPORT")
    screw_z(f"J2_BRIDGE_M3_{index}", x, y, 64, 12, "B1_TURNTABLE", "C-J2-INPUT-SUPPORT")

if MG996_HORN_DATA is not None:
    coupler = Part.makeCylinder(9, 4, App.Vector(J2_INPUT_X, 12.5, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.45, 4, App.Vector(J2_INPUT_X, 12.5, AXIS_Z), App.Vector(0, 1, 0)))
    coupler_obj = part("J2_HORN_SHAFT_COUPLER", "J2 measured-horn to 5 mm split-clamp flange", coupler, "PR-J2-HORN-COUPLER", "B1_TURNTABLE", "Fiberon PA12-CF10", "FDM; 10 perimeters; generated from verified horn-hole coordinates", "C-J2-HORN-COUPLER", (0.25, 0.72, 0.42))
    for index, hole in enumerate(MG996_HORN_DATA["holes"], 1):
        hx = J2_INPUT_X + float(hole["x_mm"])
        hz = AXIS_Z + float(hole["z_mm"])
        coupler_obj.Shape = coupler_obj.Shape.cut(Part.makeCylinder(1.7, 4, App.Vector(hx, 12.5, hz), App.Vector(0, 1, 0)))
        insert_y(f"J2_COUPLER_INS_{index}", hx, 15.5, hz, 4, "B1_TURNTABLE", "C-J2-HORN-COUPLER")
        screw_y(f"J2_COUPLER_M3_{index}", hx, 10.5, hz, 9, 1, "B1_TURNTABLE", "C-J2-HORN-COUPLER")

# J4 MG90S: two untouched 2.4 mm ear holes, mapped from local X=-8.55/19.15.
j4_mount = None
for z in (70.45, 98.15):
    boss = Part.makeCylinder(4, 4, App.Vector(230, -12.3, z), App.Vector(0, 1, 0))
    side_rail = Part.makeBox(4, 17.7, 6, App.Vector(216, -30, z - 3))
    crossbar = Part.makeBox(14, 4, 6, App.Vector(216, -12.3, z - 3))
    arm = side_rail.fuse(crossbar)
    j4_mount = boss.fuse(arm) if j4_mount is None else j4_mount.fuse(boss).fuse(arm)
j4_mount = j4_mount.cut(Part.makeCylinder(1.8, 4, App.Vector(230, -12.3, 70.45), App.Vector(0, 1, 0)))
j4_mount = j4_mount.cut(Part.makeCylinder(1.8, 4, App.Vector(230, -12.3, 98.15), App.Vector(0, 1, 0)))
j4_mount = j4_mount.fuse(Part.makeBox(4, 3, 32, App.Vector(216, -30, 69)))
j4_mount = j4_mount.cut(doc.getObject("J4_SERVO").Shape)
fa_l.Shape = fa_l.Shape.fuse(j4_mount).cut(doc.getObject("J4_SERVO").Shape)
add_prop(fa_l, "App::PropertyString", "J4IntegratedMount", "Single B-rep cradle; 0.4 mm case clearance; servo-ear seating only")
for iz, z in enumerate((70.45, 98.15), 1):
    insert_y(f"J4_SERVO_1_{iz}", 230, -12.3, z, 3, "B3_FOREARM", "C-J4-SERVO", "M2")
    servo_screw = screw_y(f"J4_SERVO_M2_1_{iz}", 230, -4.3, z, 8, -1, "B3_FOREARM", "C-J4-SERVO", "M2")
    add_prop(servo_screw, "App::PropertyFloat", "STEPHoleCenterX_mm", 230.0)
    add_prop(servo_screw, "App::PropertyFloat", "STEPHoleCenterZ_mm", z)
    add_prop(servo_screw, "App::PropertyFloat", "HoleAxisAlignmentError_mm", 0.0)

# J5 uses the same two MG90S holes after rotating their axes to global X.
j5_mount = None
for z in (70.45, 98.15):
    boss = Part.makeCylinder(4, 4, App.Vector(J5_X - 18.3, 0, z), App.Vector(1, 0, 0))
    arm = Part.makeBox(4, 18, 6, App.Vector(J5_X - 18.3, 0, z - 3))
    j5_mount = boss.fuse(arm) if j5_mount is None else j5_mount.fuse(boss).fuse(arm)
    j5_mount = j5_mount.cut(Part.makeCylinder(1.8, 4, App.Vector(J5_X - 18.3, 0, z), App.Vector(1, 0, 0)))
j5_mount = j5_mount.fuse(Part.makeBox(4, 4, 34, App.Vector(J5_X - 18.3, 14, 68.5)))
j5_mount = j5_mount.cut(doc.getObject("J5_SERVO").Shape)
wp_r.Shape = wp_r.Shape.fuse(j5_mount).cut(doc.getObject("J5_SERVO").Shape)
add_prop(wp_r, "App::PropertyString", "J5IntegratedMount", "Single B-rep cradle; 0.4 mm case clearance; servo-ear seating only")
for iz, z in enumerate((70.45, 98.15), 1):
    ins_shape = Part.makeCylinder(1.75, 3, App.Vector(J5_X - 17.3, 0, z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(1, 3, App.Vector(J5_X - 17.3, 0, z), App.Vector(1, 0, 0)))
    ins = part(f"J5_SERVO_{iz}", "M2 heat-set insert OD3.5 L3", ins_shape, f"INS-J5-SERVO-{iz}", "B4_WRIST_PITCH", "Brass heat-set insert", "Thermal press-fit after coupon calibration", "C-J5-SERVO", (0.84, 0.58, 0.18))
    add_prop(ins, "App::PropertyString", "InsertThread", "M2")
    add_prop(ins, "App::PropertyFloat", "InsertOD_mm", 3.5)
    add_prop(ins, "App::PropertyFloat", "InsertLength_mm", 3.0)
    sh = Part.makeCylinder(1, 8, App.Vector(J5_X - 10.9, 0, z), App.Vector(-1, 0, 0)).fuse(Part.makeCylinder(2, 1.5, App.Vector(J5_X - 9.4, 0, z), App.Vector(-1, 0, 0)))
    so = part(f"J5_SERVO_M2_{iz}", "M2x8 low-head servo screw", sh, f"SCR-J5-SERVO-{iz}", "B4_WRIST_PITCH", "Steel A2-70", "Purchased M2x8", "C-J5-SERVO", (0.55, 0.57, 0.60))
    for pn, pv, pt in (("FastenerSize", "M2", "App::PropertyString"), ("FastenerLength_mm", 8.0, "App::PropertyFloat"), ("ThreadEngagement_mm", 3.0, "App::PropertyFloat"), ("ToolAccessDirection", "+X", "App::PropertyString"), ("ToolClearance_mm", 10.0, "App::PropertyFloat"), ("ToolAccessStage", "Before J5 bearing housing closure", "App::PropertyString")):
        add_prop(so, pt, pn, pv)
    add_prop(so, "App::PropertyFloat", "STEPHoleCenterX_mm", J5_X - 18.3)
    add_prop(so, "App::PropertyFloat", "STEPHoleCenterZ_mm", z)
    add_prop(so, "App::PropertyFloat", "HoleAxisAlignmentError_mm", 0.0)

# Horn-to-link connections: two M3 screws and two OD6 x 4 heat-set inserts per pitch joint.
# These are the actual torque paths; the servo center screw only retains the stock horn on its spline.
active_specs = [(4, 230, 3.2, 1, 14, "B4_WRIST_PITCH", 15)]
if MG996_HORN_DATA is not None:
    active_specs.insert(0, (3, 115, -22, -1, -30, "B3_FOREARM", 12))
for j, xaxis, screw_start, direction, insert_y0, body, length in active_specs:
    if j == 4:
        boss = Part.makeBox(8, 5.8, 24, App.Vector(xaxis - 4, 8.2, AXIS_Z - 12))
        boss = boss.fuse(Part.makeCylinder(10, 5.8, App.Vector(xaxis, 8.2, AXIS_Z), App.Vector(0, 1, 0))).cut(Part.makeCylinder(2.6, 5.8, App.Vector(xaxis, 8.2, AXIS_Z), App.Vector(0, 1, 0)))
        part("J4_HORN_SPACER", "J4 STEP-horn receiver bridge", boss, "PR-HUB-J4", body, "Fiberon PA12-CF10", "FDM; 8 perimeters; flat receiver for MG90S STEP horn", "C-J4-ACTIVE", (0.12, 0.58, 0.80))
    hole_offsets = [(0.0, -6.5), (0.0, 6.5)] if j == 4 else [
        (float(hole["x_mm"]), float(hole["z_mm"])) for hole in MG996_HORN_DATA["holes"]
    ]
    for k, (dx, dz) in enumerate(hole_offsets, 1):
        hole_x = xaxis + dx
        hole_z = AXIS_Z + dz
        host = {2: doc.getObject("UPPER_ARM_R"), 3: doc.getObject("FOREARM_L"), 4: doc.getObject("WRIST_PITCH_R")}[j]
        host.Shape = host.Shape.cut(Part.makeCylinder(3, 4, App.Vector(hole_x, insert_y0, hole_z), App.Vector(0, 1, 0)))
        if j == 4:
            spacer_obj = doc.getObject("J4_HORN_SPACER")
            spacer_obj.Shape = spacer_obj.Shape.cut(Part.makeCylinder(1.7, 6, App.Vector(hole_x, 8, hole_z), App.Vector(0, 1, 0)))
            horn_obj = doc.getObject("J4_SERVO_HORN")
            horn_obj.Shape = horn_obj.Shape.cut(Part.makeCylinder(1.7, 15, App.Vector(hole_x, 2, hole_z), App.Vector(0, 1, 0)))
        insert_y(f"J{j}_HORN_{k}", hole_x, insert_y0, hole_z, 4, body, f"C-J{j}-ACTIVE")
        screw_y(f"J{j}_HORN_M3_{k}", hole_x, screw_start, hole_z, length, direction, body, f"C-J{j}-ACTIVE")

# J4 stock horn is retained on its spline by the actual center screw from the
# user-supplied MG90S assembly STEP.
j4_center = placed_shape(MG90_CENTER_SCREW_SOURCE, App.Vector(230, 6, AXIS_Z), MG90_TO_J4)
j4_center_obj = part("J4_HORN_CENTER_SCREW", "MG90S supplied horn center screw", j4_center, "SCR-J4-HORN-CENTER", "B3_FOREARM", "Steel servo screw", f"User STEP {MG90_SERVO_STEP}", "C-J4-ACTIVE", (0.50, 0.52, 0.56))
for pn, pv, pt in (("FastenerSize", "Servo-supplied", "App::PropertyString"), ("FastenerLength_mm", 5.75, "App::PropertyFloat"), ("ThreadEngagement_mm", 2.5, "App::PropertyFloat"), ("ToolAccessDirection", "-Y", "App::PropertyString"), ("ToolClearance_mm", 10.0, "App::PropertyFloat"), ("ToolAccessStage", "Before wrist receiver installation", "App::PropertyString")):
    add_prop(j4_center_obj, pt, pn, pv)

# Metadata used by automatic audit and MuJoCo exporter.
meta = doc.addObject("App::FeaturePython", "ENGINEERING_METADATA")
for name, value in {
    "DesignStatus": "IN_PROGRESS_NOT_COMPLETE",
    "Payload_g": 50.0,
    "Reach_mm": J5_X + 28.0,
    "MaxSpeed_deg_s": 60.0,
    "MaxAccel_deg_s2": 120.0,
    "EStopDecel_deg_s2": 600.0,
    "SupplyVoltage_V": 4.8,
    "J1Ratio": 6.0,
    "J2Ratio": J2_RATIO,
    "J2BeltEfficiency": J2_BELT_EFFICIENCY,
    "J2BeltPitch_mm": J2_BELT_PITCH,
    "J2BeltWidth_mm": J2_BELT_WIDTH,
    "J2BeltLength_mm": J2_BELT_LENGTH,
    "J2DriverTeeth": J2_DRIVER_TEETH,
    "J2DrivenTeeth": J2_DRIVEN_TEETH,
    "F695Used": 6,
    "F685Used": 7,
    "InsertNote": "M3 OD6 L4 qty100; M4 OD5 L3-8 qty30 each; both heat-set; inverse OD relation confirmed",
    "ServoGeometryNote": "All five servo bodies use unmodified user STEP B-reps; MG90S horn/center screw use user STEP; MG996R horn solids are omitted until two physical horns are measured and verified within 0.1 mm",
    "J2TransmissionNote": "Physical 16T/32T 3GTx9 belt path; supported 5 mm input shaft; two F685 input bearings; two F695 output bearings; no virtual coupling credited",
}.items():
    ptype = "App::PropertyString" if isinstance(value, str) else ("App::PropertyInteger" if isinstance(value, int) else "App::PropertyFloat")
    add_prop(meta, ptype, name, value, "Requirements")

# Complete tool-access metadata for purchased M2 fasteners created explicitly above.
for obj in doc.Objects:
    if obj.TypeId != "PartDesign::Feature" or not hasattr(obj, "PartID") or not obj.PartID.startswith("SCR-") or hasattr(obj, "FastenerSize"):
        continue
    add_prop(obj, "App::PropertyString", "FastenerSize", "M2")
    add_prop(obj, "App::PropertyFloat", "FastenerLength_mm", 7.0 if "J1_HORN" in obj.Name else 5.0)
    add_prop(obj, "App::PropertyFloat", "ThreadEngagement_mm", 0.0)
    add_prop(obj, "App::PropertyString", "ToolAccessDirection", "-Z" if "J1_HORN" in obj.Name else "-X")
    add_prop(obj, "App::PropertyFloat", "ToolClearance_mm", 10.0)
    add_prop(obj, "App::PropertyString", "ToolAccessStage", "Horn subassembly before servo installation")

doc.recompute()
doc.saveAs(OUT)
if "Gui" in globals() and Gui.activeDocument():
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
