#ifndef NIULAI_PRESENCE_H
#define NIULAI_PRESENCE_H

#include <cstdint>

enum class NiulaiPresence { Unknown, Present, Absent };

constexpr bool NiulaiDistanceValid(float cm) {
    return cm >= 2.0f && cm <= 400.0f;
}

// Only uninterrupted, valid far readings establish absence. A timeout is unknown.
constexpr NiulaiPresence ObserveNiulaiDistance(float cm, int64_t now,
                                               int64_t& far_since_us,
                                               NiulaiPresence current) {
    if (!NiulaiDistanceValid(cm)) {
        far_since_us = -1;
        return NiulaiPresence::Unknown;
    }
    if (cm < 55.0f) {
        far_since_us = -1;
        return NiulaiPresence::Present;
    }
    if (far_since_us < 0 || now < far_since_us) {
        far_since_us = now;
    }
    return now - far_since_us >= 8000000 ? NiulaiPresence::Absent : current;
}

#endif
