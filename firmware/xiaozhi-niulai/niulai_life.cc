#include "niulai_life.h"
#include "config.h"

#include <driver/gpio.h>
#include <esp_log.h>
#include <esp_rom_sys.h>
#include <esp_timer.h>

#define TAG "NiulaiLife"

namespace {
constexpr float kPresentCm = 55.0f;
constexpr int kPresentStreak = 2;
constexpr int64_t kAbsentUs = 8LL * 1000 * 1000;
constexpr uint32_t kEchoTimeoutUs = 25000;
constexpr uint32_t kCenterUs = 1500;
constexpr uint32_t kWiggleUs = 120;
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
    gpio_config(&echo);

    xTaskCreatePinnedToCore(TaskTrampoline, "niulai_life", 4096, this, 5, nullptr, 1);
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
        } else if (presence_ == kUnknown && !close) {
            next = kUnknown;
        }

        if (next != presence_) {
            OnPresence(next);
        }

        if (presence_ == kPresent) {
            HoldCenter();
        } else if (presence_ == kAbsent) {
            SecretWiggle();
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

void NiulaiLife::SnapFreeze() {
    HoldCenter();
    if (display_ != nullptr) {
        display_->SetEmotion("neutral");
        display_->SetChatMessage("system", "");
    }
}

void NiulaiLife::SecretWiggle() {
    wiggle_phase_ = (wiggle_phase_ + 1) % 8;
    int sign = (wiggle_phase_ < 4) ? 1 : -1;
    uint32_t delta = kWiggleUs;
    WritePulseUs(0, kCenterUs + sign * static_cast<int>(delta));
    WritePulseUs(1, kCenterUs - sign * static_cast<int>(delta));
    WritePulseUs(2, kCenterUs - sign * static_cast<int>(delta / 2));
    WritePulseUs(3, kCenterUs + sign * static_cast<int>(delta / 2));
}

void NiulaiLife::OnPresence(Presence next) {
    Presence prev = presence_;
    presence_ = next;
    ESP_LOGI(TAG, "presence %d -> %d", (int)prev, (int)next);
    if (display_ == nullptr) {
        return;
    }
    if (next == kPresent) {
        SnapFreeze();
        return;
    } else if (next == kAbsent) {
        display_->SetEmotion("sleepy");
        display_->SetChatMessage("assistant", "……");
    }
}
