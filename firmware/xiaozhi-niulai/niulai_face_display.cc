#include "niulai_face_display.h"

#include "display.h"

#include <esp_log.h>

#include <cstring>

#define TAG "NiulaiFace"

namespace {

constexpr uint32_t kAnimPeriodMs = 80;
constexpr int kBlinkEveryTicks = 28;
constexpr int kBlinkClosedTicks = 2;
constexpr uint32_t kBarn = 0x2B1D12;
constexpr uint32_t kFur = 0xF0B400;
constexpr uint32_t kSnout = 0xE39BB0;
constexpr uint32_t kHorn = 0xC8C2B4;
constexpr uint32_t kEar = 0xD4A090;
constexpr uint32_t kWhite = 0xFFF6EA;
constexpr uint32_t kBlack = 0x141414;
constexpr uint32_t kBlush = 0xE07090;
constexpr uint32_t kMouth = 0xB85A78;

lv_obj_t* Oval(lv_obj_t* parent, int w, int h, uint32_t hex) {
    lv_obj_t* o = lv_obj_create(parent);
    lv_obj_set_size(o, w, h);
    lv_obj_set_style_bg_color(o, lv_color_hex(hex), 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(o, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_border_width(o, 0, 0);
    lv_obj_set_style_outline_width(o, 0, 0);
    lv_obj_set_style_shadow_width(o, 0, 0);
    lv_obj_set_style_pad_all(o, 0, 0);
    lv_obj_set_style_clip_corner(o, true, 0);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_scrollbar_mode(o, LV_SCROLLBAR_MODE_OFF);
    return o;
}

void Hide(lv_obj_t* o) {
    if (o != nullptr) {
        lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN);
    }
}

void Show(lv_obj_t* o) {
    if (o != nullptr) {
        lv_obj_remove_flag(o, LV_OBJ_FLAG_HIDDEN);
    }
}

bool IsListen(const char* e) {
    return strcmp(e, "listening") == 0 || strcmp(e, "neutral") == 0 || strcmp(e, "relaxed") == 0 ||
           strcmp(e, "robot_2") == 0;
}

bool IsSmile(const char* e) {
    return strcmp(e, "happy") == 0 || strcmp(e, "laughing") == 0 || strcmp(e, "loving") == 0 ||
           strcmp(e, "funny") == 0 || strcmp(e, "cool") == 0;
}

}  // namespace

NiulaiLcdDisplay::NiulaiLcdDisplay(esp_lcd_panel_io_handle_t panel_io, esp_lcd_panel_handle_t panel,
                                   int width, int height, int offset_x, int offset_y, bool mirror_x,
                                   bool mirror_y, bool swap_xy)
    : SpiLcdDisplay(panel_io, panel, width, height, offset_x, offset_y, mirror_x, mirror_y,
                    swap_xy) {
    // Face is built in SetupUI() after the stock white chrome exists.
}

NiulaiLcdDisplay::~NiulaiLcdDisplay() {
    if (anim_timer_ != nullptr) {
        DisplayLockGuard lock(this);
        lv_timer_delete(anim_timer_);
        anim_timer_ = nullptr;
    }
}

void NiulaiLcdDisplay::AllowSecretFaces(bool allow) {
    secret_ok_ = allow;
}

void NiulaiLcdDisplay::SetupUI() {
    SpiLcdDisplay::SetupUI();
    DisplayLockGuard lock(this);
    HideChrome();
    if (face_ == nullptr) {
        BuildFace();
        StartAnim();
    }
    ApplyFace("listening");
    ESP_LOGI(TAG, "cow face on screen after SetupUI");
}

void NiulaiLcdDisplay::HideChrome() {
    Hide(container_);
    Hide(emoji_box_);
    Hide(emoji_label_);
    Hide(emoji_image_);
    Hide(top_bar_);
    Hide(status_bar_);
    Hide(bottom_bar_);
    Hide(preview_image_);
    Hide(content_);
    Hide(side_bar_);
}

void NiulaiLcdDisplay::ClearChatMessages() {
    DisplayLockGuard lock(this);
    HideChrome();
    Show(face_);
    if (face_ != nullptr) {
        lv_obj_move_foreground(face_);
    }
}

void NiulaiLcdDisplay::SetChatMessage(const char* /*role*/, const char* /*content*/) {
    DisplayLockGuard lock(this);
    HideChrome();
    Show(face_);
    if (face_ != nullptr) {
        lv_obj_move_foreground(face_);
    }
}

void NiulaiLcdDisplay::SetEmotion(const char* emotion) {
    DisplayLockGuard lock(this);
    blinking_ = false;
    blink_ticks_ = 0;
    const char* e = emotion != nullptr ? emotion : "listening";
    if (!secret_ok_ && !IsListen(e) && !IsSmile(e)) {
        e = "listening";
    }
    HideChrome();
    ApplyFace(e);
}

void NiulaiLcdDisplay::StartAnim() {
    if (anim_timer_ == nullptr) {
        anim_timer_ = lv_timer_create(AnimTimerCb, kAnimPeriodMs, this);
    }
}

void NiulaiLcdDisplay::AnimTimerCb(lv_timer_t* timer) {
    auto* self = static_cast<NiulaiLcdDisplay*>(lv_timer_get_user_data(timer));
    DisplayLockGuard lock(self);
    self->TickAnim();
}

void NiulaiLcdDisplay::TickAnim() {
    if (face_ == nullptr || lid_l_ == nullptr || lid_r_ == nullptr || mouth_ == nullptr) {
        return;
    }

    if (blinking_) {
        ++blink_ticks_;
        if (blink_ticks_ >= kBlinkClosedTicks) {
            blinking_ = false;
            blink_ticks_ = 0;
            ApplyFace(emotion_);
        }
    } else {
        ++blink_ticks_;
        if (blink_ticks_ >= kBlinkEveryTicks) {
            blinking_ = true;
            blink_ticks_ = 0;
            lv_obj_set_height(lid_l_, 28);
            lv_obj_set_height(lid_r_, 28);
        }
    }

    if (talking_) {
        static const int kPulse[] = {4, 12, 6, 2, 10, 3};
        int h = mouth_rest_h_ + kPulse[mouth_phase_ % 6];
        if (h < 8) {
            h = 8;
        }
        lv_obj_set_height(mouth_, h);
        ++mouth_phase_;
    }
}

void NiulaiLcdDisplay::BuildFace() {
    lv_obj_t* screen = lv_screen_active();
    lv_obj_set_style_bg_color(screen, lv_color_hex(kBarn), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);

    // Parent to the screen AFTER SetupUI so the stock white container cannot cover us.
    face_ = lv_obj_create(screen);
    lv_obj_set_size(face_, LV_HOR_RES, LV_VER_RES);
    lv_obj_align(face_, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(face_, lv_color_hex(kBarn), 0);
    lv_obj_set_style_bg_opa(face_, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(face_, 0, 0);
    lv_obj_set_style_border_width(face_, 0, 0);
    lv_obj_set_style_outline_width(face_, 0, 0);
    lv_obj_set_style_pad_all(face_, 0, 0);
    lv_obj_remove_flag(face_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(face_, LV_OBJ_FLAG_OVERFLOW_VISIBLE);
    lv_obj_move_foreground(face_);

    horn_l_ = Oval(face_, 36, 64, kHorn);
    lv_obj_align(horn_l_, LV_ALIGN_TOP_LEFT, 38, 10);
    horn_r_ = Oval(face_, 36, 64, kHorn);
    lv_obj_align(horn_r_, LV_ALIGN_TOP_RIGHT, -38, 10);

    ear_l_ = Oval(face_, 48, 36, kEar);
    lv_obj_align(ear_l_, LV_ALIGN_LEFT_MID, 6, -28);
    ear_r_ = Oval(face_, 48, 36, kEar);
    lv_obj_align(ear_r_, LV_ALIGN_RIGHT_MID, -6, -28);

    head_ = Oval(face_, 184, 168, kFur);
    lv_obj_align(head_, LV_ALIGN_TOP_MID, 0, 42);

    lv_obj_t* tuft = Oval(head_, 36, 22, kBlack);
    lv_obj_align(tuft, LV_ALIGN_TOP_MID, 0, 6);

    eye_l_ = Oval(head_, 52, 36, kWhite);
    lv_obj_align(eye_l_, LV_ALIGN_CENTER, -34, -18);
    eye_r_ = Oval(head_, 52, 36, kWhite);
    lv_obj_align(eye_r_, LV_ALIGN_CENTER, 34, -18);

    pupil_l_ = Oval(eye_l_, 18, 18, kBlack);
    lv_obj_align(pupil_l_, LV_ALIGN_CENTER, 4, 3);
    pupil_r_ = Oval(eye_r_, 18, 18, kBlack);
    lv_obj_align(pupil_r_, LV_ALIGN_CENTER, -4, 3);

    lid_l_ = Oval(eye_l_, 52, 12, kFur);
    lv_obj_align(lid_l_, LV_ALIGN_TOP_MID, 0, -2);
    lid_r_ = Oval(eye_r_, 52, 12, kFur);
    lv_obj_align(lid_r_, LV_ALIGN_TOP_MID, 0, -2);

    brow_l_ = Oval(head_, 42, 8, kBlack);
    lv_obj_align(brow_l_, LV_ALIGN_CENTER, -34, -46);
    brow_r_ = Oval(head_, 42, 8, kBlack);
    lv_obj_align(brow_r_, LV_ALIGN_CENTER, 34, -46);

    snout_ = Oval(head_, 108, 60, kSnout);
    lv_obj_align(snout_, LV_ALIGN_BOTTOM_MID, 0, -6);

    lv_obj_t* nose_l = Oval(snout_, 14, 10, kBlack);
    lv_obj_align(nose_l, LV_ALIGN_CENTER, -16, -6);
    lv_obj_t* nose_r = Oval(snout_, 14, 10, kBlack);
    lv_obj_align(nose_r, LV_ALIGN_CENTER, 16, -6);

    mouth_ = Oval(snout_, 42, 12, kMouth);
    lv_obj_align(mouth_, LV_ALIGN_CENTER, 0, 12);

    blush_l_ = Oval(head_, 28, 16, kBlush);
    lv_obj_align(blush_l_, LV_ALIGN_CENTER, -62, 16);
    blush_r_ = Oval(head_, 28, 16, kBlush);
    lv_obj_align(blush_r_, LV_ALIGN_CENTER, 62, 16);
    Hide(blush_l_);
    Hide(blush_r_);
}

void NiulaiLcdDisplay::ApplyFace(const char* emotion) {
    if (face_ == nullptr || emotion == nullptr) {
        return;
    }

    strncpy(emotion_, emotion, sizeof(emotion_) - 1);
    emotion_[sizeof(emotion_) - 1] = '\0';

    const bool listen = IsListen(emotion_);
    const bool smile = IsSmile(emotion_);
    const bool sleepy = strcmp(emotion_, "sleepy") == 0;
    const bool wink = strcmp(emotion_, "winking") == 0;
    const bool think = strcmp(emotion_, "thinking") == 0 || strcmp(emotion_, "confused") == 0;
    const bool angry = strcmp(emotion_, "angry") == 0;
    const bool surprise = strcmp(emotion_, "surprised") == 0 || strcmp(emotion_, "shocked") == 0;
    talking_ = smile || (!listen && !sleepy);

    int lid_h = 12;
    int mouth_w = 42;
    int mouth_h = 12;
    int pupil = 18;
    int brow_y = -46;
    int pupil_x = 4;
    if (listen) {
        lid_h = 8;
        mouth_w = 36;
        mouth_h = 10;
        pupil = 20;
        brow_y = -48;
        pupil_x = 6;
    } else if (smile) {
        lid_h = 6;
        mouth_w = 58;
        mouth_h = 20;
        pupil = 18;
        brow_y = -50;
        Show(blush_l_);
        Show(blush_r_);
    } else if (sleepy) {
        lid_h = 26;
        mouth_w = 28;
        mouth_h = 6;
        brow_y = -38;
    } else if (wink) {
        lid_h = 8;
        mouth_w = 46;
        mouth_h = 16;
        Show(blush_l_);
        Show(blush_r_);
    } else if (think) {
        lid_h = 10;
        mouth_w = 18;
        mouth_h = 18;
        brow_y = -42;
        pupil_x = -6;
    } else if (angry) {
        lid_h = 16;
        mouth_w = 22;
        mouth_h = 8;
        brow_y = -34;
    } else if (surprise) {
        lid_h = 2;
        mouth_w = 26;
        mouth_h = 26;
        pupil = 22;
    } else {
        lid_h = 8;
        mouth_w = 36;
        mouth_h = 10;
    }

    if (!smile && !wink) {
        Hide(blush_l_);
        Hide(blush_r_);
    }

    mouth_rest_h_ = mouth_h;
    mouth_phase_ = 0;

    lv_obj_set_height(lid_l_, lid_h);
    lv_obj_set_height(lid_r_, wink ? 30 : lid_h);
    lv_obj_set_size(mouth_, mouth_w, mouth_h);
    lv_obj_set_size(pupil_l_, pupil, pupil);
    lv_obj_set_size(pupil_r_, pupil, pupil);
    lv_obj_align(pupil_l_, LV_ALIGN_CENTER, pupil_x, 3);
    lv_obj_align(pupil_r_, LV_ALIGN_CENTER, -pupil_x, 3);
    lv_obj_align(brow_l_, LV_ALIGN_CENTER, -34, brow_y);
    lv_obj_align(brow_r_, LV_ALIGN_CENTER, 34, brow_y);
    if (angry) {
        lv_obj_set_style_transform_rotation(brow_l_, 250, 0);
        lv_obj_set_style_transform_rotation(brow_r_, -250, 0);
    } else {
        lv_obj_set_style_transform_rotation(brow_l_, 0, 0);
        lv_obj_set_style_transform_rotation(brow_r_, 0, 0);
    }

    Show(face_);
    lv_obj_move_foreground(face_);
}
