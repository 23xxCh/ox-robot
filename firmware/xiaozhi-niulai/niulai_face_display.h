#ifndef NIULAI_FACE_DISPLAY_H
#define NIULAI_FACE_DISPLAY_H

#include "display/lcd_display.h"

#include <lvgl.h>

class NiulaiLcdDisplay : public SpiLcdDisplay {
public:
    NiulaiLcdDisplay(esp_lcd_panel_io_handle_t panel_io, esp_lcd_panel_handle_t panel, int width,
                     int height, int offset_x, int offset_y, bool mirror_x, bool mirror_y,
                     bool swap_xy);

    void SetEmotion(const char* emotion) override;
    void ClearChatMessages() override;

private:
    lv_obj_t* face_ = nullptr;
    lv_obj_t* head_ = nullptr;
    lv_obj_t* horn_l_ = nullptr;
    lv_obj_t* horn_r_ = nullptr;
    lv_obj_t* ear_l_ = nullptr;
    lv_obj_t* ear_r_ = nullptr;
    lv_obj_t* eye_l_ = nullptr;
    lv_obj_t* eye_r_ = nullptr;
    lv_obj_t* pupil_l_ = nullptr;
    lv_obj_t* pupil_r_ = nullptr;
    lv_obj_t* lid_l_ = nullptr;
    lv_obj_t* lid_r_ = nullptr;
    lv_obj_t* brow_l_ = nullptr;
    lv_obj_t* brow_r_ = nullptr;
    lv_obj_t* snout_ = nullptr;
    lv_obj_t* mouth_ = nullptr;
    lv_obj_t* blush_l_ = nullptr;
    lv_obj_t* blush_r_ = nullptr;

    void BuildFace();
    void ApplyFace(const char* emotion);
};

#endif
