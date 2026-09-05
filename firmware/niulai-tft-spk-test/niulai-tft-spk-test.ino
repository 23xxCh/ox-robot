/*
 * 牛来扩展板：2.0 寸 ST7789 + MAX98357 喇叭测试
 * 屏: SCL=21 SDA=47 RES=45 DC=40 CS=41 BLK=42
 * 喇叭: BCLK=15 LRC=16 DIN=7
 * 超声波: TRIG=8 ECHO=17（屏上显示距离）
 * 舵机保持中位: 10/11/12/13
 */

#include <Arduino.h>
#include <math.h>
#include <Arduino_GFX_Library.h>
#include "ESP_I2S.h"

static const int PIN_SCK = 21;
static const int PIN_MOSI = 47;
static const int PIN_RST = 45;
static const int PIN_DC = 40;
static const int PIN_CS = 41;
static const int PIN_BL = 42;
static const int PIN_BCLK = 15;
static const int PIN_LRC = 16;
static const int PIN_DOUT = 7;
static const int PIN_TRIG = 8;
static const int PIN_ECHO = 17;
static const int kServoPins[4] = {10, 11, 12, 13};

static const int kSampleRate = 16000;
static const int kFreqHz = 50;
static const int kResBits = 14;
static const uint32_t kMaxDuty = (1u << kResBits) - 1;

Arduino_DataBus *bus = new Arduino_ESP32SPI(
    PIN_DC, PIN_CS, PIN_SCK, PIN_MOSI, GFX_NOT_DEFINED);
Arduino_GFX *gfx = new Arduino_ST7789(
    bus, PIN_RST, 0 /* rotation */, false /* IPS */, 240, 320);

I2SClass i2s;

static uint32_t pulseToDuty(uint32_t pulseUs) {
  return (uint32_t)((uint64_t)pulseUs * kMaxDuty / 20000u);
}

static float readCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(3);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long us = pulseIn(PIN_ECHO, HIGH, 25000);
  if (us == 0) {
    return -1.0f;
  }
  return (us * 0.0343f) / 2.0f;
}

static void beep(int hz, int ms) {
  const int n = kSampleRate * ms / 1000;
  int16_t buf[256];
  int written = 0;
  while (written < n) {
    int chunk = n - written;
    if (chunk > 256) {
      chunk = 256;
    }
    for (int i = 0; i < chunk; ++i) {
      float t = (float)(written + i) / (float)kSampleRate;
      buf[i] = (int16_t)(sinf(2.0f * 3.1415926f * hz * t) * 12000.0f);
    }
    i2s.write((uint8_t *)buf, chunk * sizeof(int16_t));
    written += chunk;
  }
}

static void drawBars() {
  int w = gfx->width();
  int bar = w / 3;
  gfx->fillScreen(RGB565_BLACK);
  gfx->fillRect(0, 0, bar, 70, RGB565_RED);
  gfx->fillRect(bar, 0, bar, 70, RGB565_GREEN);
  gfx->fillRect(bar * 2, 0, w - bar * 2, 70, RGB565_BLUE);
  gfx->setTextColor(RGB565_WHITE);
  gfx->setTextSize(2);
  gfx->setCursor(bar / 2 - 6, 24);
  gfx->print("R");
  gfx->setCursor(bar + bar / 2 - 6, 24);
  gfx->print("G");
  gfx->setCursor(bar * 2 + bar / 2 - 6, 24);
  gfx->print("B");
  gfx->setTextSize(3);
  gfx->setCursor(12, 90);
  gfx->print("NIULAI");
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("niulai tft+spk test");

  pinMode(PIN_BL, OUTPUT);
  digitalWrite(PIN_BL, HIGH);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  for (int i = 0; i < 4; ++i) {
    ledcAttach(kServoPins[i], kFreqHz, kResBits);
    ledcWrite(kServoPins[i], pulseToDuty(1500));
  }

  if (!gfx->begin()) {
    Serial.println("tft begin FAIL");
  } else {
    Serial.println("tft begin OK");
  }
  gfx->invertDisplay(true);

  i2s.setPins(PIN_BCLK, PIN_LRC, PIN_DOUT);
  if (!i2s.begin(I2S_MODE_STD, kSampleRate, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO)) {
    Serial.println("i2s begin FAIL");
  } else {
    Serial.println("i2s begin OK");
  }

  drawBars();
  beep(880, 200);
  delay(150);
  beep(1175, 200);
}

void loop() {
  float cm = readCm();
  char line[48];
  if (cm < 0) {
    snprintf(line, sizeof(line), "echo timeout");
  } else {
    snprintf(line, sizeof(line), "dist %.1f cm", cm);
  }
  gfx->fillRect(0, 150, gfx->width(), 90, RGB565_BLACK);
  gfx->setTextColor(RGB565_YELLOW);
  gfx->setTextSize(3);
  gfx->setCursor(12, 170);
  gfx->println(line);
  Serial.println(line);

  if (cm > 0 && cm < 12.0f) {
    beep(1500, 80);
  }
  delay(200);
}
