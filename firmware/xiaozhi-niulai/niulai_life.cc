#include "niulai_life.h"

#include "application.h"
#include "config.h"

#include <driver/gpio.h>
#include <esp_log.h>
#include <esp_rom_sys.h>
#include <esp_timer.h>

#include <string>

#define TAG "NiulaiLife"

namespace {
constexpr float kPresentCm = 55.0f;
constexpr int kPresentStreak = 1;
constexpr int64_t kAbsentUs = 8LL * 1000 * 1000;
constexpr uint32_t kEchoTimeoutUs = 25000;
constexpr uint32_t kCenterUs = 1500;
constexpr int kWalkAmpUs = 250;
constexpr uint32_t kMaxDuty = (1u << 14) - 1;
}  // namespace

void NiulaiLife::Start(Display* display) {
    display_ = display;
    gpio_config_t trig = {};
    trig.pin_bit_mask = 1ULL << ULTRASONIC_TRIG_GPIO;
    trig.mode = GPIO_MODE_OUTPUT;
    gpio_config(&trig);
    gpio_set_level(ULTRASONIC_TRIG_GPIO, 0);

    gpio_config_t echo = {};
    echo.pin_bit_mask = 1ULL << ULTRASONIC_ECHO_GPIO;
    echo.mode = GPIO_MODE_INPUT;
    echo.pull_down_en = GPIO_PULLDOWN_ENABLE;
    gpio_config(&echo);

    // Core 0: audio / SR typically sit on core 1.
    xTaskCreatePinnedToCore(TaskTrampoline, "niulai_life", 4096, this, 5, nullptr, 0);
    ESP_LOGI(TAG, "life loop started TRIG=%d ECHO=%d", (int)ULTRASONIC_TRIG_GPIO,
             (int)ULTRASONIC_ECHO_GPIO);
}

void NiulaiLife::TaskTrampoline(void* arg) {
    static_cast<NiulaiLife*>(arg)->Loop();
}

void NiulaiLife::Loop() {
    last_present_us_ = esp_timer_get_time();
    while (true) {
        float cm = ReadCm();
        int64_t now = esp_timer_get_time();
        bool close = cm > 1.0f && cm < kPresentCm;
        if (close) {
            present_streak_++;
            last_present_us_ = now;
        } else {
            present_streak_ = 0;
        }

        Presence next = presence_;
        if (present_streak_ >= kPresentStreak) {
            next = kPresent;
        } else if (now - last_present_us_ >= kAbsentUs) {
            next = kAbsent;
        }

        if (next != presence_) {
            OnPresence(next);
        }

        if (presence_ == kPresent || close) {
            HoldCenter();
        } else if (presence_ == kAbsent) {
            SecretWalk();
        }

        if (++log_tick_ % 10 == 0) {
            ESP_LOGI(TAG, "cm=%.1f streak=%d presence=%d", cm, present_streak_, (int)presence_);
        }

        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

float NiulaiLife::ReadCm() {
    gpio_set_level(ULTRASONIC_TRIG_GPIO, 0);
    esp_rom_delay_us(3);
    gpio_set_level(ULTRASONIC_TRIG_GPIO, 1);
    esp_rom_delay_us(10);
    gpio_set_level(ULTRASONIC_TRIG_GPIO, 0);

    int64_t wait_start = esp_timer_get_time();
    while (gpio_get_level(ULTRASONIC_ECHO_GPIO) == 0) {
        if (esp_timer_get_time() - wait_start > kEchoTimeoutUs) {
            return -1.0f;
        }
    }
    int64_t rise = esp_timer_get_time();
    while (gpio_get_level(ULTRASONIC_ECHO_GPIO) == 1) {
        if (esp_timer_get_time() - rise > kEchoTimeoutUs) {
            return -1.0f;
        }
    }
    int64_t width = esp_timer_get_time() - rise;
    return (static_cast<float>(width) * 0.0343f) / 2.0f;
}

void NiulaiLife::WritePulseUs(int index, uint32_t pulse_us) {
    if (pulse_us < 1100) {
        pulse_us = 1100;
    }
    if (pulse_us > 1900) {
        pulse_us = 1900;
    }
    uint32_t duty = pulse_us * kMaxDuty / 20000u;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, channels_[index], duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, channels_[index]);
}

void NiulaiLife::HoldCenter() {
    for (int i = 0; i < 4; ++i) {
        WritePulseUs(i, kCenterUs);
    }
}

void NiulaiLife::ParkLegs() {
    HoldCenter();
}

void NiulaiLife::SnapFreeze() {
    ParkLegs();
    PostFace("neutral", "");
}

void NiulaiLife::SecretWalk() {
    // 400 ms diagonal, then ~2 s parked at 1500 us.
    // Holding 1250/1750 forever makes 360° SG90s spin; 1500 stops them.
    // PRESENT / close pre-empts before this runs.
    wiggle_phase_ = (wiggle_phase_ + 1) % 12;
    if (wiggle_phase_ >= 2) {
        HoldCenter();
        return;
    }
    int sign = (wiggle_phase_ == 0) ? 1 : -1;
    WritePulseUs(0, kCenterUs + sign * kWalkAmpUs);
    WritePulseUs(1, kCenterUs - sign * kWalkAmpUs);
    WritePulseUs(2, kCenterUs - sign * kWalkAmpUs);
    WritePulseUs(3, kCenterUs + sign * kWalkAmpUs);
    if (wiggle_phase_ == 0) {
        PostFace("sleepy", "……");
    } else if (wiggle_phase_ == 1) {
        PostFace("winking", "……");
    }
}

void NiulaiLife::OnPresence(Presence next) {
    Presence prev = presence_;
    presence_ = next;
    ESP_LOGI(TAG, "presence %d -> %d", (int)prev, (int)next);
    if (next == kPresent) {
        SnapFreeze();
        return;
    }
    if (next == kAbsent) {
        wiggle_phase_ = 0;
        PostFace("sleepy", "……");
    }
}

void NiulaiLife::PostFace(const char* emotion, const char* chat) {
    if (display_ == nullptr) {
        return;
    }
    std::string emo = emotion != nullptr ? emotion : "neutral";
    std::string msg = chat != nullptr ? chat : "";
    Display* display = display_;
    Application::GetInstance().Schedule([display, emo, msg]() {
        display->SetEmotion(emo.c_str());
        display->SetChatMessage(msg.empty() ? "system" : "assistant", msg.c_str());
    });
}
