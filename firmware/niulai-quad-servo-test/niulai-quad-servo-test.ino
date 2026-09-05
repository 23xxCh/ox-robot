/*
 * 牛来四足第一版：四路 SG90 轮流摆动测试
 * 左前 GPIO10 / 右前 GPIO11 / 左后 GPIO12 / 右后 GPIO13
 * 50 Hz，1.0 ms <-> 2.0 ms，转到头应停住。
 * 串口 115200。烧录会覆盖小智固件，测完可再刷回去。
 */

#include <Arduino.h>

static const int kPins[4] = {10, 11, 12, 13};
static const char *kNames[4] = {"FL GPIO10", "FR GPIO11", "RL GPIO12", "RR GPIO13"};

static const int kFreqHz = 50;
static const int kResBits = 14;
static const uint32_t kMaxDuty = (1u << kResBits) - 1;
static const uint32_t kPeriodUs = 1000000u / kFreqHz;

static uint32_t pulseToDuty(uint32_t pulseUs) {
  return (uint32_t)((uint64_t)pulseUs * kMaxDuty / kPeriodUs);
}

static void writePulse(int pin, uint32_t pulseUs) {
  ledcWrite(pin, pulseToDuty(pulseUs));
}

static void holdAll(uint32_t pulseUs) {
  for (int i = 0; i < 4; ++i) {
    writePulse(kPins[i], pulseUs);
  }
}

static void moveOne(int idx, uint32_t pulseUs, uint32_t holdMs) {
  Serial.printf("move %s pulse=%lu us\n", kNames[idx], (unsigned long)pulseUs);
  writePulse(kPins[idx], pulseUs);
  delay(holdMs);
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("niulai quad servo test");
  Serial.println("FL=10 FR=11 RL=12 RR=13  50Hz");

  for (int i = 0; i < 4; ++i) {
    if (!ledcAttach(kPins[i], kFreqHz, kResBits)) {
      Serial.printf("ledcAttach failed pin %d\n", kPins[i]);
    }
  }
  holdAll(1500);
  delay(800);
}

void loop() {
  holdAll(1500);
  delay(400);

  for (int i = 0; i < 4; ++i) {
    Serial.printf("--- %s ---\n", kNames[i]);
    holdAll(1500);
    delay(300);
    moveOne(i, 1000, 900);
    moveOne(i, 2000, 900);
    moveOne(i, 1500, 700);
  }

  Serial.println("cycle done");
  delay(600);
}
