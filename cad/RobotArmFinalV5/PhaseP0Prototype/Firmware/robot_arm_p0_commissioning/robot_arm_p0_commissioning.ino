#include <ArduinoJson.h>

static const uint32_t BAUD = 115200;
static const uint8_t LIMIT_PINS[6] = {2, 3, 4, 5, 6, 7};
static const uint8_t SERVO_POWER_ENABLE_PIN = 13;
static const uint8_t ESTOP_STATUS_PIN = A2;
static const uint8_t CURRENT_SENSOR_PIN = A0;
static const uint8_t VOLTAGE_SENSOR_PIN = A1;
static uint32_t lastTelemetryMs = 0;
static uint32_t lastRxMs = 0;

uint16_t checksum16(const String &text) {
  uint32_t sum = 0;
  for (size_t i = 0; i < text.length(); ++i) {
    sum += static_cast<uint8_t>(text[i]);
  }
  return static_cast<uint16_t>(sum & 0xFFFF);
}

bool ncTriggered(uint8_t pin) {
  return digitalRead(pin) != LOW;
}

bool estopOpen() {
  return ncTriggered(ESTOP_STATUS_PIN);
}

float readServoVoltage() {
  const float adcReference = 5.0f;
  const float dividerRatio = 2.0f;
  return analogRead(VOLTAGE_SENSOR_PIN)
      * adcReference / 1023.0f * dividerRatio;
}

float readTotalCurrent() {
  const float adcReference = 5.0f;
  const float zeroVoltage = 2.5f;
  const float voltsPerAmp = 0.185f;
  float voltage = analogRead(CURRENT_SENSOR_PIN)
      * adcReference / 1023.0f;
  return max(0.0f, (voltage - zeroVoltage) / voltsPerAmp);
}

void sendTelemetry() {
  JsonDocument doc;
  doc["type"] = "telemetry";
  doc["seq"] = 0;
  doc["enabled"] = false;
  JsonArray limits = doc["limits"].to<JsonArray>();
  for (uint8_t i = 0; i < 6; ++i) {
    limits.add(ncTriggered(LIMIT_PINS[i]) ? 1 : 0);
  }
  doc["voltage"] = readServoVoltage();
  doc["current"] = readTotalCurrent();
  doc["estop_open"] = estopOpen();
  doc["fault"] = "commissioning_safe_mode";
  doc["last_rx_age_ms"] = millis() - lastRxMs;

  String base;
  serializeJson(doc, base);
  uint16_t check = checksum16(base);
  String framed = base.substring(0, base.length() - 1);
  framed += ",\"check\":";
  framed += String(check);
  framed += "}\n";
  Serial.print(framed);
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
  lastRxMs = millis();
}

void loop() {
  while (Serial.available()) {
    Serial.read();
    lastRxMs = millis();
  }

  digitalWrite(SERVO_POWER_ENABLE_PIN, LOW);

  if (millis() - lastTelemetryMs >= 100) {
    lastTelemetryMs = millis();
    sendTelemetry();
  }
}
