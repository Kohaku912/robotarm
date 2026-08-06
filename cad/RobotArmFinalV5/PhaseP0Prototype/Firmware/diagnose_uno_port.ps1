$ErrorActionPreference = "Stop"

Write-Host "Arduino and serial devices:"
Get-PnpDevice -PresentOnly |
    Where-Object {
        $_.InstanceId -match "VID_2341" -or
        $_.FriendlyName -match "Arduino|UNO R4"
    } |
    Format-Table Status,Class,FriendlyName,InstanceId -AutoSize

Write-Host ""
Write-Host "COM ports:"
Get-CimInstance Win32_SerialPort |
    Format-Table DeviceID,Name,PNPDeviceID -AutoSize

Write-Host ""
Write-Host "Detected issue in the current session:"
Write-Host "COM3 is listed, but Windows returns:"
Write-Host "'A device attached to the system is not functioning.'"
Write-Host ""
Write-Host "Recovery:"
Write-Host "1. Close serial monitors."
Write-Host "2. Disconnect external servo power."
Write-Host "3. Double-press RESET."
Write-Host "4. Run upload_safe_commissioning.ps1."
