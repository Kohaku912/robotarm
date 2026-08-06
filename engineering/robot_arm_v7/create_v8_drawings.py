import FreeCAD as App

doc = App.ActiveDocument
if doc is None or doc.Name != "ROBOT_ARM_V8_MANUFACTURABLE":
    raise RuntimeError("Open ROBOT_ARM_V8_MANUFACTURABLE before generating drawings")

import TechDraw
import TechDrawGui

template_path = App.getResourceDir() + "Mod/TechDraw/Templates/A3_Landscape_TD.svg"
out_dir = "C:/Users/kohak/programs/robotarm/engineering/robot_arm_v7"


def clean(name):
    obj = doc.getObject(name)
    if obj:
        doc.removeObject(name)


for name in (
    "TD_ASSEMBLY", "TD_ASSEMBLY_TEMPLATE", "TD_FRONT", "TD_TOP", "TD_ISO", "TD_ASSY_NOTE",
    "TD_J1", "TD_J1_TEMPLATE", "TD_J1_TOP", "TD_J1_SECTION", "TD_J1_NOTE",
    "TD_LINKS", "TD_LINKS_TEMPLATE", "TD_UA", "TD_FA", "TD_WRIST", "TD_LINK_NOTE",
):
    clean(name)


def page_with_template(page_name, template_name):
    page = doc.addObject("TechDraw::DrawPage", page_name)
    template = doc.addObject("TechDraw::DrawSVGTemplate", template_name)
    template.Template = template_path
    page.Template = template
    return page


all_parts = [o for o in doc.Objects if o.TypeId == "PartDesign::Feature"]

assembly = page_with_template("TD_ASSEMBLY", "TD_ASSEMBLY_TEMPLATE")
front = doc.addObject("TechDraw::DrawViewPart", "TD_FRONT")
front.Source = all_parts
front.Direction = App.Vector(0, -1, 0)
front.X, front.Y, front.ScaleType, front.Scale = 95, 105, "Custom", 0.62
assembly.addView(front)
top = doc.addObject("TechDraw::DrawViewPart", "TD_TOP")
top.Source = all_parts
top.Direction = App.Vector(0, 0, 1)
top.X, top.Y, top.ScaleType, top.Scale = 95, 245, "Custom", 0.62
assembly.addView(top)
iso = doc.addObject("TechDraw::DrawViewPart", "TD_ISO")
iso.Source = all_parts
iso.Direction = App.Vector(1, -1, 0.8)
iso.X, iso.Y, iso.ScaleType, iso.Scale = 300, 150, "Custom", 0.45
assembly.addView(iso)
note = doc.addObject("TechDraw::DrawViewAnnotation", "TD_ASSY_NOTE")
note.Text = [
    "ROBOT ARM V8 — ASSEMBLY / ENVELOPE",
    "Reach 288 mm; base OD 88 mm; extended width 64 mm max; shoulder axis Z=79 mm",
    "Payload 50 g; 4.8 V; normal range J2 -90..0, J3 -90..90, J4 -60..60 deg",
    "Fold corridor: J2=-80, J3 90..150, J4 0..-70 deg; see MuJoCo report",
    "DO NOT SCALE. All dimensions in mm. See connection schedule for fastening details.",
]
note.X, note.Y = 245, 270
assembly.addView(note)

j1_names = [n for n in [
    "BASE_PLATE", "V8_R_J1_RingGear", "V8_R_J1_SunGear", "V8_R_J1_Planet1",
    "V8_R_J1_Planet2", "V8_R_J1_Planet3", "V8_R_J1_LowerHousing",
    "V8_R_J1_UpperHousing", "V8_R_J1_CarrierLower", "V8_R_J1_CarrierUpper",
    "F695_J1_1", "F695_J1_2", "J1_SERVO", "J1_STOCK_HORN",
] if doc.getObject(n)]
j1_parts = [doc.getObject(n) for n in j1_names]
j1page = page_with_template("TD_J1", "TD_J1_TEMPLATE")
j1top = doc.addObject("TechDraw::DrawViewPart", "TD_J1_TOP")
j1top.Source = j1_parts
j1top.Direction = App.Vector(0, 0, 1)
j1top.X, j1top.Y, j1top.ScaleType, j1top.Scale = 105, 150, "Custom", 1.6
j1page.addView(j1top)
j1side = doc.addObject("TechDraw::DrawViewPart", "TD_J1_SECTION")
j1side.Source = j1_parts
j1side.Direction = App.Vector(0, -1, 0)
j1side.X, j1side.Y, j1side.ScaleType, j1side.Scale = 270, 150, "Custom", 1.6
j1page.addView(j1side)
j1note = doc.addObject("TechDraw::DrawViewAnnotation", "TD_J1_NOTE")
j1note.Text = [
    "J1 GEARCASE / INTERFACES",
    "Gear: m1.0, 20 deg involute, 12T sun / 24T planets x3 / 60T fixed ring, ratio 6:1",
    "Case OD 84; ring boss PCD 76; six M3 clearance 3.4; M3 inserts OD6 x L4",
    "F685ZZ planets: 5x11x5, flange 12.5x1. F695ZZ output: 5x13x4, flange 15x1.",
    "Case screws: 6x M3x20, top access, minimum insert engagement 4.0.",
    "Sun horn: 2x M2x8 through bolts + prevailing-torque nuts; supplied center screw retained.",
]
j1note.X, j1note.Y = 220, 280
j1page.addView(j1note)

linkpage = page_with_template("TD_LINKS", "TD_LINKS_TEMPLATE")
for name, source_names, y, scale in (
    ("TD_UA", ["UPPER_ARM_L", "UPPER_ARM_R"], 235, 1.0),
    ("TD_FA", ["FOREARM_L", "FOREARM_R"], 150, 1.0),
    ("TD_WRIST", ["WRIST_PITCH_L", "WRIST_PITCH_R", "J5_BEARING_HOUSING", "GRIPPER_CRADLE"], 65, 1.0),
):
    view = doc.addObject("TechDraw::DrawViewPart", name)
    view.Source = [doc.getObject(n) for n in source_names if doc.getObject(n)]
    view.Direction = App.Vector(0, -1, 0)
    view.X, view.Y, view.ScaleType, view.Scale = 140, y, "Custom", scale
    linkpage.addView(view)
linknote = doc.addObject("TechDraw::DrawViewAnnotation", "TD_LINK_NOTE")
linknote.Text = [
    "LINK PLATES — PA12-CF10 FDM",
    "Upper arm and forearm pivot spacing 115.0; wrist stack 30.0; tool tip X=288.0.",
    "Plate thickness 3.0; top/bottom beams 4.0 high; nominal beam separation 16.0.",
    "Print flat, 0.15 mm layer, 6 perimeters; bearing bores undersize then ream after conditioning.",
    "Horn joints: 2x M3 screws per axis into OD6 x L4 heat-set inserts; 4.0 mm engagement.",
]
linknote.X, linknote.Y = 300, 265
linkpage.addView(linknote)

doc.recompute()
doc.save()
for page, stem in ((assembly, "V8_TechDraw_Assembly"), (j1page, "V8_TechDraw_J1"), (linkpage, "V8_TechDraw_Links")):
    TechDrawGui.exportPageAsPdf(page, out_dir + "/" + stem + ".pdf")
