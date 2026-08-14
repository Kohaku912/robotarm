"""Run the V8 CAD audit against the saved assembly."""

from pathlib import Path

import FreeCAD as App


ROOT = Path("C:/Users/kohak/programs/robotarm")
MODEL = ROOT / "cad/RobotArmFinalV5/CompletedPreviewV5_2CradleAlignment/ROBOT_ARM_V8_MANUFACTURABLE.FCStd"
AUDIT = ROOT / "engineering/robot_arm_v7/audit_v8_freecad.py"

App.openDocument(str(MODEL))
exec(compile(AUDIT.read_text(encoding="utf-8"), str(AUDIT), "exec"), globals())
