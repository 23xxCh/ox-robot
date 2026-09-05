# 牛来机器人：开源 3D 模型偷懒路线调研

更新时间：2026-09-02

> 更正：本文最初把目标误解成了“通用牛外形”。本项目真正的目标是电影《牛来》中的黄色拟人角色。精确角色模型、许可和采用建议请以同目录的 `2026-09-02-niulai-movie-character-3d-model-sources.md` 为准；下列通用牛模型只保留为许可干净的备选几何来源，不再是首选。

## 结论

没有找到一套能直接同时匹配主办方 `ESP32-S3 + 两个黄色 TT 电机 + HC-SR04 + 2.42 寸 OLED + 三个定位舵机` 的现成整机。已经找到电影《牛来》角色本体的打印模型，但它们不是开源许可。若不能获得作者改造授权，最省工且风险最低的组合仍是：

1. 用 CC0 牛模型快速获得牛头、牛角、耳朵和鼻子的基础几何。
2. 用现成开源机器人项目借 OLED 表情、舵机动作和装配经验。
3. 保留本项目 FreeCAD v0.2 的底盘和头部接口，因为它已经按主办方物料包络处理。

## 第一优先级：可以直接拿来改

### 1. Quaternius Cow（Poly Pizza）——牛头基础几何首选

- 地址：https://poly.pizza/m/26zM1outCr
- 格式：FBX / GLTF。
- 许可：CC0，允许修改、再发布和商用，无需署名。
- 适合复用：完整牛体、牛头比例、牛角、耳朵和鼻子。
- 使用方式：在 Blender 中只保留头部，调整为“牛来”的宽鼻子和半眯眼，再空心化；不要直接作为机械结构。
- 判断：这是当前最干净的合法偷懒起点，优先于从单张图片完全重新生成。

### 2. Highland Cow（Pinshape）——可打印牛外观参考

- 地址：https://pinshape.com/items/108366-3d-printed-highland-cow
- 格式：完整 STL、左右分件 STL 和 16 个大尺寸分件。
- 许可：CC0。
- 适合复用：牛角、额头、耳朵、鼻部轮廓以及分件方式。
- 限制：它是墙面装饰模型，不是可套在舵机骨架上的完整头壳；适合提取轮廓和局部，不适合直接当牛来头壳。

### 3. OpenBot / OpenBot Compact Body——底盘结构与 STEP 零件库

- 主项目：https://github.com/ob-f/OpenBot
- 小打印机版本：https://github.com/sloretz/OpenBot-CompactBody
- 格式：大量 STL 与 STEP；Compact Body 至少包含车体、电池架和安装板的 STL/STEP。
- 许可：OpenBot 为 MIT；Compact Body 为 Apache-2.0。
- 适合复用：TT 电机仓、分体车壳、电池固定、M3 螺母槽、轮轴布局和装配说明。
- 限制：原 OpenBot DIY 主要是四个 TT 电机和手机方案，不是牛来的两轮 P0，不能整体替换现有底盘。
- 判断：借局部结构和 STEP 建模方式，不整车照搬。

### 4. Sesame Robot——OLED 表情与“有生命感”软件首选

- 地址：https://github.com/dorianborian/sesame-robot
- 格式：16 个以上 STL/STEP、ESP32 固件、表情库、动作编辑器和仿真环境。
- 许可：Apache-2.0。
- 适合复用：OLED 表情位图、说话表情变体、动作序列、REST/串口控制思路和打印装配文档。
- 限制：它是 8 个 MG90 舵机的四足机器人，机械腿和主体不能直接套到牛来。
- 判断：硬件不抄，表情和动作软件值得重点借鉴。

### 5. DIY Animatronic Endoskeleton——嘴与头部动作参考

- 地址：https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton
- 格式：Blender 源文件、ESP32/MicroPython 控制与多舵机方案。
- 许可：MIT。
- 适合复用：下巴开合、头部转动、动作通信和舵机控制组织方式。
- 限制：原项目约 10 个舵机，远超牛来 P0 的复杂度；只借一个嘴舵机和头部运动概念。

## 第二优先级：有用，但必须先确认许可或实物尺寸

### minirobo Caster

- 地址：https://www.minirobo.io/projects/caster
- 提供 STL、OpenSCAD 源文件、固件和接线资料。
- 可借鉴 DRV8833 双轮差速、打印万向轮/后支撑、试打电机仓的顺序。
- 它使用 N20 电机而不是主办方黄色 TT 电机；页面未明确显示设计文件许可，不应直接并入需要公开发布的牛来文件。

### Animatronic Puppet Head Mechanics

- 地址：https://bechele.de/?p=1206
- 提供完整 STL、STEP，并使用 5 个 SG90 舵机。
- 嘴部、颈部和精度校准说明非常有参考价值。
- 页面未看到清晰的硬件文件许可；可以学习机构，正式复用前要进一步确认。

### ε-Series Animatronic Eye Mechanism

- 地址：https://nmrobots.com/pages/designs
- 官方提供可下载 CAD，并宣称大部分设计开源；支持 MG90/SG90。
- 牛来 P0 已经选 OLED 表情，不值得现在增加机械眼，保留为后续升级参考。

## 发现模型的网站怎么选

| 网站 | 最适合找什么 | 许可风险 | 建议 |
| --- | --- | --- | --- |
| GitHub | 带 STEP/OpenSCAD/Blender 源文件的机器人项目 | 看仓库 LICENSE | 机械件首选 |
| Poly Pizza / Quaternius | CC0 的低多边形动物与角色 | 低，逐项确认 CC0 | 牛外形首选 |
| Printables | 有真实打印记录的 STL/3MF | 每个模型不同 | 优先看 Makes 和源文件 |
| MakerWorld | Bambu 3MF、切片参数和直接打印配置 | 每个模型不同 | 适合最终打印配置，不等于开源 |
| Thingiverse | 老牌机器人零件与大量 Remix | 常见 CC BY-NC-SA | 可找旧机构，必须回原页看许可 |
| Pinshape | 免费 STL 与明确 CC 许可 | 每个模型不同 | 目前找到一个 CC0 牛模型 |
| GrabCAD | STEP、SolidWorks、工业零件 | 免费下载不等于开源 | 尺寸参考，不默认再发布 |
| TurboSquid / CGTrader / Cults | 成品模型多 | 平台许可或个人许可 | 只有许可清楚时才采用 |
| Thangs / STLFinder / 3DGo | 跨站搜索 | 聚合页不代表授权 | 只用于发现，必须回原始页面 |

## 推荐的最省工实施顺序

1. 下载 Quaternius CC0 Cow 的 GLTF/FBX，在 Blender 中切出牛头。
2. 以牛来参考图修改鼻子、眼皮、耳朵和牛角；必要时再把修改后的多视图交给 Tripo P2.0 重拓扑。
3. 把头部缩放到 FreeCAD v0.2 预留的核心包络约 `136 × 112 × 72 mm`，底部保留 `80 × 50 mm` 机械接口。
4. 最终尺寸冻结后做 `1.4–1.6 mm` 壁厚、前后分壳、嘴部切割和螺丝柱。
5. 复制 Sesame 的 OLED 表情/动作组织思路，不复制四足结构。
6. 底盘继续使用本项目 v0.2；只在主办方 TT 电机实物不匹配时，从 OpenBot STEP 中借电机仓结构。

## 不建议现在做的事

- 不要整套换成 OpenBot、SMARS、Otto 或 Sesame；它们的电机数、舵机数、控制板和电源都与主办方物料不一致。
- 不要看到“Free Download”就当成开源；没有明确 LICENSE 的模型只作为参考。
- 不要先打印完整网络模型；先打印牛角、底部接口环和嘴轴三个小样。
- 不要为 P0 加机械眼；OLED 已经能提供更低重量、更可靠的表情。
