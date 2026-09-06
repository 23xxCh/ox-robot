"""Check actual voice-startup source with C++17 constexpr side-effect spies.

No device access, generated artifacts, private headers, or linked firmware build.
Dependencies are substituted only at their singleton boundaries; production
branches are extracted from the supplied application.cc, never reimplemented.
The compiler evaluates the assertions; this does not prove physical audio IO.
"""
from pathlib import Path
import argparse
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True,
                    help="Native main directory containing application.cc and main.cc")
parser.add_argument("--compiler", required=True,
                    help="GCC-compatible C++17 compiler executable; syntax check only")
args = parser.parse_args()
text = (args.source / "application.cc").read_text(encoding="utf-8")


def check_cpp(code, label):
    result = subprocess.run(
        [args.compiler, "-std=c++17", "-x", "c++", "-fsyntax-only", "-"],
        input=code.encode("utf-8"), capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr.decode("utf-8", errors="replace"))
    print("PASS: " + label)


body = text.split("void Application::NiulaiEnterPresent() {", 1)[1].split("\n}", 1)[0]
# Substitute only the Board singleton dependency; keep all production branches.
body = body.replace("Board::GetInstance()", "board_")
code = r'''
#define ESP_LOGI(...) ((void)0)
enum ListeningMode { kListeningModeAutoStop, kListeningModeManualStop };
enum { kAbortReasonNone, kDeviceStateIdle, kDeviceStateStarting, kDeviceStateActivating, kDeviceStateWifiConfiguring };
struct App {
    struct Intro { bool pending = false; constexpr bool Pending() const { return pending; } } niulai_polite_intro_;
    bool niulai_cloud_reply_enabled_ = false;
    ListeningMode listening_mode_ = kListeningModeManualStop;
    struct Display {
        int changes = 0;
        constexpr void SetEmotion(const char*) { ++changes; }
        constexpr void SetChatMessage(const char*, const char*) { ++changes; }
    };
    struct Board {
        int parks = 0;
        Display display;
        constexpr void ParkActuators() { ++parks; }
        constexpr Display* GetDisplay() { return &display; }
    } board_;
    struct Audio {
        int resets = 0;
        bool wake = false;
        constexpr void ResetDecoder() { ++resets; }
        constexpr void EnableWakeWordDetection(bool enabled) { wake = enabled; }
    } audio_service_;
    struct Protocol {
        bool open = true;
        int presence_sent = 0;
        constexpr bool IsAudioChannelOpened() const { return open; }
        constexpr void SendNiulaiPresence(const char*) { ++presence_sent; }
        constexpr void CloseAudioChannel() { open = false; }
    } protocol;
    Protocol* protocol_ = &protocol;
    int aborts = 0;
    int state = kDeviceStateIdle;
    constexpr int GetDeviceState() const { return state; }
    constexpr void AbortSpeaking(int) {
        ++aborts;
        niulai_polite_intro_.pending = false;
        niulai_cloud_reply_enabled_ = false;
    }
    constexpr void SetDeviceState(int next) { state = next; }
    constexpr void NiulaiEnterPresent() {
''' + body + r'''
    }
};
constexpr bool explicit_intro_survives_presence_jitter() {
    App app;
    app.niulai_polite_intro_.pending = true;
    app.NiulaiEnterPresent(); // PRESENT
    app.NiulaiEnterPresent(); // UNKNOWN uses this same handler.
    return app.board_.parks == 2 && app.aborts == 0 && app.niulai_polite_intro_.pending &&
        app.protocol.open && app.audio_service_.resets == 0;
}
static_assert(explicit_intro_survives_presence_jitter(), "presence must park legs without cancelling requested mama");
constexpr bool polite_conversation_survives_presence_jitter() {
    App app;
    app.niulai_cloud_reply_enabled_ = true;
    app.listening_mode_ = kListeningModeAutoStop;
    app.NiulaiEnterPresent();
    app.NiulaiEnterPresent();
    return app.board_.parks == 2 && app.aborts == 0 && app.protocol.open &&
        app.niulai_cloud_reply_enabled_ && app.audio_service_.resets == 0;
}
static_assert(polite_conversation_survives_presence_jitter(), "explicit polite audio must survive sensor jitter");
constexpr bool unrequested_secret_still_cancels() {
    App app;
    app.niulai_cloud_reply_enabled_ = true;
    app.NiulaiEnterPresent();
    return app.board_.parks == 1 && app.aborts == 1 && !app.protocol.open &&
        !app.niulai_cloud_reply_enabled_ && app.audio_service_.wake;
}
static_assert(unrequested_secret_still_cancels(), "SECRET must still stop on presence or unknown");
constexpr bool explicit_abort_is_not_undone() {
    App app;
    app.listening_mode_ = kListeningModeAutoStop;
    app.niulai_cloud_reply_enabled_ = true;
    app.AbortSpeaking(kAbortReasonNone);
    app.NiulaiEnterPresent();
    return !app.niulai_cloud_reply_enabled_ && !app.protocol.open && app.board_.parks == 1;
}
static_assert(explicit_abort_is_not_undone(), "an aborted polite session must not remain protected");
constexpr bool startup_presence_only_parks() {
    for (int state : {kDeviceStateStarting, kDeviceStateActivating, kDeviceStateWifiConfiguring}) {
        App app;
        app.state = state;
        app.NiulaiEnterPresent();
        if (app.board_.parks != 1 || app.aborts != 0 || app.audio_service_.wake ||
            app.state != state || app.audio_service_.resets != 0) return false;
    }
    return true;
}
static_assert(startup_presence_only_parks(), "startup presence must not initialize wake detection or force idle");
'''
code = "#include <initializer_list>\n" + code

check_cpp(code, "presence parks legs, preserves explicit polite audio, cancels SECRET, protects startup")

initialize = text.split("void Application::Initialize() {", 1)[1].split("\n}", 1)[0]
startup = initialize.split("audio_service_.Initialize(codec);", 1)[1].split("audio_service_.Start();", 1)[0]
startup = startup.replace("Assets::GetInstance()", "assets_")
check_entry = text.split("void Application::CheckAssetsVersion() {", 1)[1].split("auto& board =", 1)[0]
main = (args.source / "main.cc").read_text(encoding="utf-8")
assert main.index("app.Initialize();") < main.index("app.Run();")
assert initialize.index("audio_service_.Initialize(codec);") < initialize.index("audio_service_.Start();")

code = r'''
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
#define ESP_LOGE(...) ((void)0)
struct App {
    bool niulai = true;
    bool assets_version_checked_ = false;
    bool started = false;
    int network_asset_work = 0;
    struct Assets {
        bool valid = true;
        bool succeeds = true;
        int apply_calls = 0;
        bool refreshed = false;
        constexpr bool partition_valid() const { return valid; }
        constexpr bool Apply(bool refresh) { ++apply_calls; refreshed = refresh; return succeeds; }
    } assets_;
    constexpr bool IsNiulaiBoard() const { return niulai; }
    constexpr void StartupBeforeAudioStart() {
''' + startup + r'''
        started = true;
    }
    constexpr void CheckAssetsVersion() {
''' + check_entry + r'''
        ++network_asset_work; // All real download/apply statements follow the extracted guard.
    }
};
constexpr bool local_assets_precede_start_and_only_apply_once() {
    App app;
    app.StartupBeforeAudioStart();
    app.CheckAssetsVersion();
    app.CheckAssetsVersion();
    return app.started && app.assets_.apply_calls == 1 && !app.assets_.refreshed &&
        app.assets_version_checked_ && app.network_asset_work == 0;
}
static_assert(local_assets_precede_start_and_only_apply_once(), "Niulai must apply local models before start, never repeat over network");
constexpr bool missing_or_invalid_assets_do_not_enable_hot_replacement() {
    App missing;
    missing.assets_.valid = false;
    missing.StartupBeforeAudioStart();
    missing.CheckAssetsVersion();
    App failed;
    failed.assets_.succeeds = false;
    failed.StartupBeforeAudioStart();
    failed.CheckAssetsVersion();
    return missing.assets_.apply_calls == 0 && missing.network_asset_work == 0 &&
        failed.assets_.apply_calls == 1 && failed.network_asset_work == 0;
}
static_assert(missing_or_invalid_assets_do_not_enable_hot_replacement(), "failed local assets must not trigger unsafe runtime remapping");
constexpr bool other_boards_keep_network_asset_path() {
    App app;
    app.niulai = false;
    app.StartupBeforeAudioStart();
    app.CheckAssetsVersion();
    return app.assets_.apply_calls == 0 && app.network_asset_work == 1;
}
static_assert(other_boards_keep_network_asset_path(), "other boards must retain existing activation flow");
'''

check_cpp(code, "local Niulai models load before Start/Run; no network replacement; other boards unchanged")
