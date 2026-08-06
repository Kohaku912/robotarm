$ErrorActionPreference = "Stop"
$FirmwareRoot = $PSScriptRoot
$Bossac = Join-Path $env:LOCALAPPDATA "Arduino15\packages\arduino\tools\bossac\1.9.1-arduino5\bossac.exe"
$Binary = Join-Path $FirmwareRoot "commissioning_build\robot_arm_p0_commissioning.ino.bin"
$Log = Join-Path $FirmwareRoot "safe_upload_watch.log"
$Status = Join-Path $FirmwareRoot "commissioning_upload_status.json"

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Host $Message
}

function Save-Status([string]$State, [string]$Message, [string]$Port = "") {
    [PSCustomObject]@{
        time = (Get-Date -Format o)
        state = $State
        message = $Message
        port = $Port
        binary = $Binary
        servo_power_enable_forced_low = $true
    } | ConvertTo-Json -Depth 4 | Set-Content -Path $Status -Encoding UTF8
}

function Get-SerialDevices {
    @(Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue |
        Select-Object DeviceID,Name,PNPDeviceID)
}

function Test-Port([string]$Port) {
    try {
        $serial = New-Object System.IO.Ports.SerialPort $Port,115200,None,8,One
        $serial.ReadTimeout = 150
        $serial.WriteTimeout = 150
        $serial.Open()
        $serial.Close()
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-Path $Bossac)) { throw "bossac not found: $Bossac" }
if (-not (Test-Path $Binary)) { throw "safe binary not found: $Binary" }
Remove-Item $Log -ErrorAction SilentlyContinue
Save-Status "WAITING_FOR_BOOTLOADER" "Waiting for UNO R4 bootloader port"
Write-Log "Safe commissioning uploader is ready."
Write-Log "External 6 V servo power must remain disconnected."
Write-Log "Double-press the RESET button on the UNO R4 WiFi now."
Write-Log "Waiting up to 10 minutes..."

$deadline = (Get-Date).AddMinutes(10)
$bootPort = $null
while ((Get-Date) -lt $deadline) {
    foreach ($dev in (Get-SerialDevices)) {
        $pnp = [string]$dev.PNPDeviceID
        if ($pnp -match 'VID_2341&PID_006D') {
            $bootPort = [string]$dev.DeviceID
            break
        }
    }
    if ($bootPort) { break }
    Start-Sleep -Milliseconds 150
}

if (-not $bootPort) {
    Save-Status "TIMEOUT" "Bootloader port was not detected"
    throw "Bootloader port was not detected. Double-press RESET and run this script again."
}

Write-Log "Bootloader detected on $bootPort"
Save-Status "UPLOADING" "Uploading safe commissioning firmware" $bootPort
$bossacOutput = & $Bossac --port=$bootPort -U -e -w $Binary -R 2>&1 | Out-String
Add-Content -Path $Log -Value $bossacOutput -Encoding UTF8
if ($LASTEXITCODE -ne 0) {
    Save-Status "UPLOAD_FAILED" $bossacOutput $bootPort
    throw "bossac upload failed. See $Log"
}
Write-Log "Safe firmware upload completed."

$normalPort = $null
$normalDeadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $normalDeadline) {
    foreach ($dev in (Get-SerialDevices)) {
        $pnp = [string]$dev.PNPDeviceID
        if ($pnp -match 'VID_2341&PID_1002' -and (Test-Port ([string]$dev.DeviceID))) {
            $normalPort = [string]$dev.DeviceID
            break
        }
    }
    if ($normalPort) { break }
    Start-Sleep -Milliseconds 250
}

if (-not $normalPort) {
    Save-Status "UPLOADED_PORT_NOT_READY" "Firmware uploaded but normal serial port did not become usable" $bootPort
    throw "Firmware uploaded, but no usable normal serial port appeared."
}

Write-Log "Normal serial port is $normalPort"
$serial = New-Object System.IO.Ports.SerialPort $normalPort,115200,None,8,One
$serial.ReadTimeout = 1500
$serial.NewLine = "`n"
$lines = @()
try {
    $serial.Open()
    $readDeadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $readDeadline -and $lines.Count -lt 10) {
        try {
            $line = $serial.ReadLine().Trim()
            if ($line) {
                $lines += $line
                Write-Log "RX $line"
            }
        } catch [System.TimeoutException] {}
    }
} finally {
    if ($serial.IsOpen) { $serial.Close() }
}

$verified = ($lines | Where-Object { $_ -match 'commissioning_safe_mode' }).Count -gt 0
if (-not $verified) {
    Save-Status "TELEMETRY_NOT_VERIFIED" "Serial opened, but safe-mode telemetry was not confirmed" $normalPort
    throw "Safe-mode telemetry was not confirmed. See $Log"
}

Save-Status "PASS" "Safe commissioning firmware and telemetry verified" $normalPort
Write-Log "PASS: safe commissioning firmware is running."
Write-Log "D13 remains LOW and no Servo objects are attached."
Write-Host "Press Enter to close this window."
[void][Console]::ReadLine()
