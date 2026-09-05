#include "niulai_life.h"

#include "application.h"
#include "assets/lang_config.h"
#include "audio_codec.h"
#include "board.h"
#include "config.h"

#include <driver/gpio.h>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_rom_sys.h>
#include <esp_timer.h>

#include <string>

#define TAG "NiulaiLife"

namespace {
constexpr float kPresentCm = 55.0f;
constexpr int kPresentStreak = 1;
constexpr int64_t kAbsentUs = 8LL * 1000 * 1000;
constexpr int64_t kSecretTalkUs = 10LL * 1000 * 1000;
constexpr uint32_t kEchoTimeoutUs = 25000;
constexpr uint32_t kCenterUs = 1500;
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
            if (now - last_speak_us_ >= kSecretTalkUs) {
                SpeakSecret();
            }
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
    // Random gait, short burst then park so 360° servos stop.
    if (wiggle_phase_ == 0) {
        gait_ = static_cast<int>(esp_random() % 4);
    }
    wiggle_phase_ = (wiggle_phase_ + 1) % 14;
    if (wiggle_phase_ >= 4) {
        HoldCenter();
        return;
    }
    int sign = (wiggle_phase_ < 2) ? 1 : -1;
    int amp = 160 + static_cast<int>(esp_random() % 120);
    switch (gait_) {
        case 1:  // front pair
            WritePulseUs(0, kCenterUs + sign * amp);
            WritePulseUs(1, kCenterUs - sign * amp);
            WritePulseUs(2, kCenterUs);
            WritePulseUs(3, kCenterUs);
            break;
        case 2:  // rear pair
            WritePulseUs(0, kCenterUs);
            WritePulseUs(1, kCenterUs);
            WritePulseUs(2, kCenterUs - sign * amp);
            WritePulseUs(3, kCenterUs + sign * amp);
            break;
        case 3:  // turn in place
            WritePulseUs(0, kCenterUs + sign * amp);
            WritePulseUs(1, kCenterUs + sign * amp);
            WritePulseUs(2, kCenterUs + sign * amp);
            WritePulseUs(3, kCenterUs + sign * amp);
            break;
        default:  // diagonal
            WritePulseUs(0, kCenterUs + sign * amp);
            WritePulseUs(1, kCenterUs - sign * amp);
            WritePulseUs(2, kCenterUs - sign * amp);
            WritePulseUs(3, kCenterUs + sign * amp);
            break;
    }
}

void NiulaiLife::OnPresence(Presence next) {
    Presence prev = presence_;
    presence_ = next;
    ESP_LOGI(TAG, "presence %d -> %d", (int)prev, (int)next);
    if (next == kPresent) {
        ParkLegs();
        Speak(Lang::Sounds::OGG_HI, "happy", "你回来啦");
        return;
    }
    if (next == kAbsent) {
        wiggle_phase_ = 0;
        SpeakSecret();
    }
}

void NiulaiLife::SpeakSecret() {
    secret_line_ = (secret_line_ + 1) % 3;
    if (secret_line_ == 0) {
        Speak(Lang::Sounds::OGG_SECRET1, "sleepy", "终于清静了");
    } else if (secret_line_ == 1) {
        Speak(Lang::Sounds::OGG_SECRET2, "winking", "哼，又没人理我");
    } else {
        Speak(Lang::Sounds::OGG_SECRET3, "thinking", "他们以为我只会叫妈妈");
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

void NiulaiLife::Speak(const std::string_view& ogg, const char* emotion, const char* chat) {
    last_speak_us_ = esp_timer_get_time();
    PostFace(emotion, chat);
    Application::GetInstance().Schedule([ogg]() {
        auto& audio = Application::GetInstance().GetAudioService();
        auto* codec = Board::GetInstance().GetAudioCodec();
        if (codec != nullptr) {
            codec->SetOutputVolume(90);
        }
        audio.ResetDecoder();
        audio.PlaySound(ogg);
    });
}
