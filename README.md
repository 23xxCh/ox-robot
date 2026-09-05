# 牛来 / ox-robot

人前它是一只只会说「妈妈」的机械玩具；人离开后，它才过自己的生活。

一块小智 S3 扩展板 V1.7 负责听、说、屏、灯、键、超声和四路舵机信号。笔记本上的 `brain/` 负责人格、记忆和动作编排。不把完整 ESP-Claw 固件并进小智。

- 仓库：https://github.com/23xxCh/ox-robot
- Checkpoint 1：[牛来机器人-进展说明-2026-09-05.md](./牛来机器人-进展说明-2026-09-05.md)
- Checkpoint 2：[牛来机器人-Checkpoint2-进展说明-2026-09-06.md](./牛来机器人-Checkpoint2-进展说明-2026-09-06.md)
- Submission：[牛来机器人-Submission-2026-09-06.md](./牛来机器人-Submission-2026-09-06.md)

## 架构

```
喊「牛来牛来」 / 按 KY-004
        │
        ▼
  小智板 niulai-s3-expand-v17
  本地播 mama.ogg（不打开云端对话）
  冻结走板端 C · 舵机 5V 外供
        │  小智 WSS
        ▼
  笔记本 FastAPI  brain/
  人格 · Lua(niu.*) · MCP ttl 帽 · SQLite · 飞书/微信
```

约束：不合完整 ESP-Claw；ESP 的 5V 不给舵机供电；继电器不用；freeze 不走 LLM。

## 仓库

| 路径 | 内容 |
|---|---|
| `brain/` | 本地大脑（FastAPI、测例、排练页） |
| `firmware/xiaozhi-niulai/` | 小智板型 overlay、`mama.ogg`、接线说明 |
| `firmware/niulai-*-test/` | 屏/喇叭、超声、四足 Arduino 测试 |
| `mechanical/` | 开框 / BOM 件 / 外壳接口 |
| `docs/` | 架构、PRD、SPEC |
| `outputs/牛来机器人-A2L打印包-v0.5/` | 打印包 |

## 接线

屏已经占用 **GPIO 21（SCL）** 和 **GPIO 47（MOSI）**。灯和键不能接这两脚，否则花屏。

| 功能 | GPIO | 说明 |
|---|---|---|
| 屏 ST7789 2" | 21 / 47 / 45 / 40 / 41 / 42 | SCL / MOSI / RST / DC / CS / BL |
| 喇叭 MAX98357 | 15 / 16 / 7 | BCLK / LRC / DIN |
| 麦 | 4 / 5 / 6 | WS / SCK / DIN |
| 超声 HC-SR04 | 8 / 17 | TRIG / ECHO |
| 舵机 SG90 ×4 | 10 / 11 / **9** / 13 | **5V 外供**；左后不要接 GPIO 12（充电指示） |
| KY-016 灯 S | **14** | 三针模块本轮只会红 |
| KY-004 键 S | **18** | 按下为低，播本地「妈妈」 |
| BOOT | 0 | 短按切换聆听 |

KY-016：`-`=GND，中间=5V，`S`=14。  
KY-004：`-`=GND，中间 VCC 可空，`S`=18。  
舵机黄=信号、橙=外供 5V、棕=GND。一直转的那只，先确认黄线在 10–13，不要接到 14 / 15 / 16 / 21。

## 固件

板型 `niulai-s3-expand-v17`，源码 overlay 在 `firmware/xiaozhi-niulai/`，构建在小智 `xiaozhi-esp32` 树里。

- 唤醒词：`niu lai niu lai`（牛来牛来）
- 唤醒 / BOOT / KY-004 只播本地 `mama.ogg`，并立刻把四腿写回 1500 µs；不打开云端对话
- 超声近距视为有人：腿立刻中位、机械脸；约 8 秒无近距才对角小晃（可立刻打断）
- SECRET 步态：约 400 ms 对角 ±250 µs，随后约 2 s 停在 1500 µs。360° 舵机不会一直转

构建树：`E:\XIAOZHI_NATIVE\xiaozhi-esp32`。2026-09-05 18:24 已烧进 COM6（hash verified）。

```powershell
# ESP-IDF 6.0.2
Set-Location "E:\XIAOZHI_NATIVE\xiaozhi-esp32"
python scripts/build.py niulai-s3-expand-v17
idf.py -p COM6 flash
```

COM 口按设备管理器改。烧完先看黄牛脸，再按键或喊「牛来牛来」。

## 本地大脑

```powershell
pip install -r brain/requirements.txt
python -m pytest
python -m brain.app
```

排练页：http://127.0.0.1:8000/

无云端 API key 时测例仍应通过。

## 文档

| 文件 | 用途 |
|---|---|
| [牛来机器人-进展说明-2026-09-05.md](./牛来机器人-进展说明-2026-09-05.md) | Checkpoint 1 进展 |
| [牛来机器人-Checkpoint2-进展说明-2026-09-06.md](./牛来机器人-Checkpoint2-进展说明-2026-09-06.md) | Checkpoint 2 进展 |
| [牛来机器人-Submission-2026-09-06.md](./牛来机器人-Submission-2026-09-06.md) | 12:00 交卷稿 |
| [docs/architecture-niulai-local-brain-2026-09-05.md](./docs/architecture-niulai-local-brain-2026-09-05.md) | 当前软件架构 |
| [docs/prd-niulai-life-v2-2026-09-05.md](./docs/prd-niulai-life-v2-2026-09-05.md) | 生命感 PRD |
| [firmware/xiaozhi-niulai/README.md](./firmware/xiaozhi-niulai/README.md) | 板型与烧录 |

## 团队

陈熙贤（硬件）· 潘炜德（软件）· 微微（产品 & 商业）
