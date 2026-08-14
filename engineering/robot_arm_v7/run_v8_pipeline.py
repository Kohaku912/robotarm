"""Headless rebuild and audit entry point for the V8 FreeCAD assembly."""

from pathlib import Path

import FreeCAD as App


ROOT = Path("C:/Users/kohak/programs/robotarm")
SOURCE = ROOT / "cad/RobotArmFinalV5/CompletedPreviewV5_2CradleAlignment/ROBOT_ARM_V7_MANUFACTURABLE.FCStd"
BUILD = ROOT / "engineering/robot_arm_v7/build_v8_freecad.py"
AUDIT = ROOT / "engineering/robot_arm_v7/audit_v8_freecad.py"

App.openDocument(str(SOURCE))
exec(compile(BUILD.read_text(encoding="utf-8"), str(BUILD), "exec"), globals())
exec(compile(AUDIT.read_text(encoding="utf-8"), str(AUDIT), "exec"), globals())
