#include "niulai_face_display.h"

#include "display.h"

#include <cstring>

#define TAG "NiulaiFace"

namespace {

lv_obj_t* Oval(lv_obj_t* parent, int w, int h, lv_color_t color) {
    lv_obj_t* o = lv_obj_create(parent);
    lv_obj_set_size(o, w, h);
    lv_obj_set_style_bg_color(o, color, 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(o, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_border_width(o, 0, 0);
    lv_obj_set_style_pad_all(o, 0, 0);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE);
    return o;
}

}  // namespace

NiulaiLcdDisplay::NiulaiLcdDisplay(esp_lcd_panel_io_handle_t panel_io, esp_lcd_panel_handle_t panel,
                                   int width, int height, int offset_x, int offset_y, bool mirror_x,
                                   bool mirror_y, bool swap_xy)
    : SpiLcdDisplay(panel_io, panel, width, height, offset_x, offset_y, mirror_x, mirror_y,
                    swap_xy) {
    DisplayLockGuard lock(this);
    BuildFace();
    ApplyFace("neutral");
}

void NiulaiLcdDisplay::ClearChatMessages() {
    LcdDisplay::ClearChatMessages();
    DisplayLockGuard lock(this);
    if (emoji_label_ != nullptr) {
        lv_obj_add_flag(emoji_label_, LV_OBJ_FLAG_HIDDEN);
    }
    if (emoji_image_ != nullptr) {
        lv_obj_add_flag(emoji_image_, LV_OBJ_FLAG_HIDDEN);
    }
    if (face_ != nullptr) {
        lv_obj_remove_flag(face_, LV_OBJ_FLAG_HIDDEN);
    }
}

void NiulaiLcdDisplay::SetEmotion(const char* emotion) {
    DisplayLockGuard lock(this);
    ApplyFace(emotion != nullptr ? emotion : "neutral");
}

void NiulaiLcdDisplay::BuildFace() {
    lv_obj_t* parent = emoji_box_ != nullptr ? emoji_box_ : lv_screen_active();
    if (emoji_label_ != nullptr) {
        lv_obj_add_flag(emoji_label_, LV_OBJ_FLAG_HIDDEN);
    }
    if (emoji_image_ != nullptr) {
        lv_obj_add_flag(emoji_image_, LV_OBJ_FLAG_HIDDEN);
    }

    const lv_color_t fur = lv_color_hex(0xF0C000);
    const lv_color_t snout = lv_color_hex(0xE8A8C8);
    const lv_color_t horn = lv_color_hex(0x6E6E82);
    const lv_color_t ear = lv_color_hex(0xE6B4A0);
    const lv_color_t white = lv_color_hex(0xFFF8F0);
    const lv_color_t black = lv_color_hex(0x1A1A1A);
    const lv_color_t blush = lv_color_hex(0xE07090);

    face_ = lv_obj_create(parent);
    lv_obj_set_size(face_, 200, 200);
    lv_obj_center(face_);
    lv_obj_set_style_bg_opa(face_, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(face_, 0, 0);
    lv_obj_set_style_pad_all(face_, 0, 0);
    lv_obj_remove_flag(face_, LV_OBJ_FLAG_SCROLLABLE);

    horn_l_ = Oval(face_, 28, 46, horn);
    lv_obj_align(horn_l_, LV_ALIGN_TOP_LEFT, 28, 4);
    horn_r_ = Oval(face_, 28, 46, horn);
    lv_obj_align(horn_r_, LV_ALIGN_TOP_RIGHT, -28, 4);

    ear_l_ = Oval(face_, 36, 28, ear);
    lv_obj_align(ear_l_, LV_ALIGN_LEFT_MID, 2, -18);
    ear_r_ = Oval(face_, 36, 28, ear);
    lv_obj_align(ear_r_, LV_ALIGN_RIGHT_MID, -2, -18);

    head_ = Oval(face_, 150, 132, fur);
    lv_obj_align(head_, LV_ALIGN_TOP_MID, 0, 22);

    eye_l_ = Oval(head_, 42, 28, white);
    lv_obj_align(eye_l_, LV_ALIGN_CENTER, -28, -18);
    eye_r_ = Oval(head_, 42, 28, white);
    lv_obj_align(eye_r_, LV_ALIGN_CENTER, 28, -18);

    pupil_l_ = Oval(eye_l_, 14, 14, black);
    lv_obj_align(pupil_l_, LV_ALIGN_CENTER, 4, 2);
    pupil_r_ = Oval(eye_r_, 14, 14, black);
    lv_obj_align(pupil_r_, LV_ALIGN_CENTER, -4, 2);

    lid_l_ = Oval(eye_l_, 42, 16, fur);
    lv_obj_align(lid_l_, LV_ALIGN_TOP_MID, 0, -2);
    lid_r_ = Oval(eye_r_, 42, 16, fur);
    lv_obj_align(lid_r_, LV_ALIGN_TOP_MID, 0, -2);

    brow_l_ = Oval(head_, 36, 8, black);
    lv_obj_align(brow_l_, LV_ALIGN_CENTER, -28, -38);
    brow_r_ = Oval(head_, 36, 8, black);
    lv_obj_align(brow_r_, LV_ALIGN_CENTER, 28, -38);

    snout_ = Oval(head_, 86, 48, snout);
    lv_obj_align(snout_, LV_ALIGN_BOTTOM_MID, 0, -10);

    mouth_ = Oval(snout_, 36, 10, lv_color_hex(0xC07090));
    lv_obj_align(mouth_, LV_ALIGN_CENTER, 0, 6);

    blush_l_ = Oval(head_, 22, 12, blush);
    lv_obj_align(blush_l_, LV_ALIGN_CENTER, -52, 10);
    blush_r_ = Oval(head_, 22, 12, blush);
    lv_obj_align(blush_r_, LV_ALIGN_CENTER, 52, 10);
    lv_obj_add_flag(blush_l_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(blush_r_, LV_OBJ_FLAG_HIDDEN);
}

void NiulaiLcdDisplay::ApplyFace(const char* emotion) {
    if (face_ == nullptr || emotion == nullptr) {
        return;
    }

    const bool happy = strcmp(emotion, "happy") == 0 || strcmp(emotion, "laughing") == 0 ||
                       strcmp(emotion, "loving") == 0 || strcmp(emotion, "funny") == 0 ||
                       strcmp(emotion, "kissy") == 0 || strcmp(emotion, "confident") == 0;
    const bool sleepy = strcmp(emotion, "sleepy") == 0 || strcmp(emotion, "relaxed") == 0;
    const bool sad = strcmp(emotion, "sad") == 0 || strcmp(emotion, "crying") == 0;
    const bool angry = strcmp(emotion, "angry") == 0;
    const bool surprise = strcmp(emotion, "surprised") == 0 || strcmp(emotion, "shocked") == 0;
    const bool think = strcmp(emotion, "thinking") == 0 || strcmp(emotion, "confused") == 0;
    const bool shy = strcmp(emotion, "embarrassed") == 0 || strcmp(emotion, "silly") == 0;
    const bool wink = strcmp(emotion, "winking") == 0;

    int lid_h = 16;
    int mouth_w = 36;
    int mouth_h = 10;
    int pupil = 14;
    if (happy) {
        lid_h = 8;
        mouth_w = 48;
        mouth_h = 16;
        pupil = 16;
    } else if (sleepy) {
        lid_h = 22;
        mouth_w = 28;
        mouth_h = 6;
    } else if (sad) {
        lid_h = 18;
        mouth_w = 24;
        mouth_h = 8;
    } else if (angry) {
        lid_h = 18;
        mouth_w = 20;
        mouth_h = 8;
    } else if (surprise) {
        lid_h = 2;
        mouth_w = 22;
        mouth_h = 22;
        pupil = 18;
    } else if (think) {
        lid_h = 12;
        mouth_w = 18;
        mouth_h = 18;
    } else if (shy) {
        lid_h = 14;
        mouth_w = 32;
        mouth_h = 12;
    }

    lv_obj_set_height(lid_l_, lid_h);
    lv_obj_set_height(lid_r_, lid_h);
    lv_obj_set_size(mouth_, mouth_w, mouth_h);
    lv_obj_set_size(pupil_l_, pupil, pupil);
    lv_obj_set_size(pupil_r_, pupil, pupil);

    if (wink) {
        lv_obj_set_height(lid_r_, 24);
    }

    if (shy) {
        lv_obj_remove_flag(blush_l_, LV_OBJ_FLAG_HIDDEN);
        lv_obj_remove_flag(blush_r_, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(blush_l_, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(blush_r_, LV_OBJ_FLAG_HIDDEN);
    }

    if (emoji_label_ != nullptr) {
        lv_obj_add_flag(emoji_label_, LV_OBJ_FLAG_HIDDEN);
    }
    if (emoji_image_ != nullptr) {
        lv_obj_add_flag(emoji_image_, LV_OBJ_FLAG_HIDDEN);
    }
    if (face_ != nullptr) {
        lv_obj_remove_flag(face_, LV_OBJ_FLAG_HIDDEN);
    }
}
