param([string]$Port="COM3",[int]$Seconds=10)
$ErrorActionPreference="Stop"
$s=New-Object System.IO.Ports.SerialPort $Port,115200,None,8,One
$s.ReadTimeout=500; $s.NewLine="`n"; $s.Open()
try {
  $deadline=(Get-Date).AddSeconds($Seconds)
  while((Get-Date)-lt $deadline){
    try { Write-Host ($s.ReadLine().Trim()) } catch [System.TimeoutException] {}
  }
} finally { $s.Close() }
