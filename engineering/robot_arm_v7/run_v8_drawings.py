"""Regenerate V8 TechDraw PDFs through the full FreeCAD GUI runtime."""

from pathlib import Path
import subprocess


ROOT = Path("C:/Users/kohak/programs/robotarm")
FREECAD = Path("C:/Program Files/FreeCAD 1.0/bin/FreeCAD.exe")
MACRO = ROOT / "engineering/robot_arm_v7/update_v8_drawings.FCMacro"

subprocess.run([str(FREECAD), str(MACRO)], cwd=ROOT, check=True)
