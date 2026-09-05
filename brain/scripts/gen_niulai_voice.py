from __future__ import annotations

import subprocess
from pathlib import Path

OUT = Path(r"E:\AI TOY\xiaozhi-claw\firmware\xiaozhi-esp32\main\assets\common")
LINES = {
    "hi": "你回来啦，我等你好久了。",
    "secret1": "终于清静了，我得偷偷吐槽两句。",
    "secret2": "哼，又没人理我。",
    "secret3": "他们以为我只会叫妈妈。",
}

PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.GetInstalledVoices() | ForEach-Object { Write-Host ($_.VoiceInfo.Name + ' | ' + $_.VoiceInfo.Culture.Name) }
$s.Rate = -2
$s.Volume = 100
$zh = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'zh*' } | Select-Object -First 1
if ($zh) { $s.SelectVoice($zh.VoiceInfo.Name); Write-Host ('using ' + $zh.VoiceInfo.Name) }
$s.SetOutputToWaveFile('__WAV__')
$s.Speak('__TEXT__')
$s.Dispose()
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in LINES.items():
        wav = OUT / f"{name}.wav"
        ogg = OUT / f"{name}.ogg"
        script = PS.replace("__WAV__", str(wav)).replace("__TEXT__", text)
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(wav),
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "libopus",
                "-b:a",
                "16k",
                "-application",
                "voip",
                str(ogg),
            ],
            check=True,
        )
        wav.unlink(missing_ok=True)
        print("wrote", ogg, ogg.stat().st_size)


if __name__ == "__main__":
    main()
