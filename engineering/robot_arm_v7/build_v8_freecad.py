import math

import FreeCAD as App
import Part


OUT = "C:/Users/kohak/programs/robotarm/cad/RobotArmFinalV5/CompletedPreviewV5_2CradleAlignment/ROBOT_ARM_V8_MANUFACTURABLE.FCStd"
DENSITY = {"PA12_CF": 1.06, "PA12": 1.01, "STEEL": 7.85, "BRASS": 8.50}
AXIS_Z = 79.0


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


def screw_y(name, x, y0, z, length, direction, body, cid):
    sh = Part.makeCylinder(1.5, length, App.Vector(x, y0, z), App.Vector(0, direction, 0))
    head_start = y0 - 2 if direction > 0 else y0 + 2
    head = Part.makeCylinder(3.0, 2, App.Vector(x, head_start, z), App.Vector(0, direction, 0))
    obj = part(name, f"M3x{length:g} low-head screw", sh.fuse(head), f"SCR-{name}", body, "Steel A2-70", "Purchased", cid, (0.55, 0.57, 0.60))
    add_prop(obj, "App::PropertyString", "FastenerSize", "M3")
    add_prop(obj, "App::PropertyFloat", "FastenerLength_mm", float(length))
    add_prop(obj, "App::PropertyFloat", "ThreadEngagement_mm", 4.0)
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


def insert_y(name, x, y0, z, length, body, cid):
    shape = Part.makeCylinder(3, length, App.Vector(x, y0, z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(1.5, length, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    obj = part(name, "M3 heat-set insert OD6 L4", shape, f"INS-{name}", body, "Brass heat-set insert", "Thermal press-fit; coupon-calibrated hole", cid, (0.84, 0.58, 0.18))
    add_prop(obj, "App::PropertyString", "InsertThread", "M3")
    add_prop(obj, "App::PropertyFloat", "InsertOD_mm", 6.0)
    add_prop(obj, "App::PropertyFloat", "InsertLength_mm", float(length))
    return obj


def bearing_y(name, x, y0, z, body, cid, model="F695ZZ"):
    if model == "F695ZZ":
        od, width, flange, mass = 13.0, 4.0, 15.0, 2.84
    else:
        od, width, flange, mass = 11.0, 5.0, 12.5, 2.18
    ring = Part.makeCylinder(od / 2, width, App.Vector(x, y0, z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.5, width, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    fl = Part.makeCylinder(flange / 2, 1, App.Vector(x, y0, z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.5, 1, App.Vector(x, y0, z), App.Vector(0, 1, 0)))
    return part(name, model, ring.fuse(fl), f"BR-{name}", body, "Bearing steel, ZZ shields", f"Purchased NSK {model}", cid, (0.68, 0.72, 0.78), mass)


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
        sx, sy, sz, mass = 40.7, 34.0, 19.7, 55.0
    else:
        sx, sy, sz, mass = 22.8, 24.0, 12.2, 13.4
    # The case stays between the structural plates; only the output horn side changes.
    y0 = -22.0 if model == "MG996R" else -18.0
    x0 = x_axis - sx + 7.0
    housing = Part.makeBox(sx, sy, sz, App.Vector(x0, y0, z_axis - sz / 2))
    ear_length = sx + 12 if model == "MG996R" else sx + 6
    ears = Part.makeBox(ear_length, 3, 5, App.Vector(x0 - 6, y0 + sy / 2 - 1.5, z_axis - 2.5))
    housing = housing.fuse(ears)
    obj = part(name, f"TowerPro {model} assembly", housing, f"SER-{name}", body, f"TowerPro {model} purchased assembly", "Purchased; stock horn retained", cid, (0.16, 0.18, 0.22), mass)
    side_y = y0 + sy if output_side > 0 else y0
    horn_y = side_y if output_side > 0 else side_y - 2
    horn = Part.makeCylinder(10 if model == "MG996R" else 8, 2, App.Vector(x_axis, horn_y, z_axis), App.Vector(0, 1, 0))
    horn = horn.cut(Part.makeCylinder(1.6, 2, App.Vector(x_axis, horn_y, z_axis), App.Vector(0, 1, 0)))
    part(name + "_HORN", f"{model} stock horn", horn, f"HORN-{name}", body, "Servo-supplied reinforced polymer horn", "Purchased with servo; two holes drilled 3.2 mm", cid, (0.92, 0.92, 0.92), 1.5 if model == "MG996R" else 0.6)
    return obj, horn_y


# Base and compact J1. Gear geometry is copied from the validated V7 involute set.
base = Part.makeCylinder(44, 6).cut(Part.makeCylinder(2.25, 6, App.Vector(34, 0, 0)))
for a in (90, 180, 270):
    base = base.cut(Part.makeCylinder(2.25, 6, App.Vector(34 * math.cos(math.radians(a)), 34 * math.sin(math.radians(a)), 0)))
# Two integral pillars receive the J1 servo-ear inserts.
base = base.fuse(Part.makeCylinder(4, 22, App.Vector(-15, 0, 6))).fuse(Part.makeCylinder(4, 22, App.Vector(15, 0, 6)))
part("BASE_PLATE", "Base plate OD88 with J1 servo pillars", base, "PR-B01", "B0_BASE", "Fiberon PA12-CF10", "FDM; 8 perimeters; 35% gyroid", "C-BASE-01;C-J1-SERVO", (0.22, 0.55, 0.86))
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
        cheek_shape = Part.makeBox(64, 4, 38, App.Vector(-42, -28, 60)).cut(Part.makeCylinder(7.55, 4, App.Vector(0, -28, AXIS_Z), App.Vector(0, 1, 0)))
        shape = Part.makeCylinder(32, 6, App.Vector(0, 0, 63)).fuse(Part.makeBox(58, 48, 6, App.Vector(-29, -30, 63))).fuse(cheek_shape)
        cids = "C-J1-TRANSMISSION;C-J1-DECK;C-J2-SERVO;C-J2-PASSIVE"
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
    part("V8_" + name, compact_labels.get(name, src.Label + " V8"), shape, "PR-J1-" + name, body, mat, "FDM" if "PA12" in mat else "Purchased/cut", cids, src.ViewObject.ShapeColor)

# J1 MG90S is vertical and physically drives the sun through its stock horn and bolted printed hub.
j1_servo_shape = Part.makeBox(22.8, 12.2, 28, App.Vector(-11.4, -6.1, 6))
j1_servo_shape = j1_servo_shape.fuse(Part.makeBox(34, 4, 2, App.Vector(-17, -2, 27)))
part("J1_SERVO", "TowerPro MG90S J1 servo", j1_servo_shape, "SER-J1", "B0_BASE", "TowerPro MG90S purchased assembly", "Purchased; supplied horn and center screw", "C-J1-SERVO;C-J1-SUN-HORN", (0.16, 0.18, 0.22), 13.4)
j1_horn = Part.makeCylinder(8, 2, App.Vector(0, 0, 34)).cut(Part.makeCylinder(1.5, 2, App.Vector(0, 0, 34)))
part("J1_STOCK_HORN", "MG90S stock horn", j1_horn, "HORN-J1", "B0_BASE", "Servo-supplied reinforced polymer horn", "Purchased with servo; two holes drilled 3.2 mm", "C-J1-SUN-HORN", (0.92, 0.92, 0.92), 0.6)
for i, x in enumerate((-3, 3), 1):
    m2_hole = Part.makeCylinder(1.1, 8, App.Vector(x, 0, 32))
    doc.getObject("J1_STOCK_HORN").Shape = doc.getObject("J1_STOCK_HORN").Shape.cut(m2_hole)
    doc.getObject("V8_R_J1_SunGear").Shape = doc.getObject("V8_R_J1_SunGear").Shape.cut(m2_hole)
    m2_shank = Part.makeCylinder(1.0, 8, App.Vector(x, 0, 32))
    m2_head = Part.makeCylinder(2.0, 1.5, App.Vector(x, 0, 30.5))
    part(f"J1_HORN_M2_{i}", "M2x8 horn through-bolt", m2_shank.fuse(m2_head), f"SCR-J1-HORN-M2-{i}", "B1_TURNTABLE", "Steel A2-70", "Purchased M2x8 screw", "C-J1-SUN-HORN", (0.55, 0.57, 0.60))
    nut = Part.makeCylinder(2.1, 1.6, App.Vector(x, 0, 38.4))
    part(f"J1_HORN_NUT_M2_{i}", "M2 prevailing-torque nut", nut, f"NUT-J1-HORN-M2-{i}", "B1_TURNTABLE", "Steel locknut", "Purchased", "C-J1-SUN-HORN", (0.55, 0.57, 0.60))
for i, x in enumerate((-15, 15), 1):
    doc.getObject("BASE_PLATE").Shape = doc.getObject("BASE_PLATE").Shape.cut(Part.makeCylinder(3, 4, App.Vector(x, 0, 24)))
    doc.getObject("J1_SERVO").Shape = doc.getObject("J1_SERVO").Shape.cut(Part.makeCylinder(1.7, 8, App.Vector(x, 0, 24)))
    insert_z(f"J1_SERVO_{i}", x, 0, 24, 4, "B0_BASE", "C-J1-SERVO")
    screw_z(f"J1_SERVO_M3_{i}", x, 0, 24, 8, "B0_BASE", "C-J1-SERVO")

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

# Shoulder deck and passive cheek are integral with the turntable to remove four joints and two interfaces.
bearing_y("F695_J2", 0, -28, AXIS_Z, "B1_TURNTABLE", "C-J2-PASSIVE")

# Real servos and structural links in the fully extended inspection pose.
servo_y("J2_SERVO", 0, AXIS_Z, "B1_TURNTABLE", "MG996R", 1, "C-J2-SERVO;C-J2-ACTIVE")
ua_l = truss_plate("UPPER_ARM_L", 0, 115, -32, AXIS_Z, "PR-L01", "B2_UPPER_ARM", "C-J2-PASSIVE;C-J3-PASSIVE", (0.20, 0.76, 0.36))
ua_r = truss_plate("UPPER_ARM_R", 0, 115, 14, AXIS_Z, "PR-L02", "B2_UPPER_ARM", "C-J2-ACTIVE;C-J3-SERVO;C-J3-PASSIVE", (0.20, 0.76, 0.36))
servo_y("J3_SERVO", 115, AXIS_Z, "B2_UPPER_ARM", "MG996R", -1, "C-J3-SERVO;C-J3-ACTIVE")
fa_l = truss_plate("FOREARM_L", 115, 230, -28, AXIS_Z, "PR-L03", "B3_FOREARM", "C-J3-ACTIVE;C-J4-PASSIVE", (0.10, 0.64, 0.30))
fa_r = truss_plate("FOREARM_R", 115, 230, 22, AXIS_Z, "PR-L04", "B3_FOREARM", "C-J3-PASSIVE;C-J4-SERVO", (0.10, 0.64, 0.30))
servo_y("J4_SERVO", 230, AXIS_Z, "B3_FOREARM", "MG90S", 1, "C-J4-SERVO;C-J4-ACTIVE")

# Bearing seats are real 13.1 mm press-fit bores with a 15.1 mm flange counterbore.
ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(6.55, 3, App.Vector(115, 14, AXIS_Z), App.Vector(0, 1, 0)))
ua_r.Shape = ua_r.Shape.cut(Part.makeCylinder(7.55, 1, App.Vector(115, 14, AXIS_Z), App.Vector(0, 1, 0)))
fa_l.Shape = fa_l.Shape.cut(Part.makeCylinder(6.55, 3, App.Vector(230, -28, AXIS_Z), App.Vector(0, 1, 0)))
fa_l.Shape = fa_l.Shape.cut(Part.makeCylinder(7.55, 1, App.Vector(230, -28, AXIS_Z), App.Vector(0, 1, 0)))

# Passive support bearings, short keyed/flat stub shafts, collars; no shaft passes through a servo.
bearing_y("F695_J3", 115, 14, AXIS_Z, "B2_UPPER_ARM", "C-J3-PASSIVE")
bearing_y("F695_J4", 230, -28, AXIS_Z, "B3_FOREARM", "C-J4-PASSIVE")
for j, x, y0, body in ((2, 0, -35, "B2_UPPER_ARM"), (3, 115, 13, "B3_FOREARM"), (4, 230, -35, "B4_WRIST_PITCH")):
    shaft = Part.makeCylinder(2.5, 12, App.Vector(x, y0, AXIS_Z), App.Vector(0, 1, 0))
    part(f"J{j}_PASSIVE_STUB", f"J{j} 5 mm passive stub with machined flat", shaft, f"SH-J{j}-P", body, "Hardened steel shaft", "Purchased 5 mm shaft; cut, deburr, mill 0.5 mm flat", f"C-J{j}-PASSIVE", (0.58, 0.60, 0.64))
    collar_y = y0 - 2 if j in (2, 4) else 25
    radial_hole = Part.makeCylinder(1.5, 4, App.Vector(x + 5, collar_y + 2.5, AXIS_Z), App.Vector(-1, 0, 0))
    collar = Part.makeCylinder(5, 5, App.Vector(x, collar_y, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.55, 5, App.Vector(x, collar_y, AXIS_Z), App.Vector(0, 1, 0))).cut(radial_hole)
    part(f"J{j}_COLLAR", f"J{j} CL05M 5 mm set-screw collar", collar, f"COL-J{j}", body, "Zinc-plated steel collar", "Purchased Motionco CL05M; 5 ID x 10 OD x 5 W", f"C-J{j}-RETENTION;C-J{j}-PASSIVE", (0.58, 0.60, 0.64))
    part(f"J{j}_COLLAR_SETSCREW", "CL05M included M3 set screw", radial_hole, f"SET-J{j}", body, "Steel", "Included with Motionco CL05M", f"C-J{j}-RETENTION;C-J{j}-PASSIVE", (0.48, 0.50, 0.54))

# Wrist pitch carrier and coaxial-near roll stack.
wp_l = truss_plate("WRIST_PITCH_L", 230, 260, -32, AXIS_Z, "PR-W01", "B4_WRIST_PITCH", "C-J4-PASSIVE;C-J5-HOUSING", (0.12, 0.58, 0.80))
wp_r = truss_plate("WRIST_PITCH_R", 230, 260, 14, AXIS_Z, "PR-W02", "B4_WRIST_PITCH", "C-J4-ACTIVE;C-J5-HOUSING", (0.12, 0.58, 0.80))
# J5 servo axis X, output at x=260; body lies inside the 30 mm wrist carrier.
j5_body = Part.makeBox(22, 12.2, 22.8, App.Vector(238, -6.1, 67.6))
part("J5_SERVO", "TowerPro MG90S roll servo", j5_body, "SER-J5", "B4_WRIST_PITCH", "TowerPro MG90S purchased assembly", "Purchased; stock horn retained", "C-J5-SERVO;C-J5-ACTIVE", (0.16, 0.18, 0.22), 13.4)
housing = Part.makeBox(18, 49, 30, App.Vector(260, -32, 64))
housing = housing.cut(Part.makeCylinder(8.2, 5, App.Vector(260, 0, AXIS_Z), App.Vector(1, 0, 0)))
housing = housing.cut(Part.makeCylinder(6.3, 13, App.Vector(265, 0, AXIS_Z), App.Vector(1, 0, 0)))
part("J5_BEARING_HOUSING", "J5 dual-bearing housing", housing, "PR-W03", "B4_WRIST_PITCH", "Fiberon PA12-CF10", "FDM; 8 perimeters; bearing bores reamed", "C-J5-HOUSING;C-J5-BRG", (0.12, 0.58, 0.80))
housing_obj = doc.getObject("J5_BEARING_HOUSING")
housing_obj.Shape = housing_obj.Shape.cut(wp_l.Shape).cut(wp_r.Shape)
# Four topologically real M3x16 axial screws join the two wrist plates to the bearing housing.
for iy, y in enumerate((-30.5, 15.5), 1):
    for iz, dz in enumerate((-5, 5), 1):
        z = AXIS_Z + dz
        clearance = Part.makeCylinder(1.7, 12, App.Vector(248, y, z), App.Vector(1, 0, 0))
        (wp_l if y < 0 else wp_r).Shape = (wp_l if y < 0 else wp_r).Shape.cut(clearance)
        housing_obj.Shape = housing_obj.Shape.cut(Part.makeCylinder(3, 4, App.Vector(260, y, z), App.Vector(1, 0, 0)))
        ins_shape = Part.makeCylinder(3, 4, App.Vector(260, y, z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(1.5, 4, App.Vector(260, y, z), App.Vector(1, 0, 0)))
        ins_obj = part(f"J5_HOUSING_INS_{iy}_{iz}", "M3 heat-set insert OD6 L4", ins_shape, f"INS-J5-H-{iy}-{iz}", "B4_WRIST_PITCH", "Brass heat-set insert", "Thermal press-fit", "C-J5-HOUSING", (0.84, 0.58, 0.18))
        add_prop(ins_obj, "App::PropertyString", "InsertThread", "M3")
        add_prop(ins_obj, "App::PropertyFloat", "InsertOD_mm", 6.0)
        add_prop(ins_obj, "App::PropertyFloat", "InsertLength_mm", 4.0)
        sh = Part.makeCylinder(1.5, 16, App.Vector(248, y, z), App.Vector(1, 0, 0)).fuse(Part.makeCylinder(3, 2, App.Vector(246, y, z), App.Vector(1, 0, 0)))
        so = part(f"J5_HOUSING_M3_{iy}_{iz}", "M3x16 low-head housing screw", sh, f"SCR-J5-H-{iy}-{iz}", "B4_WRIST_PITCH", "Steel A2-70", "Purchased", "C-J5-HOUSING", (0.55, 0.57, 0.60))
        add_prop(so, "App::PropertyString", "FastenerSize", "M3")
        add_prop(so, "App::PropertyFloat", "FastenerLength_mm", 16.0)
        add_prop(so, "App::PropertyFloat", "ThreadEngagement_mm", 4.0)
        add_prop(so, "App::PropertyString", "ToolAccessDirection", "-X")
        add_prop(so, "App::PropertyFloat", "ToolClearance_mm", 10.0)
        add_prop(so, "App::PropertyString", "ToolAccessStage", "Install before gripper cradle")
bearing_x("F685_J5_A", 265, 0, AXIS_Z, "B4_WRIST_PITCH", "C-J5-BRG")
bearing_x("F685_J5_B", 273, 0, AXIS_Z, "B4_WRIST_PITCH", "C-J5-BRG")
j5shaft = Part.makeCylinder(2.5, 28, App.Vector(260, 0, AXIS_Z), App.Vector(1, 0, 0))
part("J5_OUTPUT_SHAFT", "J5 5 mm output shaft", j5shaft, "SH-J5", "B5_TOOL", "Hardened steel shaft", "Purchased 5 mm shaft; cut and deburr", "C-J5-ACTIVE;C-J5-BRG;C-J5-RETENTION;C-J5-TOOL", (0.58, 0.60, 0.64))
# Stock horn and compact bolted adapter are contained ahead of the first bearing.
j5_horn = Part.makeCylinder(7, 1.5, App.Vector(260, 0, AXIS_Z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(1.5, 1.5, App.Vector(260, 0, AXIS_Z), App.Vector(1, 0, 0)))
part("J5_STOCK_HORN", "MG90S J5 stock horn", j5_horn, "HORN-J5", "B4_WRIST_PITCH", "Servo-supplied reinforced polymer horn", "Purchased with servo", "C-J5-ACTIVE", (0.92, 0.92, 0.92), 0.6)
j5_adapter = Part.makeCylinder(7.5, 3.5, App.Vector(261.5, 0, AXIS_Z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(2.5, 3.5, App.Vector(261.5, 0, AXIS_Z), App.Vector(1, 0, 0)))
part("J5_HORN_SHAFT_ADAPTER", "J5 horn-to-5mm shaft adapter", j5_adapter, "PR-HUB-J5", "B5_TOOL", "Fiberon PA12-CF10", "FDM; 10 perimeters; ream 5H8", "C-J5-ACTIVE", (0.88, 0.48, 0.12))
for i, y in enumerate((-3, 3), 1):
    hole = Part.makeCylinder(1.1, 5, App.Vector(260, y, AXIS_Z), App.Vector(1, 0, 0))
    doc.getObject("J5_STOCK_HORN").Shape = doc.getObject("J5_STOCK_HORN").Shape.cut(hole)
    doc.getObject("J5_HORN_SHAFT_ADAPTER").Shape = doc.getObject("J5_HORN_SHAFT_ADAPTER").Shape.cut(hole)
    bolt = Part.makeCylinder(1, 5, App.Vector(260, y, AXIS_Z), App.Vector(1, 0, 0)).fuse(Part.makeCylinder(2, 1.5, App.Vector(258.5, y, AXIS_Z), App.Vector(1, 0, 0)))
    part(f"J5_HORN_M2_{i}", "M2x5 horn adapter bolt", bolt, f"SCR-J5-HORN-M2-{i}", "B5_TOOL", "Steel A2-70", "Purchased M2x5 screw + locknut", "C-J5-ACTIVE", (0.55, 0.57, 0.60))
    nut = Part.makeCylinder(2.1, 1.5, App.Vector(263.5, y, AXIS_Z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(1, 1.5, App.Vector(263.5, y, AXIS_Z), App.Vector(1, 0, 0)))
    part(f"J5_HORN_NUT_M2_{i}", "M2 prevailing-torque nut", nut, f"NUT-J5-HORN-M2-{i}", "B5_TOOL", "Steel locknut", "Purchased", "C-J5-ACTIVE", (0.55, 0.57, 0.60))
j5_set_hole = Part.makeCylinder(1.5, 4, App.Vector(280.5, 0, AXIS_Z + 5), App.Vector(0, 0, -1))
j5_collar = Part.makeCylinder(5, 5, App.Vector(278, 0, AXIS_Z), App.Vector(1, 0, 0)).cut(Part.makeCylinder(2.55, 5, App.Vector(278, 0, AXIS_Z), App.Vector(1, 0, 0))).cut(j5_set_hole)
part("J5_OUTER_COLLAR", "J5 CL05M 5 mm set-screw collar", j5_collar, "COL-J5", "B5_TOOL", "Zinc-plated steel collar", "Purchased Motionco CL05M; 5 ID x 10 OD x 5 W", "C-J5-RETENTION", (0.58, 0.60, 0.64))
part("J5_COLLAR_SETSCREW", "CL05M included M3 set screw", j5_set_hole, "SET-J5", "B5_TOOL", "Steel", "Included with Motionco CL05M", "C-J5-RETENTION", (0.48, 0.50, 0.54))

# Compact printed gripper proxy with real M3 bolted palm; payload reference at x=288.
palm = Part.makeBox(5, 34, 26, App.Vector(283, -17, 66))
palm = palm.fuse(Part.makeCylinder(7, 5, App.Vector(283, 0, AXIS_Z), App.Vector(1, 0, 0)))
palm = palm.cut(Part.makeCylinder(2.55, 5, App.Vector(283, 0, AXIS_Z), App.Vector(1, 0, 0)))
palm = palm.cut(Part.makeBox(5, 1, 8, App.Vector(283, -0.5, AXIS_Z)))
palm = palm.cut(Part.makeCylinder(1.7, 11, App.Vector(285.5, -8, AXIS_Z + 5), App.Vector(0, 1, 0)))
palm = palm.cut(Part.makeCylinder(3, 4, App.Vector(285.5, 3, AXIS_Z + 5), App.Vector(0, 1, 0)))
palm = palm.cut(Part.makeCylinder(1.7, 5, App.Vector(283, -10, 73), App.Vector(1, 0, 0)))
palm = palm.cut(Part.makeCylinder(1.7, 5, App.Vector(283, 10, 85), App.Vector(1, 0, 0)))
finger_l = Part.makeBox(5, 4, 34, App.Vector(283, -17, 89))
finger_r = Part.makeBox(5, 4, 34, App.Vector(283, 13, 89))
part("GRIPPER_CRADLE", "One-piece compact gripper cradle", palm.fuse(finger_l).fuse(finger_r), "PR-E01", "B5_TOOL", "Fiberon PA12-CF10", "FDM; 6 perimeters; one-piece cradle", "C-TOOL-01;C-J5-TOOL", (0.88, 0.48, 0.12))
insert_y("J5_TOOL_CLAMP", 285.5, 3, AXIS_Z + 5, 4, "B5_TOOL", "C-J5-TOOL")
screw_y("J5_TOOL_CLAMP_M3", 285.5, -8, AXIS_Z + 5, 15, 1, "B5_TOOL", "C-J5-TOOL")

# Servo mounting uses real transverse through-bolts, printed compression spacers,
# and M3 prevailing-torque nuts. No floating insert or screw passes through a servo body.
servo_mounts = {
    2: {"xs": (-38, 16), "dz": 5, "host": "V8_R_J1_Turntable", "servo": "J2_SERVO", "spacer_y": -24, "spacer_l": 2, "lug_y": -22, "start": -26, "length": 14, "nut_y": -17, "body": "B1_TURNTABLE"},
    3: {"xs": (75,), "dz": 5, "host": "UPPER_ARM_L", "servo": "J3_SERVO", "spacer_y": -29, "spacer_l": 7, "lug_y": -22, "start": -32, "length": 19, "nut_y": -17, "body": "B2_UPPER_ARM"},
    4: {"xs": (208,), "dz": 5, "host": "FOREARM_L", "servo": "J4_SERVO", "spacer_y": -25, "spacer_l": 7, "lug_y": -18, "start": -28, "length": 19, "nut_y": -13, "body": "B3_FOREARM"},
}
for j, spec in servo_mounts.items():
    host = doc.getObject(spec["host"])
    servo = doc.getObject(spec["servo"])
    for ix, x in enumerate(spec["xs"], 1):
        for iz, dz in enumerate((-spec["dz"], spec["dz"]), 1):
            z = AXIS_Z + dz
            clearance = Part.makeCylinder(1.7, spec["length"], App.Vector(x, spec["start"], z), App.Vector(0, 1, 0))
            host.Shape = host.Shape.cut(clearance)
            lug = Part.makeCylinder(4, 5, App.Vector(x, spec["lug_y"], z), App.Vector(0, 1, 0))
            servo.Shape = servo.Shape.fuse(lug).cut(clearance)
            spacer = Part.makeCylinder(3.5, spec["spacer_l"], App.Vector(x, spec["spacer_y"], z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(1.7, spec["spacer_l"], App.Vector(x, spec["spacer_y"], z), App.Vector(0, 1, 0)))
            part(f"J{j}_SERVO_SPACER_{ix}_{iz}", f"J{j} servo compression spacer", spacer, f"SP-J{j}-{ix}-{iz}", spec["body"], "Fiberon PA12-CF10", "FDM; 100% infill", f"C-J{j}-SERVO", (0.25, 0.72, 0.42))
            screw_y(f"J{j}_SERVO_M3_{ix}_{iz}", x, spec["start"], z, spec["length"], 1, spec["body"], f"C-J{j}-SERVO")
            nut = Part.makeCylinder(3.2, 4, App.Vector(x, spec["nut_y"], z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(1.5, 4, App.Vector(x, spec["nut_y"], z), App.Vector(0, 1, 0)))
            part(f"J{j}_SERVO_NUT_{ix}_{iz}", "M3 prevailing-torque nut", nut, f"NUT-J{j}-{ix}-{iz}", spec["body"], "Steel locknut", "Purchased DIN 985", f"C-J{j}-SERVO", (0.55, 0.57, 0.60))

# Horn-to-link connections: two M3 screws and two OD6 x 4 heat-set inserts per pitch joint.
# These are the actual torque paths; the servo center screw only retains the stock horn on its spline.
active_specs = [
    (2, 0, 12, 1, 14, "B2_UPPER_ARM", 8),
    (3, 115, -22, -1, -28, "B3_FOREARM", 6),
    (4, 230, 6, 1, 12, "B4_WRIST_PITCH", 12),
]
for j, xaxis, screw_start, direction, insert_y0, body, length in active_specs:
    if j == 4:
        boss = Part.makeCylinder(10, 6, App.Vector(xaxis, 8, AXIS_Z), App.Vector(0, 1, 0)).cut(Part.makeCylinder(2.6, 6, App.Vector(xaxis, 8, AXIS_Z), App.Vector(0, 1, 0)))
        part("J4_HORN_SPACER", "J4 horn spacer boss", boss, "PR-HUB-J4", body, "Fiberon PA12-CF10", "FDM; 8 perimeters", "C-J4-ACTIVE", (0.12, 0.58, 0.80))
    for k, dx in enumerate((-5, 5), 1):
        host = {2: doc.getObject("UPPER_ARM_R"), 3: doc.getObject("FOREARM_L"), 4: doc.getObject("WRIST_PITCH_R")}[j]
        host.Shape = host.Shape.cut(Part.makeCylinder(3, 4, App.Vector(xaxis + dx, insert_y0, AXIS_Z), App.Vector(0, 1, 0)))
        if j == 4:
            spacer_obj = doc.getObject("J4_HORN_SPACER")
            spacer_obj.Shape = spacer_obj.Shape.cut(Part.makeCylinder(1.7, 6, App.Vector(xaxis + dx, 8, AXIS_Z), App.Vector(0, 1, 0)))
        insert_y(f"J{j}_HORN_{k}", xaxis + dx, insert_y0, AXIS_Z, 4, body, f"C-J{j}-ACTIVE")
        screw_y(f"J{j}_HORN_M3_{k}", xaxis + dx, screw_start, AXIS_Z, length, direction, body, f"C-J{j}-ACTIVE")

# Metadata used by automatic audit and MuJoCo exporter.
meta = doc.addObject("App::FeaturePython", "ENGINEERING_METADATA")
for name, value in {
    "DesignStatus": "IN_PROGRESS_NOT_COMPLETE",
    "Payload_g": 50.0,
    "Reach_mm": 288.0,
    "MaxSpeed_deg_s": 60.0,
    "MaxAccel_deg_s2": 120.0,
    "EStopDecel_deg_s2": 600.0,
    "SupplyVoltage_V": 4.8,
    "J1Ratio": 6.0,
    "F695Used": 5,
    "F685Used": 5,
    "InsertNote": "M3 OD6 L4 qty100; M4 OD5 L3-8 qty30 each; both heat-set; inverse OD relation confirmed",
}.items():
    ptype = "App::PropertyString" if isinstance(value, str) else ("App::PropertyInteger" if isinstance(value, int) else "App::PropertyFloat")
    add_prop(meta, ptype, name, value, "Requirements")

# Complete tool-access metadata for purchased M2 fasteners created explicitly above.
for obj in doc.Objects:
    if obj.TypeId != "PartDesign::Feature" or not hasattr(obj, "PartID") or not obj.PartID.startswith("SCR-") or hasattr(obj, "FastenerSize"):
        continue
    add_prop(obj, "App::PropertyString", "FastenerSize", "M2")
    add_prop(obj, "App::PropertyFloat", "FastenerLength_mm", 8.0 if "J1_HORN" in obj.Name else 5.0)
    add_prop(obj, "App::PropertyFloat", "ThreadEngagement_mm", 0.0)
    add_prop(obj, "App::PropertyString", "ToolAccessDirection", "-Z" if "J1_HORN" in obj.Name else "-X")
    add_prop(obj, "App::PropertyFloat", "ToolClearance_mm", 10.0)
    add_prop(obj, "App::PropertyString", "ToolAccessStage", "Horn subassembly before servo installation")

doc.recompute()
doc.saveAs(OUT)
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
