"""Compile-time timing checks against the actual Application intro state."""
from pathlib import Path
import argparse
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True, help="Directory containing application.cc and application.h")
parser.add_argument("--compiler", required=True, help="C++17 compiler executable; syntax check only")
args = parser.parse_args()
text = (args.source / "application.cc").read_text(encoding="utf-8")
pin = text.split("void PinNiulaiBrainWebsocket() {", 1)[1].split("\n}", 1)[0]
assert 'settings.SetString("token", "");' not in pin, "Do not erase the device credential"
assert '#if __has_include("niulai_device_private.h")\n    settings.SetString("token", NIULAI_DEVICE_TOKEN);\n#endif' in pin
intro = text.split("void Application::NiulaiStartPoliteChat()", 1)[1].split(
    "void Application::NiulaiEnterSecret()", 1
)[0]
assert "vTaskDelay" not in intro, "Mama wait must not block the application task"
assert "audio_service_.IsPlaybackIdle()" in intro
assert intro.index("PlaySound(Lang::Sounds::OGG_MAMA)") < intro.index("niulai_polite_intro_.Begin(")
assert "Schedule([this]() { BeginNiulaiPoliteChat(); });" in intro
assert "CancelNiulaiPoliteChat();" in text.split("void Application::AbortSpeaking(", 1)[1].split("\n}", 1)[0]
assert "AbortSpeaking(" in text.split("void Application::NiulaiEnterPresent()", 1)[1].split("\n}", 1)[0]
error = text.split("if (bits & MAIN_EVENT_ERROR) {", 1)[1].split("\n        }", 1)[0]
assert error.index("CancelNiulaiPoliteChat();") < error.index("SetDeviceState("), "network error cancels intro"
closed = text.split("protocol_->OnAudioChannelClosed(", 1)[1].split("protocol_->OnIncomingJson(", 1)[0]
assert closed.index("CancelNiulaiPoliteChat();") < closed.index("SetDeviceState("), "channel close cancels intro"
incoming_json = text.split("protocol_->OnIncomingJson(", 1)[1].split("void Application::HandleDeviceConfig", 1)[0]
callbacks = re.findall(r"Schedule\(\[(.*?)\]\(\) \{(.*?)\n\s*\}\);", incoming_json, re.S)
for mutation in (
    "active_tts_reply_id_ = playback_reply_id;",  # tts.start
    "Ignoring stale TTS stop acknowledgement request",  # tts.stop with reply id
    "SetDeviceState(kDeviceStateListening);",  # legacy tts.stop
    'SetChatMessage("assistant", message.c_str());',
    'SetChatMessage("user", message.c_str());',
    "SetEmotion(emotion_str.c_str());",
):
    capture, body = next((capture, body) for capture, body in callbacks if mutation in body)
    assert "this" in capture and "reply_generation" in capture, mutation
    assert body.index("CanAcceptCloudReply(reply_generation)") < body.index(mutation), mutation
cancel = text.split("void Application::CancelNiulaiPoliteChat()", 1)[1].split("\n}", 1)[0]
assert "niulai_reply_generation_.fetch_add(1);" in cancel
assert "niulai_cloud_reply_enabled_ = false;" in cancel
continuation = text.split("void Application::ContinueNiulaiPoliteChat()", 1)[1].split("void Application::NiulaiEnterSecret()", 1)[0]
assert continuation.index("OpenAudioChannelWithConfigRefresh()") < continuation.index("EnableNiulaiCloudReplies();")

header = (args.source / "application.h").read_text(encoding="utf-8")
state = re.search(r"    struct NiulaiPoliteIntro \{.*?\n    \};", header, re.S)
assert state, "The actual intro timing state must be present"
source_code = "#include <cstdint>\n" + state.group(0) + r'''
constexpr bool mama_then_drain_once() {
    NiulaiPoliteIntro intro;
    if (!intro.Begin(100)) return false;
    if (intro.Take(2200099, true)) return false;
    if (intro.Take(2200100, false)) return false;
    if (!intro.Take(2300000, true)) return false;
    return !intro.Take(2400000, true);
}
static_assert(mama_then_drain_once(), "2.2 seconds and drained playback are both required");
constexpr bool repeated_wake_coalesces() {
    NiulaiPoliteIntro intro;
    if (!intro.Begin(0)) return false;
    if (intro.Begin(1000000)) return false;
    return intro.Take(2200000, true);
}
static_assert(repeated_wake_coalesces(), "duplicate wake neither stacks nor postpones intro");
constexpr bool cancellation_and_new_wake() {
    NiulaiPoliteIntro intro;
    intro.Begin(0);
    intro.Cancel();  // PRESENT and UNKNOWN share this cancellation path.
    if (intro.Take(2200000, true)) return false;
    if (!intro.Begin(3000000)) return false;  // A person may remain nearby and wake again.
    if (intro.Take(3100000, true)) return false;  // stale timer event
    if (!intro.Take(5200000, true)) return false;
    return !intro.Pending();
}
static_assert(cancellation_and_new_wake(), "cancel old continuation; allow a fresh near-person wake");
constexpr bool cloud_reply_epoch_blocks_stale_callbacks() {
    NiulaiPoliteIntro intro;
    uint32_t generation = 1;
    const uint32_t old_reply = generation;
    intro.Begin(0);
    if (intro.AcceptCloudReply(true, old_reply, generation)) return false;
    intro.Cancel();
    ++generation;
    if (intro.AcceptCloudReply(false, generation, generation)) return false;
    intro.Begin(3000000);
    intro.Take(5200000, true);
    if (intro.AcceptCloudReply(true, old_reply, generation)) return false;
    return intro.AcceptCloudReply(true, generation, generation);
}
static_assert(cloud_reply_epoch_blocks_stale_callbacks(), "cancelled replies cannot revive after a new chat opens");
'''
stop_body = text.split("void Application::HandleStopListeningEvent() {", 1)[1].split("\n}", 1)[0]
source_code += r'''
enum DeviceState { kDeviceStateAudioTesting, kDeviceStateWifiConfiguring, kDeviceStateListening, kDeviceStateIdle };
struct StopHarness {
    NiulaiPoliteIntro niulai_polite_intro_;
    bool cloud_enabled = true;
    DeviceState state = kDeviceStateListening;
    struct Audio { constexpr void EnableAudioTesting(bool) {} } audio_service_;
    struct Protocol { bool sent = false; constexpr void SendStopListening() { sent = true; } } protocol;
    Protocol* protocol_ = &protocol;
    constexpr void CancelNiulaiPoliteChat() { niulai_polite_intro_.Cancel(); cloud_enabled = false; }
    constexpr DeviceState GetDeviceState() const { return state; }
    constexpr void SetDeviceState(DeviceState next) { state = next; }
    constexpr void HandleStopListeningEvent() {
''' + stop_body + r'''
    }
};
constexpr bool normal_vad_stop_waits_for_cloud_reply() {
    StopHarness app;
    app.HandleStopListeningEvent();
    return app.protocol.sent && app.state == kDeviceStateIdle &&
        app.niulai_polite_intro_.AcceptCloudReply(app.cloud_enabled, 2, 2);
}
static_assert(normal_vad_stop_waits_for_cloud_reply(), "normal VAD stop must still accept STT/TTS");
constexpr bool stop_during_intro_cancels() {
    StopHarness app;
    app.niulai_polite_intro_.Begin(0);
    app.HandleStopListeningEvent();
    return !app.niulai_polite_intro_.Pending() && !app.cloud_enabled;
}
static_assert(stop_during_intro_cancels(), "explicit stop during mama cancels its continuation");
'''
enable_body = text.split("void Application::EnableNiulaiCloudReplies() {", 1)[1].split("\n}", 1)[0]
source_code += r'''
struct EnableHarness {
    bool niulai_cloud_reply_enabled_ = false;
    struct Counter {
        uint32_t value = 7;
        constexpr void fetch_add(uint32_t amount) { value += amount; }
    } niulai_reply_generation_;
    constexpr void EnableNiulaiCloudReplies() {
''' + enable_body + r'''
    }
};
constexpr bool opening_reply_gate_invalidates_handshake_callbacks() {
    EnableHarness app;
    NiulaiPoliteIntro intro;
    const uint32_t during_handshake = app.niulai_reply_generation_.value;
    app.EnableNiulaiCloudReplies();
    uint32_t live = app.niulai_reply_generation_.value;
    if (intro.AcceptCloudReply(app.niulai_cloud_reply_enabled_, during_handshake, live)) return false;
    if (!intro.AcceptCloudReply(app.niulai_cloud_reply_enabled_, live, live)) return false;
    app.EnableNiulaiCloudReplies(); // Existing SECRET session is not invalidated by its heartbeat.
    return live == app.niulai_reply_generation_.value;
}
static_assert(opening_reply_gate_invalidates_handshake_callbacks(), "blocked-era replies remain stale after authorization");
'''
compiler = Path(args.compiler)
result = subprocess.run([str(compiler), "-std=c++17", "-x", "c++", "-fsyntax-only", "-"],
                        input=source_code.encode("utf-8"), cwd=Path(__file__).parent, capture_output=True)
assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
print("PASS: actual C++ timing state, cancellation, repeated wake and native wiring")
