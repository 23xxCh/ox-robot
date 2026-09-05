#ifndef NIULAI_LIFE_H
#define NIULAI_LIFE_H

#include "display.h"

#include <driver/ledc.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

class NiulaiLife {
public:
    void Start(Display* display);
    void SnapFreeze();
    void ParkLegs();
    void PulseMotion(const char* dir, int ms);

private:
    enum Presence { kUnknown, kPresent, kAbsent };

    Display* display_ = nullptr;
    Presence presence_ = kUnknown;
    int64_t last_present_us_ = 0;
    int64_t last_brain_us_ = 0;
    int present_streak_ = 0;
    int wiggle_phase_ = 0;
    int gait_ = 0;
    int log_tick_ = 0;
    int64_t motion_until_us_ = 0;
    ledc_channel_t channels_[4] = {
        LEDC_CHANNEL_2, LEDC_CHANNEL_3, LEDC_CHANNEL_4, LEDC_CHANNEL_5
    };

    static void TaskTrampoline(void* arg);
    void Loop();
    float ReadCm();
    void WritePulseUs(int index, uint32_t pulse_us);
    void HoldCenter();
    void SecretWalk();
    void OnPresence(Presence next);
    void PostFace(const char* emotion, const char* chat);
    void AskBrainSecret();
};

#endif
