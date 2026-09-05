/*
 * 牛来超声波测试：HC-SR04
 * TRIG=GPIO8  ECHO=GPIO17
 * 串口 115200，每 200ms 打一次距离。
 * 同时保持四路舵机在中位，避免腿掉电乱抖。
 */

#include <Arduino.h>

static const int kTrig = 8;
static const int kEcho = 17;
static const int kServoPins[4] = {10, 11, 12, 13};

static const uint32_t kTimeoutUs = 25000;
static const int kFreqHz = 50;
static const int kResBits = 14;
static const uint32_t kMaxDuty = (1u << kResBits) - 1;

static uint32_t pulseToDuty(uint32_t pulseUs) {
  return (uint32_t)((uint64_t)pulseUs * kMaxDuty / 20000u);
}

static float readCm() {
  digitalWrite(kTrig, LOW);
  delayMicroseconds(3);
  digitalWrite(kTrig, HIGH);
  delayMicroseconds(10);
  digitalWrite(kTrig, LOW);

  unsigned long us = pulseIn(kEcho, HIGH, kTimeoutUs);
  if (us == 0) {
    return -1.0f;
  }
  return (us * 0.0343f) / 2.0f;
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("niulai hcsr04 test TRIG=8 ECHO=17");

  pinMode(kTrig, OUTPUT);
  pinMode(kEcho, INPUT);
  digitalWrite(kTrig, LOW);

  for (int i = 0; i < 4; ++i) {
    ledcAttach(kServoPins[i], kFreqHz, kResBits);
    ledcWrite(kServoPins[i], pulseToDuty(1500));
  }
}

void loop() {
  float cm = readCm();
  if (cm < 0) {
    Serial.println("echo timeout  (no return pulse)");
  } else {
    Serial.printf("dist_cm=%.1f\n", cm);
  }
  delay(200);
}
