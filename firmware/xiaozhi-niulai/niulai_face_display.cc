#include "niulai_face_display.h"

#include "display.h"

#include <cstring>

#define TAG "NiulaiFace"

namespace {

constexpr uint32_t kAnimPeriodMs = 80;
constexpr int kBlinkEveryTicks = 28;
constexpr int kBlinkClosedTicks = 2;
constexpr uint32_t kBarn = 0x2B1D12;
constexpr uint32_t kFur = 0xE8B000;
constexpr uint32_t kSnout = 0xE39BB0;
constexpr uint32_t kHorn = 0x8A8494;
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
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE);
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

}  // namespace

NiulaiLcdDisplay::NiulaiLcdDisplay(esp_lcd_panel_io_handle_t panel_io, esp_lcd_panel_handle_t panel,
                                   int width, int height, int offset_x, int offset_y, bool mirror_x,
                                   bool mirror_y, bool swap_xy)
    : SpiLcdDisplay(panel_io, panel, width, height, offset_x, offset_y, mirror_x, mirror_y,
                    swap_xy) {
    DisplayLockGuard lock(this);
    BuildFace();
    ApplyFace("listening");
    StartAnim();
}

NiulaiLcdDisplay::~NiulaiLcdDisplay() {
    if (anim_timer_ != nullptr) {
        DisplayLockGuard lock(this);
        lv_timer_delete(anim_timer_);
        anim_timer_ = nullptr;
    }
}

void NiulaiLcdDisplay::ClearChatMessages() {
    LcdDisplay::ClearChatMessages();
    DisplayLockGuard lock(this);
    Hide(emoji_label_);
    Hide(emoji_image_);
    Show(face_);
}

void NiulaiLcdDisplay::SetEmotion(const char* emotion) {
    DisplayLockGuard lock(this);
    blinking_ = false;
    blink_ticks_ = 0;
    ApplyFace(emotion != nullptr ? emotion : "listening");
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
        static const int kPulse[] = {4, 10, 6, 2, 8, 3};
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
    lv_obj_t* parent = container_ != nullptr ? container_ : screen;
    lv_obj_set_style_bg_color(screen, lv_color_hex(kBarn), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(parent, lv_color_hex(kBarn), 0);
    lv_obj_set_style_bg_opa(parent, LV_OPA_COVER, 0);

    Hide(emoji_label_);
    Hide(emoji_image_);
    Hide(emoji_box_);

    face_ = lv_obj_create(parent);
    lv_obj_set_size(face_, 240, 300);
    lv_obj_align(face_, LV_ALIGN_CENTER, 0, 6);
    lv_obj_set_style_bg_color(face_, lv_color_hex(kBarn), 0);
    lv_obj_set_style_bg_opa(face_, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(face_, 0, 0);
    lv_obj_set_style_border_width(face_, 0, 0);
    lv_obj_set_style_outline_width(face_, 0, 0);
    lv_obj_set_style_pad_all(face_, 0, 0);
    lv_obj_remove_flag(face_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(face_, LV_OBJ_FLAG_OVERFLOW_VISIBLE);
    lv_obj_move_foreground(face_);

    horn_l_ = Oval(face_, 34, 56, kHorn);
    lv_obj_align(horn_l_, LV_ALIGN_TOP_LEFT, 36, 8);
    horn_r_ = Oval(face_, 34, 56, kHorn);
    lv_obj_align(horn_r_, LV_ALIGN_TOP_RIGHT, -36, 8);

    ear_l_ = Oval(face_, 44, 34, kEar);
    lv_obj_align(ear_l_, LV_ALIGN_LEFT_MID, 4, -24);
    ear_r_ = Oval(face_, 44, 34, kEar);
    lv_obj_align(ear_r_, LV_ALIGN_RIGHT_MID, -4, -24);

    head_ = Oval(face_, 176, 156, kFur);
    lv_obj_align(head_, LV_ALIGN_TOP_MID, 0, 36);

    eye_l_ = Oval(head_, 50, 34, kWhite);
    lv_obj_align(eye_l_, LV_ALIGN_CENTER, -32, -20);
    eye_r_ = Oval(head_, 50, 34, kWhite);
    lv_obj_align(eye_r_, LV_ALIGN_CENTER, 32, -20);

    pupil_l_ = Oval(eye_l_, 16, 16, kBlack);
    lv_obj_align(pupil_l_, LV_ALIGN_CENTER, 4, 3);
    pupil_r_ = Oval(eye_r_, 16, 16, kBlack);
    lv_obj_align(pupil_r_, LV_ALIGN_CENTER, -4, 3);

    lid_l_ = Oval(eye_l_, 50, 14, kFur);
    lv_obj_align(lid_l_, LV_ALIGN_TOP_MID, 0, -2);
    lid_r_ = Oval(eye_r_, 50, 14, kFur);
    lv_obj_align(lid_r_, LV_ALIGN_TOP_MID, 0, -2);

    brow_l_ = Oval(head_, 40, 8, kBlack);
    lv_obj_align(brow_l_, LV_ALIGN_CENTER, -32, -44);
    brow_r_ = Oval(head_, 40, 8, kBlack);
    lv_obj_align(brow_r_, LV_ALIGN_CENTER, 32, -44);

    snout_ = Oval(head_, 100, 56, kSnout);
    lv_obj_align(snout_, LV_ALIGN_BOTTOM_MID, 0, -8);

    mouth_ = Oval(snout_, 42, 12, kMouth);
    lv_obj_align(mouth_, LV_ALIGN_CENTER, 0, 8);

    blush_l_ = Oval(head_, 26, 14, kBlush);
    lv_obj_align(blush_l_, LV_ALIGN_CENTER, -58, 12);
    blush_r_ = Oval(head_, 26, 14, kBlush);
    lv_obj_align(blush_r_, LV_ALIGN_CENTER, 58, 12);
    Hide(blush_l_);
    Hide(blush_r_);
}

void NiulaiLcdDisplay::ApplyFace(const char* emotion) {
    if (face_ == nullptr || emotion == nullptr) {
        return;
    }

    strncpy(emotion_, emotion, sizeof(emotion_) - 1);
    emotion_[sizeof(emotion_) - 1] = '\0';

    // Present/polite: only listen + smile. Everything else is the secret persona.
    const bool listen = strcmp(emotion_, "listening") == 0 || strcmp(emotion_, "neutral") == 0 ||
                        strcmp(emotion_, "relaxed") == 0;
    const bool smile = strcmp(emotion_, "happy") == 0 || strcmp(emotion_, "laughing") == 0 ||
                       strcmp(emotion_, "loving") == 0 || strcmp(emotion_, "funny") == 0;
    const bool sleepy = strcmp(emotion_, "sleepy") == 0;
    const bool wink = strcmp(emotion_, "winking") == 0;
    const bool think = strcmp(emotion_, "thinking") == 0 || strcmp(emotion_, "confused") == 0;
    const bool angry = strcmp(emotion_, "angry") == 0;
    const bool surprise = strcmp(emotion_, "surprised") == 0 || strcmp(emotion_, "shocked") == 0;
    talking_ = smile;

    int lid_h = 14;
    int mouth_w = 42;
    int mouth_h = 12;
    int pupil = 16;
    int brow_y = -44;
    if (listen) {
        lid_h = 10;
        mouth_w = 36;
        mouth_h = 10;
        pupil = 18;
        brow_y = -46;
    } else if (smile) {
        lid_h = 6;
        mouth_w = 56;
        mouth_h = 18;
        pupil = 18;
        brow_y = -48;
        Show(blush_l_);
        Show(blush_r_);
    } else if (sleepy) {
        lid_h = 24;
        mouth_w = 28;
        mouth_h = 6;
        brow_y = -36;
    } else if (wink) {
        lid_h = 10;
        mouth_w = 44;
        mouth_h = 14;
    } else if (think) {
        lid_h = 12;
        mouth_w = 20;
        mouth_h = 20;
        brow_y = -40;
    } else if (angry) {
        lid_h = 16;
        mouth_w = 22;
        mouth_h = 8;
        brow_y = -32;
    } else if (surprise) {
        lid_h = 2;
        mouth_w = 24;
        mouth_h = 24;
        pupil = 20;
    } else {
        // Unknown → listen, never a blank white face.
        lid_h = 10;
        mouth_w = 36;
        mouth_h = 10;
    }

    if (!smile) {
        Hide(blush_l_);
        Hide(blush_r_);
    }

    mouth_rest_h_ = mouth_h;
    mouth_phase_ = 0;

    lv_obj_set_height(lid_l_, lid_h);
    lv_obj_set_height(lid_r_, wink ? 28 : lid_h);
    lv_obj_set_size(mouth_, mouth_w, mouth_h);
    lv_obj_set_size(pupil_l_, pupil, pupil);
    lv_obj_set_size(pupil_r_, pupil, pupil);
    lv_obj_align(brow_l_, LV_ALIGN_CENTER, -32, brow_y);
    lv_obj_align(brow_r_, LV_ALIGN_CENTER, 32, brow_y);

    Hide(emoji_label_);
    Hide(emoji_image_);
    Hide(emoji_box_);
    Show(face_);
    lv_obj_move_foreground(face_);
}
