# 牛来小智板型 `niulai-s3-expand-v17`

源码：`E:\XIAOZHI_NATIVE\xiaozhi-esp32\main\boards\niulai-s3-expand-v17\`
overlay 同步在本目录。不要合完整 ESP-Claw。

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

屏上是黄牛来脸。人靠近：腿停，打断吐槽，切断私有 WSS，等人喊。人离开约 8 秒：随机小晃；吐槽走私有 `ws://192.168.10.95:8000/xiaozhi/v1/`（LLM + 千问 Dylan，约 11 秒一句）。拒绝 xiaozhi.me。音量 90。

生命循环在 `niulai_life.cc`：200 ms 一轮，有人时每拍都写 1500 µs，SECRET 可被近距立刻打断。超时 ≠ 确认无人。SECRET 随机步态短促再停，避免 360° 舵机空转。靠近不播 `mama.ogg`。唤醒 / BOOT / 键都会 `ParkActuators()` 并开始礼貌对话。

## 唤醒与礼貌对话

- 唤醒词：`niu lai`（单次「牛来」）
- 唤醒后走私有大脑礼貌听、想、说，**不打开小智官网**
- BOOT / 开始聆听同样走礼貌对话，禁止连官方 websocket
- 启动时跳过官方 OTA，避免被官网固件覆盖
- KY-004 短按同样开始礼貌对话

## 编译烧录

需要 ESP-IDF 6.0.2（本机 `E:\AI_TOY_TOOLS\esp-idf-v6.0.2`）：

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
$env:IDF_PATH = "E:\AI_TOY_TOOLS\esp-idf-v6.0.2"
$env:IDF_TOOLS_PATH = "E:\AI_TOY_TOOLS\espressif"
. "$env:IDF_PATH\export.ps1"
Set-Location "E:\XIAOZHI_NATIVE\xiaozhi-esp32"
python scripts/build.py niulai-s3-expand-v17
idf.py -p COM6 flash monitor
```

COM 口按设备管理器改。不要闪 COM6，除非 brain 挂了或 WLAN 不再是 `192.168.10.95`。靠近会 `ResetDecoder()`，SECRET 吐槽立刻停。烧完先看黄牛脸，再按 KY-004 或喊「牛来」。左后黄线必须在 GPIO 9，不要接 12。

## 小智主干挂钩（不在本 overlay 目录里）

这些改动在构建树 `E:\XIAOZHI_NATIVE\xiaozhi-esp32`，板型为 `niulai-s3-expand-v17` 时才生效：

- `main/application.cc`：`IsNiulaiBoard()`。启动跳过官方 OTA/激活；拒绝打开官方 websocket 音频通道；唤醒 / BOOT / KY-004 走 `NiulaiStartPoliteChat()`；近距走 `NiulaiEnterPresent()` 冻腿打断吐槽。
- `main/boards/common/board.h`：`virtual void ParkActuators() {}`，牛来板 override 成四腿 1500 µs。
- `main/assets/lang_config.h`：`OGG_MAMA` / `OGG_HI` / `OGG_SECRET1..3` 指向本地 Opus 剪辑。

不要打开 xiaozhi.me 点升级。
