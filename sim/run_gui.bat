@echo off
cd /d "%~dp0\.."
py -3.11 -m pip install pybullet numpy --prefer-binary
py -3.11 sim\pybullet_arm.py
pause
