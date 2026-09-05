# 牛来小智板型 `niulai-s3-expand-v17`

源码：`E:\AI TOY\xiaozhi-claw\firmware\xiaozhi-esp32\main\boards\niulai-s3-expand-v17\`
（与 `E:\XIAOZHI_NATIVE\xiaozhi-esp32` 是同一棵树）

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
- 灯不要占 GPIO 12（后左舵机）

KY-016 三针模块只有一路 PWM，所以现在只会红。要红绿蓝混色需要再引出 G/B 两路。

## 当前固件接线

| 功能 | GPIO | 说明 |
|---|---|---|
| KY-016 S（红） | **14** | PWM，共阴极，高电平更亮 |
| KY-004 S | **18** | 上拉，按下为低；点一下播本地「妈妈」 |
| 喇叭 MAX98357 | BCLK 15 / LRC 16 / DIN 7 | |
| 屏 ST7789 | SCL 21 MOSI 47 RST 45 DC 40 CS 41 BL 42 | invert on |
| 麦 I2S | WS 4 / SCK 5 / DIN 6 | 板载 |
| 超声 | TRIG 8 / ECHO 17 | 已预留，本轮未驱动 |
| 舵机 | 10 / 11 / 12 / 13 | 外供 5V。上电保持 1.5ms 中位（180° 停在中间，360° 连续转会停） |
| BOOT | 0 | 短按切换聆听；启动时进入配网 |

KY-016：`-`=GND，中间=5V，`S`=GPIO14。
KY-004：`-`=GND，中间 VCC 可空，`S`=GPIO18。

屏上是黄牛来脸（灰角、紫鼻子、半眼皮），不是小智机器人图标。唤醒/按键时切开心脸并显示「妈妈」。

## 唤醒与妈妈

- 唤醒词：`niu lai niu lai`（牛来牛来）
- 唤醒后只播本地 `mama.ogg`，**不打开云端对话，也不走小智官网**
- BOOT / 开始聆听同样只播「妈妈」，禁止连官方 websocket
- 启动时跳过官方 OTA，避免被官网固件覆盖
- KY-004 短按同样只播本地「妈妈」

## 编译烧录

需要 ESP-IDF 6.0.2（本机 `E:\AI_TOY_TOOLS\esp-idf-v6.0.2`）：

```powershell
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
$env:IDF_PATH = "E:\AI_TOY_TOOLS\esp-idf-v6.0.2"
$env:IDF_TOOLS_PATH = "E:\AI_TOY_TOOLS\espressif"
. "$env:IDF_PATH\export.ps1"
Set-Location "E:\AI TOY\xiaozhi-claw\firmware\xiaozhi-esp32"
python scripts/build.py niulai-s3-expand-v17
idf.py -p COM6 flash monitor
```

COM 口按设备管理器改。烧完后先看屏是否正常，再喊「牛来牛来」听喇叭是否说「妈妈」。
