/*
  Robot Arm V5.3-P0 — Arduino UNO R4 WiFi firmware

  Required library:
    ArduinoJson 7.x
    Servo (standard Arduino library)

  IMPORTANT:
  - The NC E-stop must physically cut servo power. This input is only status.
  - Safe NC circuits are wired to GND with INPUT_PULLUP, so LOW = safe/closed.
  - The servo-power-enable pin drives a suitable external MOSFET/relay circuit,
    never the servo rail directly.
*/

#include <ArduinoJson.h>
#include <Servo.h>

static const uint32_t BAUD = 115200;
static const uint32_t TELEMETRY_PERIOD_MS = 50;
static const uint32_t DEFAULT_WATCHDOG_MS = 200;

static const uint8_t SERVO_PINS[5] = {8, 9, 10, 11, 12};
static const uint8_t LIMIT_PINS[6] = {2, 3, 4, 5, 6, 7};
static const uint8_t SERVO_POWER_ENABLE_PIN = 13;
static const uint8_t ESTOP_STATUS_PIN = A2;
static const uint8_t CURRENT_SENSOR_PIN = A0;
static const uint8_t VOLTAGE_SENSOR_PIN = A1;

Servo servos[5];

// Replace after neutral calibration.
int neutralUs[5] = {1500, 1500, 1500, 1500, 1500};
int continuousSpanUs[5] = {200, 0, 0, 200, 200};
bool invertJoint[5] = {false, false, false, false, false};

int positionalMinUs[5] = {0, 700, 700, 0, 0};
int positionalMaxUs[5] = {0, 2300, 2300, 0, 0};

float commandSpeed[5] = {0, 0, 0, 0, 0};
float commandPositionDeg[5] = {0, 90, 90, 0, 0};
bool requestedEnable = false;
bool servoPowerEnabled = false;
uint32_t lastValidCommandMs = 0;
uint32_t watchdogMs = DEFAULT_WATCHDOG_MS;
uint32_t continuousWindowMs = 300;
uint32_t continuousMotionStartMs = 0;
bool continuousMotionActive = false;
uint32_t lastTelemetryMs = 0;
uint32_t lastSequence = 0;
String faultText = "";

uint16_t checksum16(const String &text) {
  uint32_t sum = 0;
  for (size_t i = 0; i < text.length(); ++i) {
    sum += static_cast<uint8_t>(text[i]);
  }
  return static_cast<uint16_t>(sum & 0xFFFF);
}

bool verifyChecksum(const String &line) {
  int marker = line.lastIndexOf(",\"check\":");
  if (marker < 0 || !line.endsWith("}")) return false;
  String base = line.substring(0, marker) + "}";
  JsonDocument doc;
  if (deserializeJson(doc, line)) return false;
  if (!doc["check"].is<int>()) return false;
  return static_cast<uint16_t>(doc["check"].as<int>()) == checksum16(base);
}

bool ncTriggered(uint8_t pin) {
  // LOW means the NC circuit is closed and safe.
  return digitalRead(pin) != LOW;
}

bool estopOpen() {
  return ncTriggered(ESTOP_STATUS_PIN);
}

float readServoVoltage() {
  // Placeholder calibration. Adjust dividerRatio and ADC reference by meter.
  const float adcReference = 5.0f;
  const float dividerRatio = 2.0f;
  float adc = analogRead(VOLTAGE_SENSOR_PIN);
  return adc * adcReference / 1023.0f * dividerRatio;
}

float readTotalCurrent() {
  // Placeholder for a centered analog current sensor. Calibrate before use.
  const float adcReference = 5.0f;
  const float zeroVoltage = 2.5f;
  const float voltsPerAmp = 0.185f;
  float voltage = analogRead(CURRENT_SENSOR_PIN) * adcReference / 1023.0f;
  return max(0.0f, (voltage - zeroVoltage) / voltsPerAmp);
}

void stopContinuousServos() {
  servos[0].writeMicroseconds(neutralUs[0]);
  servos[3].writeMicroseconds(neutralUs[3]);
  servos[4].writeMicroseconds(neutralUs[4]);
}

void disableServoPower(const String &reason) {
  requestedEnable = false;
  servoPowerEnabled = false;
  commandSpeed[0] = commandSpeed[3] = commandSpeed[4] = 0.0f;
  stopContinuousServos();
  digitalWrite(SERVO_POWER_ENABLE_PIN, LOW);
  if (reason.length() > 0) faultText = reason;
}

int speedToPulse(uint8_t joint, float speed) {
  speed = constrain(speed, -1.0f, 1.0f);
  if (invertJoint[joint]) speed = -speed;
  return neutralUs[joint] + static_cast<int>(
    round(speed * continuousSpanUs[joint])
  );
}

int degreesToPulse(uint8_t joint, float degrees) {
  degrees = constrain(degrees, 0.0f, 180.0f);
  if (invertJoint[joint]) degrees = 180.0f - degrees;
  float ratio = degrees / 180.0f;
  return static_cast<int>(
    round(positionalMinUs[joint] +
          ratio * (positionalMaxUs[joint] - positionalMinUs[joint]))
  );
}

void applyOutputs() {
  bool timedOut = millis() - lastValidCommandMs > watchdogMs;
  if (timedOut) {
    disableServoPower("command_watchdog");
    return;
  }
  if (estopOpen()) {
    disableServoPower("estop_open");
    return;
  }

  servoPowerEnabled = requestedEnable;
  digitalWrite(
    SERVO_POWER_ENABLE_PIN,
    servoPowerEnabled ? HIGH : LOW
  );

  if (!servoPowerEnabled) {
    stopContinuousServos();
    return;
  }

  // Continuous joints with direction-specific NC limit blocking.
  float j1 = commandSpeed[0];
  float j4 = commandSpeed[3];
  float j5 = commandSpeed[4];
  bool anyContinuous = abs(j1) > 0.0001f || abs(j4) > 0.0001f || abs(j5) > 0.0001f;
  if (anyContinuous && !continuousMotionActive) {
    continuousMotionActive = true;
    continuousMotionStartMs = millis();
  }
  if (!anyContinuous) {
    continuousMotionActive = false;
  }
  if (continuousMotionActive && millis() - continuousMotionStartMs >= continuousWindowMs) {
    j1 = j4 = j5 = 0.0f;
    commandSpeed[0] = commandSpeed[3] = commandSpeed[4] = 0.0f;
    continuousMotionActive = false;
  }
  if (j1 < 0 && ncTriggered(LIMIT_PINS[0])) j1 = 0;
  if (j1 > 0 && ncTriggered(LIMIT_PINS[1])) j1 = 0;
  if (j4 < 0 && ncTriggered(LIMIT_PINS[2])) j4 = 0;
  if (j4 > 0 && ncTriggered(LIMIT_PINS[3])) j4 = 0;
  if (j5 < 0 && ncTriggered(LIMIT_PINS[4])) j5 = 0;
  if (j5 > 0 && ncTriggered(LIMIT_PINS[5])) j5 = 0;

  servos[0].writeMicroseconds(speedToPulse(0, j1));
  servos[1].writeMicroseconds(
    degreesToPulse(1, commandPositionDeg[1])
  );
  servos[2].writeMicroseconds(
    degreesToPulse(2, commandPositionDeg[2])
  );
  servos[3].writeMicroseconds(speedToPulse(3, j4));
  servos[4].writeMicroseconds(speedToPulse(4, j5));
}

void sendTelemetry() {
  JsonDocument doc;
  doc["type"] = "telemetry";
  doc["seq"] = lastSequence;
  doc["enabled"] = servoPowerEnabled;
  JsonArray limits = doc["limits"].to<JsonArray>();
  for (uint8_t i = 0; i < 6; ++i) {
    limits.add(ncTriggered(LIMIT_PINS[i]) ? 1 : 0);
  }
  doc["voltage"] = readServoVoltage();
  doc["current"] = readTotalCurrent();
  doc["estop_open"] = estopOpen();
  if (faultText.length() > 0) {
    doc["fault"] = faultText;
  } else {
    doc["fault"] = nullptr;
  }

  String base;
  serializeJson(doc, base);
  uint16_t check = checksum16(base);
  String framed = base.substring(0, base.length() - 1);
  framed += ",\"check\":";
  framed += String(check);
  framed += "}\n";
  Serial.print(framed);
}

void handleCommand(const JsonDocument &doc) {
  lastSequence = doc["seq"] | lastSequence;
  requestedEnable = doc["enable"] | false;
  commandSpeed[0] = constrain(
    doc["j1_speed"] | 0.0f, -0.25f, 0.25f
  );
  commandPositionDeg[1] = constrain(
    doc["j2_deg"] | 90.0f, 30.0f, 145.0f
  );
  commandPositionDeg[2] = constrain(
    doc["j3_deg"] | 90.0f, 25.0f, 150.0f
  );
  commandSpeed[3] = constrain(
    doc["j4_speed"] | 0.0f, -0.25f, 0.25f
  );
  commandSpeed[4] = constrain(
    doc["j5_speed"] | 0.0f, -0.25f, 0.25f
  );
  watchdogMs = constrain(
    doc["timeout_ms"] | DEFAULT_WATCHDOG_MS,
    100UL,
    1000UL
  );
  continuousWindowMs = constrain(
    doc["continuous_window_ms"] | 300UL,
    100UL,
    1000UL
  );
  faultText = "";
  lastValidCommandMs = millis();
}

void handleNeutralCalibration(const JsonDocument &doc) {
  const char *jointName = doc["joint"] | "";
  int joint = -1;
  if (strcmp(jointName, "J1") == 0) joint = 0;
  if (strcmp(jointName, "J4") == 0) joint = 3;
  if (strcmp(jointName, "J5") == 0) joint = 4;
  if (joint < 0) return;

  int pulse = constrain(doc["pulse_us"] | 1500, 1300, 1700);
  neutralUs[joint] = pulse;
  requestedEnable = doc["enable"] | false;
  lastSequence = doc["seq"] | lastSequence;
  lastValidCommandMs = millis();
  if (requestedEnable && !estopOpen()) {
    digitalWrite(SERVO_POWER_ENABLE_PIN, HIGH);
    servoPowerEnabled = true;
    servos[joint].writeMicroseconds(pulse);
  }
}

void processLine(const String &line) {
  if (!verifyChecksum(line)) {
    disableServoPower("invalid_checksum");
    return;
  }
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, line);
  if (error) {
    disableServoPower("invalid_json");
    return;
  }
  const char *type = doc["type"] | "";
  if (strcmp(type, "command") == 0) {
    handleCommand(doc);
  } else if (strcmp(type, "calibrate_neutral") == 0) {
    handleNeutralCalibration(doc);
  } else {
    disableServoPower("unknown_message");
  }
}

void setup() {
  Serial.begin(BAUD);
  analogReadResolution(10);
  pinMode(SERVO_POWER_ENABLE_PIN, OUTPUT);
  digitalWrite(SERVO_POWER_ENABLE_PIN, LOW);
  pinMode(ESTOP_STATUS_PIN, INPUT_PULLUP);
  for (uint8_t i = 0; i < 6; ++i) {
    pinMode(LIMIT_PINS[i], INPUT_PULLUP);
  }
  for (uint8_t i = 0; i < 5; ++i) {
    servos[i].attach(SERVO_PINS[i]);
  }
  stopContinuousServos();
  servos[1].writeMicroseconds(degreesToPulse(1, 90));
  servos[2].writeMicroseconds(degreesToPulse(2, 90));
  lastValidCommandMs = millis();
}

void loop() {
  static String line;
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      line.trim();
      if (line.length() > 0) processLine(line);
      line = "";
    } else if (c != '\r') {
      if (line.length() < 512) {
        line += c;
      } else {
        line = "";
        disableServoPower("line_too_long");
      }
    }
  }

  applyOutputs();

  if (millis() - lastTelemetryMs >= TELEMETRY_PERIOD_MS) {
    lastTelemetryMs = millis();
    sendTelemetry();
  }
}
