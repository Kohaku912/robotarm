# UNO R4 WiFi commissioning package

Detected board:

- Board: Arduino UNO R4 WiFi
- Normal port: COM3
- FQBN: `arduino:renesas_uno:unor4wifi`
- Board core: 1.5.3

Installed on the user's PC:

- ArduinoJson 7.4.2
- Servo library

Both the safe commissioning sketch and full P0 sketch compiled successfully.

## Current blocker

Windows lists COM3, but opening it returns:

`A device attached to the system is not functioning.`

The current board sketch appears to expose a broken CDC serial endpoint.
The physical RESET button must be double-pressed so the bootloader creates a
temporary usable serial port.

## Safe upload

External servo power should remain disconnected.

```powershell
cd "$HOME\Documents\RobotArmFinalV5\PhaseP0Prototype\Firmware"
.\upload_safe_commissioning.ps1
```

When prompted, double-press RESET. The script automatically detects the
temporary bootloader COM port and uploads the safe diagnostic firmware.

The diagnostic firmware:

- does not attach any Servo object;
- keeps D13 LOW;
- never enables servo power;
- reports the six NC inputs;
- reports E-stop state;
- reports provisional A0/A1 current and voltage readings.

## Full PWM upload

Only after the diagnostic inputs are verified:

```powershell
.\upload_full_p0.ps1 -ServoPowerPhysicallyDisconnected
```
