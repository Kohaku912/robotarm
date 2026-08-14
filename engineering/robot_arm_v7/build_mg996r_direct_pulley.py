"""Build a hornless MG996R direct-spline 16T 3GT prototype pulley.

The female socket is derived from the user-supplied MG996R STEP B-rep.  This
is a fit/load prototype, not a released arm component: the physical servo
spline, center thread and printed-tooth coupon still require verification.
"""

from pathlib import Path
import math

import FreeCAD as App
import MeshPart
import Part


ROOT = Path("C:/Users/kohak/programs/robotarm")
OUT = ROOT / "engineering/robot_arm_v7/direct_spline_pulley"
SERVO_STEP = ROOT / "vendor/servo_cad/MG996R_SERVO.step"
FCSTD = OUT / "MG996R_DIRECT_16T_3GT_PROTOTYPE.FCStd"
PULLEY_STL = OUT / "MG996R_DIRECT_16T_3GT_PULLEY.stl"
COUPON_STL = OUT / "MG996R_SPLINE_CLEARANCE_COUPON_005_010_015.stl"
PULLEY_STEP = OUT / "MG996R_DIRECT_16T_3GT_PULLEY.step"

PITCH_MM = 3.0
TEETH = 16
BELT_WIDTH_MM = 9.0
SOCKET_CLEARANCE_MM = 0.10
SPLINE_AXIS_X = 10.0
SPLINE_AXIS_Z = -10.0
SPLINE_BASE_Y = 40.7
SPLINE_TOP_Y = 47.6
SPLINE_REFERENCE_RADIUS_MM = 3.592015


def add_string(obj, name: str, value: str) -> None:
    obj.addProperty("App::PropertyString", name)
    setattr(obj, name, value)


def source_spline_print_frame(source: Part.Shape, clearance_mm: float) -> Part.Shape:
    """Extract the STEP output spline and rotate it to a Z-axis print frame."""
    capture = Part.makeCylinder(
        4.15,
        SPLINE_TOP_Y - SPLINE_BASE_Y,
        App.Vector(SPLINE_AXIS_X, SPLINE_BASE_Y, SPLINE_AXIS_Z),
        App.Vector(0, 1, 0),
    )
    male = source.common(capture)
    if male.isNull() or not male.Solids:
        raise RuntimeError("MG996R STEP spline extraction produced no solid")

    # X'=X-10, Y'=-(Z+10), Z'=Y-40.7.  This is a proper rotation
    # (determinant +1), with the socket entrance on the print-bed side.
    orient = App.Matrix()
    orient.A11, orient.A12, orient.A13, orient.A14 = 1, 0, 0, -SPLINE_AXIS_X
    orient.A21, orient.A22, orient.A23, orient.A24 = 0, 0, -1, SPLINE_AXIS_Z
    orient.A31, orient.A32, orient.A33, orient.A34 = 0, 1, 0, -SPLINE_BASE_Y
    male = male.transformGeometry(orient)

    # Radial scale provides a controlled FDM fit allowance without changing
    # engagement depth.  The exact tooth count/profile remains that of STEP.
    radial_scale = 1.0 + clearance_mm / SPLINE_REFERENCE_RADIUS_MM
    grow = App.Matrix()
    grow.A11 = radial_scale
    grow.A22 = radial_scale
    grow.A33 = 1.0
    return male.transformGeometry(grow)


def source_servo_assembly_frame(source: Part.Shape) -> Part.Shape:
    """Rotate the complete servo so its output tip is Z=0 and axis is +Z."""
    orient = App.Matrix()
    orient.A11, orient.A12, orient.A13, orient.A14 = 1, 0, 0, -SPLINE_AXIS_X
    orient.A21, orient.A22, orient.A23, orient.A24 = 0, 0, -1, SPLINE_AXIS_Z
    orient.A31, orient.A32, orient.A33, orient.A34 = 0, 1, 0, -SPLINE_TOP_Y
    return source.transformGeometry(orient)


def timing_pulley(socket_tool: Part.Shape) -> Part.Shape:
    pitch_radius = TEETH * PITCH_MM / (2.0 * math.pi)
    root_radius = pitch_radius - 1.14
    track_z = 3.0
    core = Part.makeCylinder(root_radius, BELT_WIDTH_MM, App.Vector(0, 0, track_z))
    teeth = []
    for index in range(TEETH):
        angle = 2.0 * math.pi * index / TEETH
        radius = root_radius + 1.10 / 2.0 - 0.20
        cx, cy = radius * math.cos(angle), radius * math.sin(angle)
        tooth = Part.makeBox(1.10, 0.61, BELT_WIDTH_MM, App.Vector(-0.55, -0.305, track_z))
        tooth.rotate(App.Vector(), App.Vector(0, 0, 1), math.degrees(angle))
        tooth.translate(App.Vector(cx, cy, 0))
        teeth.append(tooth)

    toothed_track = core.multiFuse(teeth).removeSplitter()
    hub = Part.makeCylinder(6.50, 13.0)
    lower_flange = Part.makeCylinder(8.60, 1.0, App.Vector(0, 0, 2.0))
    upper_flange = Part.makeCylinder(8.60, 1.0, App.Vector(0, 0, 12.0))
    blank = hub.fuse(toothed_track).fuse(lower_flange).fuse(upper_flange).removeSplitter()

    # M3 user-stock screw: 3.3 mm through clearance, head OD6/H2 with
    # 0.2 mm radial/axial tool allowance.  The socket is open from Z=0.
    screw_clearance = Part.makeCylinder(1.65, 13.0)
    head_counterbore = Part.makeCylinder(3.20, 2.20, App.Vector(0, 0, 10.8))
    return blank.cut(socket_tool.fuse(screw_clearance).fuse(head_counterbore)).removeSplitter()


def clearance_coupon(source: Part.Shape) -> Part.Shape:
    clearances = (0.05, 0.10, 0.15)
    plate = Part.makeBox(48.0, 18.0, 3.0, App.Vector(-24.0, -9.0, 0.0))
    # An asymmetric corner notch identifies the 0.05 mm end after printing.
    index_notch = Part.makeBox(4.0, 4.0, 3.0, App.Vector(-24.0, -9.0, 0.0))
    shape = plate.cut(index_notch)
    for x, clearance in zip((-16.0, 0.0, 16.0), clearances):
        boss = Part.makeCylinder(6.0, 7.2, App.Vector(x, 0, 0))
        tool = source_spline_print_frame(source, clearance)
        tool.translate(App.Vector(x, 0, 0))
        bore = Part.makeCylinder(1.65, 7.2, App.Vector(x, 0, 0))
        shape = shape.fuse(boss).cut(tool.fuse(bore))
    return shape.removeSplitter()


def export_stl(shape: Part.Shape, path: Path) -> None:
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=0.035,
        AngularDeflection=0.10,
        Relative=False,
    )
    mesh.write(str(path))


OUT.mkdir(parents=True, exist_ok=True)
source = Part.Shape()
source.read(str(SERVO_STEP))
socket = source_spline_print_frame(source, SOCKET_CLEARANCE_MM)
pulley = timing_pulley(socket)
coupon = clearance_coupon(source)

if pulley.isNull() or len(pulley.Solids) != 1 or not pulley.isValid():
    raise RuntimeError("Direct pulley is not one valid connected solid")
if coupon.isNull() or len(coupon.Solids) != 1 or not coupon.isValid():
    raise RuntimeError("Spline coupon is not one valid connected solid")

doc = App.newDocument("MG996R_DIRECT_16T_3GT_PROTOTYPE")
pulley_obj = doc.addObject("PartDesign::Feature", "DIRECT_16T_3GT_PULLEY")
pulley_obj.Label = "MG996R direct-spline 16T 3GT pulley — prototype"
pulley_obj.Shape = pulley
for name, value in {
    "DesignStatus": "PROTOTYPE_NOT_LOAD_APPROVED",
    "GeometrySource": str(SERVO_STEP),
    "ConnectionMethod": "STEP-derived spline socket plus central M3 screw; no horn",
    "Material": "Fiberon PA12-CF10",
    "ManufacturingMethod": "FDM; axis Z; 0.15 mm layers; 8 perimeters; 100% local infill",
    "BeltSpecification": "16T, 3GT pitch 3 mm, belt width 9 mm",
    "SocketClearance": "0.10 mm radial from STEP spline",
    "Fastener": "M3x8 or M3x10, head OD6 H2; verify center thread before installation",
}.items():
    add_string(pulley_obj, name, value)

coupon_obj = doc.addObject("PartDesign::Feature", "SPLINE_CLEARANCE_COUPON")
coupon_obj.Label = "MG996R STEP-spline fit coupon 0.05 / 0.10 / 0.15 mm"
coupon_obj.Shape = coupon
coupon_obj.Placement.Base = App.Vector(28, 0, 0)
add_string(coupon_obj, "DesignStatus", "FIT_TEST_ONLY")
add_string(coupon_obj, "TestOrder", "Try 0.15 first, then 0.10, then 0.05; do not force onto servo")

assembly_x = -40.0
servo_assembly = source_servo_assembly_frame(source)
servo_assembly.translate(App.Vector(assembly_x, 0, 0))
reference = doc.addObject("PartDesign::Feature", "MG996R_ASSEMBLY_REFERENCE")
reference.Label = "User MG996R STEP — axis-aligned assembly reference"
reference.Shape = servo_assembly
reference.Visibility = False
add_string(reference, "GeometrySource", str(SERVO_STEP))

installed_shape = pulley.copy()
installed_shape.translate(App.Vector(assembly_x, 0, -(SPLINE_TOP_Y - SPLINE_BASE_Y)))
installed = doc.addObject("PartDesign::Feature", "DIRECT_PULLEY_INSTALLED_REFERENCE")
installed.Label = "Direct pulley installed on STEP spline — reference"
installed.Shape = installed_shape
installed.Visibility = False
add_string(installed, "ConnectionID", "C-MG996-DIRECT-SPLINE")

# User-stock M3x8, head OD6/H2.  The shaft enters the STEP center thread by
# about 3.9 mm when the pulley is seated at the spline base.
screw = Part.makeCylinder(1.5, 8.0, App.Vector(assembly_x, 0, -3.9))
screw = screw.fuse(Part.makeCylinder(3.0, 2.0, App.Vector(assembly_x, 0, 4.1)))
screw_obj = doc.addObject("PartDesign::Feature", "M3X8_CENTER_RETAINER_REFERENCE")
screw_obj.Label = "M3x8 center retaining screw — verify actual servo thread"
screw_obj.Shape = screw
screw_obj.Visibility = False
add_string(screw_obj, "ConnectionID", "C-MG996-DIRECT-SPLINE")
add_string(screw_obj, "Fastener", "M3x8, head OD6 H2, estimated thread engagement 3.9 mm")

assembly_group = doc.addObject("App::DocumentObjectGroup", "INSTALLED_ASSEMBLY_REFERENCE")
assembly_group.Label = "Installed assembly reference — toggle children visible"
assembly_group.addObject(reference)
assembly_group.addObject(installed)
assembly_group.addObject(screw_obj)

notes = doc.addObject("App::FeaturePython", "PROTOTYPE_REQUIREMENTS")
for name, value in {
    "Status": "FAIL_NOT_COMPLETE",
    "RequiredChecks": "physical spline fit; M3 center-thread confirmation; 30 s hold; belt tracking; no tooth skip; servo bearing temperature/play",
    "LoadRestriction": "Fit test by hand only until coupon passes; do not apply the arm belt load",
    "Reason": "Direct pulley returns belt radial load to the servo output bearing and removes the supported input shaft",
}.items():
    add_string(notes, name, value)

doc.recompute()
doc.saveAs(str(FCSTD))
Part.export([pulley_obj], str(PULLEY_STEP))
export_stl(pulley, PULLEY_STL)
export_stl(coupon, COUPON_STL)

print(f"FCStd={FCSTD}")
print(f"pulley_stl={PULLEY_STL}")
print(f"coupon_stl={COUPON_STL}")
print(f"pulley_volume_mm3={pulley.Volume:.3f}")
print(f"pulley_solids={len(pulley.Solids)} valid={pulley.isValid()}")
print(f"coupon_solids={len(coupon.Solids)} valid={coupon.isValid()}")
