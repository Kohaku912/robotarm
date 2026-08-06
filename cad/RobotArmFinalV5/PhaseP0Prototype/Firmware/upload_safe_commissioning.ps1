$ErrorActionPreference = "Stop"
$cli = Join-Path $env:LOCALAPPDATA "Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
if (-not (Test-Path $cli)) { throw "arduino-cli not found" }
$sketch = Join-Path $PSScriptRoot "robot_arm_p0_commissioning"
$build = Join-Path $PSScriptRoot "commissioning_build"
New-Item -ItemType Directory -Force -Path $build | Out-Null

& $cli lib install "ArduinoJson@7.4.2"
if ($LASTEXITCODE -ne 0) { throw "ArduinoJson install failed" }
& $cli compile --fqbn arduino:renesas_uno:unor4wifi --output-dir $build $sketch
if ($LASTEXITCODE -ne 0) { throw "Compile failed" }

function Test-Port([string]$Port) {
  try {
    $s = New-Object System.IO.Ports.SerialPort $Port,115200,None,8,One
    $s.ReadTimeout = 200
    $s.Open(); $s.Close(); return $true
  } catch { return $false }
}

function Find-UsablePort([int]$Seconds) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) {
    $ports = Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue |
      Where-Object { $_.DeviceID -ne "COM1" } |
      Select-Object -ExpandProperty DeviceID
    foreach ($port in $ports) {
      if (Test-Port $port) { return $port }
    }
    Start-Sleep -Milliseconds 250
  }
  return $null
}

$port = Find-UsablePort 3
if (-not $port) {
  Write-Host "COM3 is present but its serial endpoint is not opening."
  Write-Host "Disconnect external servo power, then double-press RESET now."
  Write-Host "Waiting 30 seconds for the bootloader port..."
  $port = Find-UsablePort 30
}
if (-not $port) { throw "No usable UNO R4 bootloader port appeared" }

& $cli upload -p $port --fqbn arduino:renesas_uno:unor4wifi --input-dir $build
if ($LASTEXITCODE -ne 0) { throw "Upload failed on $port" }
Write-Host "Safe commissioning firmware uploaded on $port"
Write-Host "D13 remains LOW and no Servo object is attached."
