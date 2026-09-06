# 牛来小智板型 `niulai-s3-expand-v17`

源码：`E:\XIAOZHI_NATIVE\xiaozhi-esp32\main\boards\niulai-s3-expand-v17\`
overlay 同步在本目录。同步生命循环时须同时复制 `niulai_life.cc`、`niulai_life.h` 和 `niulai_presence.h`。不要合完整 ESP-Claw。

基于官方 `bread-compact-wifi-lcd`。继电器不用。舵机 5V 必须外供，不要从 ESP 5V 取电。

## 必须改线（屏会抢 21/47）

扩展板 2 寸屏已经占用：

| 屏脚 | GPIO |
|---|---|
| SCL | **21** |
| MOSI/SDA | **47** |
| RST | 45 |
| DC | 40 |
| CS | 41 |
| BL | 42 |

所以：

- **KY-016 的 S 不要接 21，改接到 GPIO 14**
- **KY-004 的 S 不要接 47，改接到 GPIO 18**
- 灯不要占 GPIO 12（充电指示 CHRG）。左后舵机改接 **GPIO 9**

KY-016 三针模块只有一路 PWM，所以现在只会红。要红绿蓝混色需要再引出 G/B 两路。

## 当前固件接线

| 功能 | GPIO | 说明 |
|---|---|---|
| KY-016 S（红） | **14** | PWM，共阴极，高电平更亮 |
| KY-004 S | **18** | 上拉，按下为低；点一下开始礼貌听、想、说 |
| 喇叭 MAX98357 | BCLK 15 / LRC 16 / DIN 7 | |
| 屏 ST7789 | SCL 21 MOSI 47 RST 45 DC 40 CS 41 BL 42 | invert on |
| 麦 I2S | WS 4 / SCK 5 / DIN 6 | 板载 |
| 超声 | TRIG 8 / ECHO 17 | 近距 PRESENT 立刻冻腿；约 8 秒无近距才 SECRET 对角晃。ECHO 建议 1k+2k 分压到 3.3V |
| 舵机 | 10 / 11 / **9** / 13 | 外供 5V。左后不要接 12：板上 12 是充电指示 CHRG |
| BOOT | 0 | 短按切换聆听；启动时进入配网 |

KY-016：`-`=GND，中间=5V，`S`=GPIO14。
KY-004：`-`=GND，中间 VCC 可空，`S`=GPIO18。

屏上是黄牛来脸。人靠近：腿停，打断吐槽，切断私有 WSS，等人喊；脸只用听/笑。人离开约 8 秒：随机小晃 + 吐槽脸；本轮候选固件的私有地址为 `ws://192.168.18.144:8000/xiaozhi/v1/`（冷却、可安静、最近 5 句不重复）。电脑服务目前仅绑定本机，尚未进行板端连接验收。断链播本地 `secret1/2/3.ogg`，不假装云端在聊。拒绝 xiaozhi.me。音量 90。

生命循环在 `niulai_life.cc`：200 ms 一轮，近距路径输出 1500 µs 冻腿，实际停止时延待测。礼貌对话里若让它动，可短促 `niu.walk`/`niu.turn`（ttl≤2000）；靠近仍冻。超时 ≠ 确认无人。SECRET 随机步态短促再停，避免 360° 舵机空转。靠近不播 `mama.ogg`。唤醒 / BOOT / 键：先停腿，播电影「妈妈」；至少 2.2 秒且音频排空后进入礼貌听、想、说。

## 唤醒与礼貌对话

- 唤醒词：`niu lai`（单次「牛来」）
- 唤醒后先播 `mama.ogg`（电影「妈妈」），再走私有大脑礼貌听、想、说，**不打开小智官网**
- BOOT / 开始聆听同样：妈妈片段 → 礼貌对话，禁止连官方 websocket
- 启动时跳过官方 OTA，避免被官网固件覆盖
- KY-004 短按同样开始礼貌对话

## 编译烧录

需要 ESP-IDF 6.0.2（本机 `E:\AI_TOY_TOOLS\esp-idf-v6.0.2`）：

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
$env:IDF_PATH = "E:\AI_TOY_TOOLS\esp-idf-v6.0.2"
$env:IDF_TOOLS_PATH = "E:\AI_TOY_TOOLS\espressif"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
. "$env:IDF_PATH\export.ps1"
Set-Location "E:\XIAOZHI_NATIVE\xiaozhi-esp32"
python scripts/build.py niulai-s3-expand-v17
```

COM 口按设备管理器改。先确认喇叭、超声、独立舵机供电接线和四腿悬空固定，再单独执行烧录命令。当前构建未烧录。服务故障本身不构成重刷固件的理由；WLAN 地址变化时须同步固件地址并验证服务可达。靠近会请求 `ResetDecoder()`，实际静音时延待测。烧完先看黄牛脸，再按 KY-004 或喊「牛来」。左后黄线必须在 GPIO 9，不要接 12。

实体准备完成后的烧录命令（沿用上方 IDF 环境）：

```powershell
idf.py -p COM6 flash monitor
```

## 小智主干挂钩（不在本 overlay 目录里）

本轮妈妈定时与回复过滤增量保存在 [application-intro-2026-09-06.patch](application-intro-2026-09-06.patch)，前后源码哈希见 [本轮记录](../../.grok-loop/evidence/runs/20260906-codex-round2.json)。仅适用于 `.scratch/codex-round2/native-before/` 对应的已修改小智基线，不能当成完整上游补丁。应用前先核对基线并运行 `git apply --check`，不要对已经包含该改动的构建树重复应用。

在上述 intro 补丁之后应用 [application-dialogue-2026-09-06.patch](application-dialogue-2026-09-06.patch)。它只修改 `main/application.cc`，加入可选本机设备凭据、启动前加载模型，以及传感器抖动时保留显式礼貌会话；不是完整上游补丁。应用前 SHA256：`458AE720797A69152B115FB09D0DBFC7CA3932911FAF7C070C74763197CC37A2`；应用后：`20B99D565A9E04A5207163A648FBAD95B51CF0C98990BD41793EC9C69A303EF9`。已在隔离目录通过 `git apply --check`、实际回放和结果哈希核对。

本机私有 `main/niulai_device_private.h` 可提供 `NIULAI_DEVICE_TOKEN`；缺头文件时保留 NVS token。补丁不包含凭据值，私有头文件不随 overlay 发布。

牛来的模型与资产随匹配固件发布，更新模型时须同时更新匹配的 `assets` 分区。启动在音频任务运行前加载一次，随后跳过联网资产下载与再次加载；本轮不支持运行中热换模型，避免引擎引用已解除映射的模型。缺资产或加载失败会记错误日志，需修复本地资产后重启。近距或 UNKNOWN 始终停腿并取消 SECRET；明确唤醒、BOOT 或 KY-004 发起的礼貌会话会保留，显式取消与断线仍会终止它。

本地可运行检查（使用实际源码；不会连接板子）：

```powershell
python firmware/xiaozhi-niulai/check_application_intro.py --source E:/XIAOZHI_NATIVE/xiaozhi-esp32/main --compiler E:/AI_TOY_TOOLS/espressif/tools/xtensa-esp-elf/esp-15.2.0_20251204/xtensa-esp-elf/bin/xtensa-esp32s3-elf-g++.exe
```

启动与传感器回归检查支持同样的 `--source`、`--compiler` 参数。替换为实际 native `main` 目录和支持 C++17 的 GCC 兼容编译器路径：

```powershell
python firmware/xiaozhi-niulai/check_application_voice_startup.py --source path/to/xiaozhi-esp32/main --compiler path/to/xtensa-esp32s3-elf-g++.exe
```

该检查提取实际源码，以 C++ 常量求值验证停腿、礼貌保留、SECRET 取消、启动状态保护及模型加载顺序；不生成固件、不接触私有头文件，不代替真机音频验收。

2026-09-06 接管修复：测距超时、非数值或超出 2–400 cm 时进入 UNKNOWN、清除远距计时并停腿；只有连续有效远距达到 8 秒才进入 ABSENT。已排队的 SECRET 请求执行前再次核对状态。音频取消仍经过应用任务调度，停止时延须真机测量；源码或构建通过不代表时延达标。

这些改动在构建树 `E:\XIAOZHI_NATIVE\xiaozhi-esp32`，板型为 `niulai-s3-expand-v17` 时才生效：

- `main/application.cc`：`IsNiulaiBoard()`。启动跳过官方 OTA/激活；拒绝打开官方 websocket 音频通道；唤醒 / BOOT / KY-004 走 `NiulaiStartPoliteChat()`（妈妈片段、定时事件与播放排空后再听）；近距走 `NiulaiEnterPresent()` 冻腿打断吐槽。
- `main/boards/common/board.h`：`virtual void ParkActuators() {}`，牛来板 override 成四腿 1500 µs。
- `main/assets/lang_config.h`：`OGG_MAMA` / `OGG_HI` / `OGG_SECRET1..3` 指向本地 Opus 剪辑。

不要打开 xiaozhi.me 点升级。

## Overlay vs native：本地 secret 剪辑

Overlay `AskBrainSecret()` **只** `Schedule(NiulaiEnterSecret)`，本目录没有 `PlaySound`、没有 clip 轮播。断链本地闷声在 native `main/application.cc` `NiulaiEnterSecret()`：WSS 打开失败才 `PlaySound(OGG_SECRET1/2/3)` 轮转；每 3 拍可安静。靠近路径走 `NiulaiEnterPresent()`，**不**播 `OGG_MAMA`。

| Overlay 资源 | Native 符号 / 路径 |
|---|---|
| `firmware/xiaozhi-niulai/secret1.ogg` | `Lang::Sounds::OGG_SECRET1` ← `main/assets/common/secret1.ogg` |
| `firmware/xiaozhi-niulai/secret2.ogg` | `Lang::Sounds::OGG_SECRET2` ← `main/assets/common/secret2.ogg` |
| `firmware/xiaozhi-niulai/secret3.ogg` | `Lang::Sounds::OGG_SECRET3` ← `main/assets/common/secret3.ogg` |
| `firmware/xiaozhi-niulai/mama.ogg` | `Lang::Sounds::OGG_MAMA` ← `main/assets/common/mama.ogg`（仅唤醒 / BOOT / KY-004） |
| `firmware/xiaozhi-niulai/hi.ogg` | `Lang::Sounds::OGG_HI` ← `main/assets/common/hi.ogg` |

资源存在 ≠ 已进当前 native 板型编译 ≠ 喇叭听过。三列证据见 [fallback-evidence.md](fallback-evidence.md)。本切片不复制 native 文件、不烧板、不声称 heard-on-device。
