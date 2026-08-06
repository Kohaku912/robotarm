param([switch]$ServoPowerPhysicallyDisconnected)
$ErrorActionPreference = "Stop"
if (-not $ServoPowerPhysicallyDisconnected) {
  throw "Disconnect the external 6 V servo rail, then rerun with -ServoPowerPhysicallyDisconnected"
}
$cli = Join-Path $env:LOCALAPPDATA "Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$sketch = Join-Path $PSScriptRoot "robot_arm_p0_uno_r4"
$build = Join-Path $PSScriptRoot "full_build"
New-Item -ItemType Directory -Force -Path $build | Out-Null
& $cli lib install "ArduinoJson@7.4.2"
& $cli lib install "Servo"
& $cli compile --fqbn arduino:renesas_uno:unor4wifi --output-dir $build $sketch
if ($LASTEXITCODE -ne 0) { throw "Compile failed" }
Write-Host "Double-press RESET if COM3 cannot be opened, then enter the temporary COM port."
$port = Read-Host "Upload COM port (example COM4)"
& $cli upload -p $port --fqbn arduino:renesas_uno:unor4wifi --input-dir $build
if ($LASTEXITCODE -ne 0) { throw "Upload failed" }
Write-Host "Full P0 firmware uploaded. Keep servo power disconnected until NC inputs are verified."
